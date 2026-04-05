"""
visualize.py
------------
Reads data/cleaned_jobs.csv and produces a set of charts that compare
Remote vs Hybrid vs On-site work arrangements across four tech roles
(Software Engineer, Data Analyst, Cybersecurity, DevOps).

Charts saved to visualizations/:
  1. work_type_distribution.png  — grouped bar chart (count per role × work type)
  2. work_type_pct_stacked.png   — 100 % stacked bar chart
  3. work_type_pie_by_role.png   — 2×2 grid of pie charts, one per role
  4. overall_work_type_pie.png   — single pie chart across all roles
  5. salary_by_work_type.png     — box-plot of salary_avg by work type
  6. salary_by_role_work_type.png— grouped box-plot of salary_avg
  7. postings_over_time.png      — line chart: daily postings by work type
  8. heatmap_role_work_type.png  — heatmap of posting counts

Usage:
    python visualize.py
    python visualize.py --input path/to/cleaned.csv --output-dir visualizations/
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd
import seaborn as sns

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_INPUT = Path("data/cleaned_jobs.csv")
DEFAULT_OUTPUT_DIR = Path("visualizations")

WORK_TYPE_ORDER = ["Remote", "Hybrid", "On-site"]
ROLE_ORDER = ["Software Engineer", "Data Analyst", "Cybersecurity", "DevOps"]

PALETTE = {
    "Remote":  "#4C9BE8",
    "Hybrid":  "#F6AE2D",
    "On-site": "#F26419",
}

sns.set_theme(style="whitegrid", font_scale=1.1)
plt.rcParams.update({"figure.dpi": 150, "savefig.bbox": "tight"})


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    print(f"  [SAVED] {path}")


# ---------------------------------------------------------------------------
# Chart functions
# ---------------------------------------------------------------------------

def chart_grouped_bar(df: pd.DataFrame, out_dir: Path) -> None:
    """Grouped bar chart: count per (job_role, work_type)."""
    counts = (
        df.groupby(["job_role", "work_type"])
        .size()
        .reset_index(name="count")
    )
    counts["job_role"] = pd.Categorical(counts["job_role"], categories=ROLE_ORDER, ordered=True)
    counts["work_type"] = pd.Categorical(counts["work_type"], categories=WORK_TYPE_ORDER, ordered=True)
    counts.sort_values(["job_role", "work_type"], inplace=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    roles = ROLE_ORDER
    x = range(len(roles))
    width = 0.25
    offsets = [-width, 0, width]

    for i, wt in enumerate(WORK_TYPE_ORDER):
        sub = counts[counts["work_type"] == wt].set_index("job_role").reindex(roles)
        bars = ax.bar(
            [xi + offsets[i] for xi in x],
            sub["count"].fillna(0),
            width=width,
            label=wt,
            color=PALETTE[wt],
            edgecolor="white",
        )
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    h + 0.3,
                    str(int(h)),
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

    ax.set_xticks(list(x))
    ax.set_xticklabels(roles)
    ax.set_xlabel("Tech Role")
    ax.set_ylabel("Number of Job Postings")
    ax.set_title("Remote vs Hybrid vs On-site Job Postings by Tech Role\n(Indeed.com · April 2026)", pad=12)
    ax.legend(title="Work Type")
    _save(fig, out_dir / "work_type_distribution.png")


def chart_stacked_pct(df: pd.DataFrame, out_dir: Path) -> None:
    """100 % stacked bar chart."""
    pivot = (
        df.groupby(["job_role", "work_type"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=WORK_TYPE_ORDER, fill_value=0)
    )
    pivot = pivot.loc[[r for r in ROLE_ORDER if r in pivot.index]]
    pct = pivot.div(pivot.sum(axis=1), axis=0) * 100

    fig, ax = plt.subplots(figsize=(10, 6))
    bottom = pd.Series([0.0] * len(pct), index=pct.index)
    for wt in WORK_TYPE_ORDER:
        ax.bar(pct.index, pct[wt], bottom=bottom, label=wt, color=PALETTE[wt], edgecolor="white")
        for i, (role, val) in enumerate(pct[wt].items()):
            if val > 4:
                ax.text(
                    i,
                    bottom.iloc[i] + val / 2,
                    f"{val:.0f}%",
                    ha="center",
                    va="center",
                    fontsize=10,
                    color="white",
                    fontweight="bold",
                )
        bottom = bottom + pct[wt]

    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_ylim(0, 100)
    ax.set_xlabel("Tech Role")
    ax.set_ylabel("Share of Job Postings (%)")
    ax.set_title("Work-Type Share by Tech Role — 100 % Stacked Bar\n(Indeed.com · April 2026)", pad=12)
    ax.legend(title="Work Type", loc="upper right")
    _save(fig, out_dir / "work_type_pct_stacked.png")


def chart_pie_by_role(df: pd.DataFrame, out_dir: Path) -> None:
    """2×2 grid of pie charts, one per role."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle("Work-Type Distribution per Tech Role\n(Indeed.com · April 2026)", fontsize=14, y=1.01)

    for ax, role in zip(axes.flat, ROLE_ORDER):
        sub = df[df["job_role"] == role]["work_type"].value_counts().reindex(WORK_TYPE_ORDER).fillna(0)
        colors = [PALETTE[wt] for wt in sub.index]
        wedges, texts, autotexts = ax.pie(
            sub,
            labels=sub.index,
            autopct="%1.1f%%",
            colors=colors,
            startangle=140,
            pctdistance=0.75,
        )
        for at in autotexts:
            at.set_fontsize(9)
        ax.set_title(role, fontsize=12, fontweight="bold")

    plt.tight_layout()
    _save(fig, out_dir / "work_type_pie_by_role.png")


def chart_overall_pie(df: pd.DataFrame, out_dir: Path) -> None:
    """Single pie chart across all roles combined."""
    counts = df["work_type"].value_counts().reindex(WORK_TYPE_ORDER).fillna(0)
    colors = [PALETTE[wt] for wt in counts.index]

    fig, ax = plt.subplots(figsize=(7, 7))
    wedges, texts, autotexts = ax.pie(
        counts,
        labels=counts.index,
        autopct="%1.1f%%",
        colors=colors,
        startangle=140,
        pctdistance=0.75,
        explode=[0.03] * len(counts),
    )
    for at in autotexts:
        at.set_fontsize(11)
    ax.set_title("Overall Work-Type Distribution — All Tech Roles\n(Indeed.com · April 2026)", fontsize=13, pad=18)
    _save(fig, out_dir / "overall_work_type_pie.png")


def chart_salary_by_work_type(df: pd.DataFrame, out_dir: Path) -> None:
    """Box-plot: salary_avg by work type."""
    salary_df = df[df["salary_avg"].notna()].copy()
    salary_df["work_type"] = pd.Categorical(salary_df["work_type"], categories=WORK_TYPE_ORDER, ordered=True)

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.boxplot(
        data=salary_df,
        x="work_type",
        y="salary_avg",
        hue="work_type",
        palette=PALETTE,
        order=WORK_TYPE_ORDER,
        legend=False,
        ax=ax,
        width=0.5,
        linewidth=1.5,
    )
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x/1000:.0f}k"))
    ax.set_xlabel("Work Type")
    ax.set_ylabel("Estimated Annual Salary (USD)")
    ax.set_title("Salary Distribution by Work Type\n(Indeed.com · April 2026)", pad=12)
    _save(fig, out_dir / "salary_by_work_type.png")


def chart_salary_by_role_work_type(df: pd.DataFrame, out_dir: Path) -> None:
    """Grouped box-plot: salary_avg by role and work type."""
    salary_df = df[df["salary_avg"].notna()].copy()

    fig, ax = plt.subplots(figsize=(12, 6))
    sns.boxplot(
        data=salary_df,
        x="job_role",
        y="salary_avg",
        hue="work_type",
        hue_order=WORK_TYPE_ORDER,
        palette=PALETTE,
        order=ROLE_ORDER,
        ax=ax,
        width=0.6,
        linewidth=1.2,
    )
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x/1000:.0f}k"))
    ax.set_xlabel("Tech Role")
    ax.set_ylabel("Estimated Annual Salary (USD)")
    ax.set_title("Salary Distribution by Role & Work Type\n(Indeed.com · April 2026)", pad=12)
    ax.legend(title="Work Type", loc="upper left")
    _save(fig, out_dir / "salary_by_role_work_type.png")


def chart_postings_over_time(df: pd.DataFrame, out_dir: Path) -> None:
    """Line chart: daily posting count by work type."""
    df2 = df.copy()
    df2["date_posted"] = pd.to_datetime(df2["date_posted"], errors="coerce")
    daily = (
        df2.groupby(["date_posted", "work_type"])
        .size()
        .reset_index(name="count")
    )
    daily["work_type"] = pd.Categorical(daily["work_type"], categories=WORK_TYPE_ORDER, ordered=True)

    fig, ax = plt.subplots(figsize=(12, 5))
    for wt in WORK_TYPE_ORDER:
        sub = daily[daily["work_type"] == wt].sort_values("date_posted")
        ax.plot(sub["date_posted"], sub["count"], label=wt, color=PALETTE[wt], linewidth=2, marker="o", markersize=4)

    ax.set_xlabel("Date Posted")
    ax.set_ylabel("Number of Postings")
    ax.set_title("Daily Job Postings by Work Type — April 2026\n(Indeed.com)", pad=12)
    ax.legend(title="Work Type")
    fig.autofmt_xdate(rotation=30)
    _save(fig, out_dir / "postings_over_time.png")


def chart_heatmap(df: pd.DataFrame, out_dir: Path) -> None:
    """Heatmap of posting counts: roles × work types."""
    pivot = (
        df.groupby(["job_role", "work_type"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=WORK_TYPE_ORDER, fill_value=0)
    )
    pivot = pivot.loc[[r for r in ROLE_ORDER if r in pivot.index]]

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.heatmap(
        pivot,
        annot=True,
        fmt="d",
        cmap="YlOrRd",
        linewidths=0.5,
        linecolor="white",
        ax=ax,
        cbar_kws={"label": "Number of Postings"},
    )
    ax.set_xlabel("Work Type")
    ax.set_ylabel("Tech Role")
    ax.set_title("Heatmap: Job Postings — Role × Work Type\n(Indeed.com · April 2026)", pad=12)
    _save(fig, out_dir / "heatmap_role_work_type.png")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Visualise cleaned Indeed job data.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Path to cleaned CSV.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for output PNGs.")
    args = parser.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.output_dir)

    print(f"[INFO] Reading cleaned data from {input_path} …")
    df = pd.read_csv(input_path)
    print(f"[INFO] Loaded {len(df)} rows.")

    print("[INFO] Generating charts …")
    chart_grouped_bar(df, out_dir)
    chart_stacked_pct(df, out_dir)
    chart_pie_by_role(df, out_dir)
    chart_overall_pie(df, out_dir)
    chart_salary_by_work_type(df, out_dir)
    chart_salary_by_role_work_type(df, out_dir)
    chart_postings_over_time(df, out_dir)
    chart_heatmap(df, out_dir)

    print(f"\n[INFO] All charts saved to {out_dir}/")


if __name__ == "__main__":
    main()
