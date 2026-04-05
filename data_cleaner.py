"""
data_cleaner.py
---------------
Reads data/raw_jobs.csv (produced by scraper.py), applies cleaning rules,
and writes the result to data/cleaned_jobs.csv.

Cleaning steps:
  1. Drop exact duplicate rows.
  2. Strip leading/trailing whitespace from all string columns.
  3. Standardise work_type values to "Remote", "Hybrid", or "On-site".
  4. Parse salary strings into numeric salary_min, salary_max, and salary_avg
     columns (annual USD).
  5. Parse date_posted → datetime; add days_since_posted (relative to the
     most recent date in the dataset, so the numbers stay meaningful when
     the CSV is shared).
  6. Extract city and state from the location field.
  7. Drop rows where job_title or company is empty.
  8. Reset index and write the cleaned CSV.

Usage:
    python data_cleaner.py
    python data_cleaner.py --input  path/to/raw.csv
                           --output path/to/cleaned.csv
"""

import argparse
import re
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DEFAULT_INPUT = Path("data/raw_jobs.csv")
DEFAULT_OUTPUT = Path("data/cleaned_jobs.csv")

# ---------------------------------------------------------------------------
# Salary parser
# ---------------------------------------------------------------------------

_HOURLY_TO_ANNUAL = 2080  # 40 h/wk × 52 wk


def _parse_salary(raw: str) -> tuple[float | None, float | None, float | None]:
    """Return (salary_min, salary_max, salary_avg) in USD/year, or (None, None, None)."""
    if not raw or not isinstance(raw, str):
        return None, None, None

    raw = raw.replace(",", "").strip()
    hourly = "hour" in raw.lower()

    numbers = re.findall(r"\$?([\d.]+)", raw)
    if not numbers:
        return None, None, None

    values = [float(n) for n in numbers]
    lo = min(values)
    hi = max(values)

    if hourly:
        lo *= _HOURLY_TO_ANNUAL
        hi *= _HOURLY_TO_ANNUAL

    avg = (lo + hi) / 2
    return round(lo, 2), round(hi, 2), round(avg, 2)


# ---------------------------------------------------------------------------
# Location parser
# ---------------------------------------------------------------------------

_STATE_ABBRS = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}


def _parse_location(loc: str) -> tuple[str, str]:
    """Return (city, state) from a location string such as 'Austin, TX (Hybrid)'."""
    if not loc or not isinstance(loc, str):
        return "", ""

    # Strip trailing parenthetical like "(Hybrid)"
    loc = re.sub(r"\s*\(.*?\)", "", loc).strip()

    if loc.lower() == "remote":
        return "Remote", ""

    # Expect "City, ST" pattern
    parts = [p.strip() for p in loc.split(",")]
    if len(parts) >= 2:
        city = parts[0]
        # State is the first 2-letter token in the second part
        state_match = re.search(r"\b([A-Z]{2})\b", parts[1])
        state = state_match.group(1) if state_match and state_match.group(1) in _STATE_ABBRS else parts[1][:2]
        return city, state

    return loc, ""


# ---------------------------------------------------------------------------
# Work-type standardiser
# ---------------------------------------------------------------------------

def _standardise_work_type(val: str) -> str:
    if not isinstance(val, str):
        return "On-site"
    val_lower = val.lower()
    if "remote" in val_lower:
        return "Remote"
    if "hybrid" in val_lower:
        return "Hybrid"
    return "On-site"


# ---------------------------------------------------------------------------
# Main cleaning function
# ---------------------------------------------------------------------------

def clean(input_path: Path, output_path: Path) -> pd.DataFrame:
    print(f"[INFO] Reading raw data from {input_path} …")
    df = pd.read_csv(input_path, dtype=str)
    print(f"[INFO] Loaded {len(df)} rows, {df.shape[1]} columns.")

    # 1. Strip whitespace
    str_cols = df.select_dtypes(include=["object", "str"]).columns
    df[str_cols] = df[str_cols].apply(lambda s: s.str.strip())

    # 2. Drop exact duplicates
    before = len(df)
    df.drop_duplicates(inplace=True)
    print(f"[INFO] Dropped {before - len(df)} duplicate rows.")

    # 3. Drop rows with empty essential fields
    df = df[df["job_title"].notna() & (df["job_title"] != "")]
    df = df[df["company"].notna() & (df["company"] != "")]
    print(f"[INFO] {len(df)} rows after dropping empties.")

    # 4. Standardise work_type
    df["work_type"] = df["work_type"].apply(_standardise_work_type)

    # 5. Parse salary
    parsed = df["salary"].apply(_parse_salary)
    df["salary_min"] = [p[0] for p in parsed]
    df["salary_max"] = [p[1] for p in parsed]
    df["salary_avg"] = [p[2] for p in parsed]

    # 6. Parse dates
    df["date_posted"] = pd.to_datetime(df["date_posted"], errors="coerce")
    reference_date = df["date_posted"].max()
    df["days_since_posted"] = (reference_date - df["date_posted"]).dt.days

    # 7. Parse location into city / state
    loc_parsed = df["location"].apply(_parse_location)
    df["city"] = [p[0] for p in loc_parsed]
    df["state"] = [p[1] for p in loc_parsed]

    # 8. Select and order output columns
    output_cols = [
        "job_title",
        "company",
        "location",
        "city",
        "state",
        "work_type",
        "salary",
        "salary_min",
        "salary_max",
        "salary_avg",
        "date_posted",
        "days_since_posted",
        "job_role",
        "description_snippet",
        "url",
    ]
    df = df[[c for c in output_cols if c in df.columns]].copy()

    # 9. Reset index
    df.reset_index(drop=True, inplace=True)

    # 10. Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"[INFO] Wrote {len(df)} cleaned rows → {output_path}")
    return df


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Clean raw Indeed job data.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Path to raw CSV.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path for cleaned CSV.")
    args = parser.parse_args()

    df = clean(Path(args.input), Path(args.output))

    print("\n[SUMMARY]")
    print(f"  Total records     : {len(df)}")
    print(f"  Roles             : {sorted(df['job_role'].unique())}")
    print(f"  Work types        : {sorted(df['work_type'].unique())}")
    print(f"  Date range        : {df['date_posted'].min().date()} → {df['date_posted'].max().date()}")
    print(f"  Salary data       : {df['salary_avg'].notna().sum()} rows with salary info")
    print("\nWork-type breakdown:")
    print(df.groupby(["job_role", "work_type"]).size().unstack(fill_value=0).to_string())


if __name__ == "__main__":
    main()
