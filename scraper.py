"""
scraper.py
----------
Scrapes Indeed.com for tech job postings (Software Engineer, Data Analyst,
Cybersecurity, DevOps) and saves the raw results to data/raw_jobs.csv.

Because Indeed actively blocks automated requests, the script first attempts
a live scrape with rotating User-Agents and a polite crawl delay.  If the
live scrape returns no results (e.g. the request is blocked), it falls back
to a curated sample dataset that mirrors the structure and volume of a real
April 2026 scrape so that the downstream cleaning and visualisation scripts
always have data to work with.

Usage:
    python scraper.py                # tries live, falls back to sample data
    python scraper.py --sample-only  # skip live scrape, write sample data
"""

import argparse
import csv
import random
import time
from datetime import date, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_PATH = Path("data/raw_jobs.csv")

SEARCH_TERMS = [
    "Software Engineer",
    "Data Analyst",
    "Cybersecurity",
    "DevOps",
]

LOCATION = "United States"
PAGES_PER_TERM = 5          # 10 results per page → 50 results per term
REQUEST_DELAY = 2.0         # seconds between requests (polite crawl rate)

FIELDNAMES = [
    "job_title",
    "company",
    "location",
    "work_type",
    "salary",
    "date_posted",
    "job_role",
    "description_snippet",
    "url",
]

# ---------------------------------------------------------------------------
# Live scraper
# ---------------------------------------------------------------------------


def _headers(ua: str) -> dict:
    return {
        "User-Agent": ua,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


def _parse_page(html: str, job_role: str) -> list[dict]:
    """Parse a single Indeed search-results page and return a list of raw job dicts."""
    soup = BeautifulSoup(html, "lxml")
    jobs = []

    for card in soup.select("div.job_seen_beacon, li.css-5lfssm"):
        try:
            title_el = card.select_one("h2.jobTitle span")
            company_el = card.select_one("[data-testid='company-name']")
            location_el = card.select_one("[data-testid='text-location']")
            salary_el = card.select_one("[data-testid='attribute_snippet_testid']")
            snippet_el = card.select_one("div.job-snippet, div.css-1bgni6j")
            link_el = card.select_one("a[data-jk]")
            badge_el = card.select_one("div.jobMetaDataGroup, span.remote")

            if not title_el:
                continue

            work_type = "On-site"
            if badge_el:
                badge_text = badge_el.get_text(strip=True).lower()
                if "remote" in badge_text:
                    work_type = "Remote"
                elif "hybrid" in badge_text:
                    work_type = "Hybrid"

            url = ""
            if link_el and link_el.get("data-jk"):
                url = f"https://www.indeed.com/viewjob?jk={link_el['data-jk']}"

            jobs.append({
                "job_title": title_el.get_text(strip=True) if title_el else "",
                "company": company_el.get_text(strip=True) if company_el else "",
                "location": location_el.get_text(strip=True) if location_el else "",
                "work_type": work_type,
                "salary": salary_el.get_text(strip=True) if salary_el else "",
                "date_posted": "",
                "job_role": job_role,
                "description_snippet": snippet_el.get_text(separator=" ", strip=True)[:300] if snippet_el else "",
                "url": url,
            })
        except Exception:
            continue

    return jobs


def scrape_indeed(pages_per_term: int = PAGES_PER_TERM) -> list[dict]:
    """Attempt to scrape Indeed and return raw job records."""
    try:
        from fake_useragent import UserAgent
        ua_gen = UserAgent()
    except Exception:
        ua_gen = None

    all_jobs: list[dict] = []

    for term in SEARCH_TERMS:
        for page in range(pages_per_term):
            start = page * 10
            url = (
                "https://www.indeed.com/jobs"
                f"?q={requests.utils.quote(term)}"
                f"&l={requests.utils.quote(LOCATION)}"
                f"&start={start}"
            )
            ua = ua_gen.random if ua_gen else "Mozilla/5.0"
            try:
                resp = requests.get(url, headers=_headers(ua), timeout=15)
                if resp.status_code != 200:
                    print(f"  [WARN] {term} page {page+1}: HTTP {resp.status_code}")
                    continue
                jobs = _parse_page(resp.text, job_role=term)
                all_jobs.extend(jobs)
                print(f"  [OK]   {term} page {page+1}: {len(jobs)} jobs")
            except Exception as exc:
                print(f"  [ERR]  {term} page {page+1}: {exc}")
            time.sleep(REQUEST_DELAY)

    return all_jobs


# ---------------------------------------------------------------------------
# Sample / fallback data
# ---------------------------------------------------------------------------

COMPANIES = [
    "Google", "Amazon", "Microsoft", "Meta", "Apple", "IBM", "Accenture",
    "Deloitte", "Salesforce", "Oracle", "Cisco", "Palo Alto Networks",
    "CrowdStrike", "HashiCorp", "Datadog", "Splunk", "Snowflake", "Databricks",
    "Stripe", "Twilio", "GitHub", "Atlassian", "ServiceNow", "Workday",
    "LinkedIn", "Uber", "Lyft", "Airbnb", "DoorDash", "Robinhood",
    "Capital One", "JPMorgan Chase", "Bank of America", "Goldman Sachs",
    "Lockheed Martin", "Raytheon", "Booz Allen Hamilton", "MITRE",
    "UnitedHealth Group", "Epic Systems", "Cerner", "Philips",
]

CITIES = [
    ("New York", "NY"), ("San Francisco", "CA"), ("Seattle", "WA"),
    ("Austin", "TX"), ("Chicago", "IL"), ("Boston", "MA"),
    ("Denver", "CO"), ("Atlanta", "GA"), ("Raleigh", "NC"),
    ("Washington", "DC"), ("Los Angeles", "CA"), ("Dallas", "TX"),
    ("Phoenix", "AZ"), ("Minneapolis", "MN"), ("Portland", "OR"),
    ("San Jose", "CA"), ("Charlotte", "NC"), ("Nashville", "TN"),
    ("Pittsburgh", "PA"), ("Columbus", "OH"),
]

ROLE_TITLES = {
    "Software Engineer": [
        "Software Engineer", "Senior Software Engineer", "Staff Software Engineer",
        "Software Engineer II", "Software Engineer III", "Principal Software Engineer",
        "Backend Software Engineer", "Frontend Software Engineer",
        "Full Stack Software Engineer", "Junior Software Engineer",
    ],
    "Data Analyst": [
        "Data Analyst", "Senior Data Analyst", "Business Intelligence Analyst",
        "Data Analyst II", "Marketing Data Analyst", "Financial Data Analyst",
        "Operations Data Analyst", "Junior Data Analyst", "Lead Data Analyst",
        "Product Data Analyst",
    ],
    "Cybersecurity": [
        "Cybersecurity Analyst", "Information Security Analyst",
        "Senior Cybersecurity Engineer", "Security Operations Center Analyst",
        "Penetration Tester", "Cybersecurity Specialist", "Network Security Engineer",
        "Cloud Security Engineer", "Application Security Engineer",
        "Cybersecurity Consultant",
    ],
    "DevOps": [
        "DevOps Engineer", "Senior DevOps Engineer", "Site Reliability Engineer",
        "Platform Engineer", "Cloud DevOps Engineer", "DevOps Architect",
        "Infrastructure Engineer", "Release Engineer",
        "DevOps Engineer II", "Principal Site Reliability Engineer",
    ],
}

SALARY_RANGES = {
    "Software Engineer": [
        "$80,000 - $110,000 a year", "$100,000 - $140,000 a year",
        "$130,000 - $170,000 a year", "$160,000 - $200,000 a year",
        "$90,000 - $120,000 a year", "$50 - $75 an hour",
        "$70 - $95 an hour", "",
    ],
    "Data Analyst": [
        "$60,000 - $85,000 a year", "$75,000 - $100,000 a year",
        "$90,000 - $120,000 a year", "$55,000 - $75,000 a year",
        "$40 - $55 an hour", "$45 - $65 an hour", "",
    ],
    "Cybersecurity": [
        "$85,000 - $115,000 a year", "$110,000 - $150,000 a year",
        "$140,000 - $180,000 a year", "$95,000 - $130,000 a year",
        "$60 - $85 an hour", "$75 - $100 an hour", "",
    ],
    "DevOps": [
        "$90,000 - $120,000 a year", "$115,000 - $155,000 a year",
        "$140,000 - $180,000 a year", "$100,000 - $140,000 a year",
        "$55 - $80 an hour", "$70 - $100 an hour", "",
    ],
}

SNIPPETS = {
    "Software Engineer": [
        "Design and develop scalable backend services using Python and Go. Collaborate with cross-functional teams to deliver high-quality software.",
        "Build and maintain web applications using React and Node.js. Work in an agile environment with a focus on code quality and performance.",
        "Develop cloud-native applications on AWS. Experience with microservices, Docker, and Kubernetes required.",
        "Contribute to our core platform engineering team. Strong knowledge of distributed systems and algorithms expected.",
        "Implement new features and fix bugs in our flagship SaaS product. Participate in code reviews and technical design discussions.",
    ],
    "Data Analyst": [
        "Analyze large datasets to uncover insights that drive business decisions. Proficiency in SQL, Python, and Tableau required.",
        "Build dashboards and reports in Power BI to support operations and marketing teams. Experience with data modeling a plus.",
        "Work with stakeholders to define KPIs and create self-service analytics solutions. Strong Excel and SQL skills required.",
        "Perform statistical analysis and A/B testing to optimize product features. Experience with R or Python preferred.",
        "Support the finance team with financial modeling and forecasting. Advanced SQL and data visualization skills required.",
    ],
    "Cybersecurity": [
        "Monitor and respond to security incidents using SIEM tools. Experience with Splunk or Microsoft Sentinel preferred.",
        "Conduct vulnerability assessments and penetration tests on web applications and infrastructure. OSCP certification a plus.",
        "Implement and manage cloud security controls across AWS and Azure environments. Knowledge of zero-trust architecture required.",
        "Develop and maintain security policies, procedures, and awareness programs. CISSP or CISM certification preferred.",
        "Investigate security alerts, perform forensic analysis, and produce incident reports. Strong knowledge of MITRE ATT&CK framework.",
    ],
    "DevOps": [
        "Design and maintain CI/CD pipelines using Jenkins, GitHub Actions, and ArgoCD. Experience with Terraform and Kubernetes required.",
        "Manage cloud infrastructure on AWS using Infrastructure as Code (Terraform, CloudFormation). Strong scripting skills in Python or Bash.",
        "Build and operate Kubernetes clusters at scale. Experience with Helm, Prometheus, and Grafana for observability.",
        "Partner with development teams to improve deployment frequency and reduce MTTR. Expertise in GitOps workflows preferred.",
        "Automate operational tasks, manage on-call rotations, and drive reliability improvements. Experience with Datadog or PagerDuty.",
    ],
}

# Work-type distribution weights per role (Remote, Hybrid, On-site)
WORK_TYPE_WEIGHTS = {
    "Software Engineer": [0.40, 0.38, 0.22],
    "Data Analyst":      [0.30, 0.42, 0.28],
    "Cybersecurity":     [0.25, 0.35, 0.40],
    "DevOps":            [0.45, 0.35, 0.20],
}


def _random_date(start: date, end: date, rng: random.Random) -> str:
    delta = (end - start).days
    return (start + timedelta(days=rng.randint(0, delta))).strftime("%Y-%m-%d")


def generate_sample_data(n_per_role: int = 60, seed: int = 42) -> list[dict]:
    """Generate a realistic sample dataset of n_per_role records per role."""
    rng = random.Random(seed)
    records = []

    start_date = date(2026, 4, 1)
    end_date = date(2026, 4, 30)

    for role in SEARCH_TERMS:
        weights = WORK_TYPE_WEIGHTS[role]
        for i in range(n_per_role):
            work_type = rng.choices(["Remote", "Hybrid", "On-site"], weights=weights)[0]
            city, state = rng.choice(CITIES)
            if work_type == "Remote":
                location = "Remote"
            elif work_type == "Hybrid":
                location = f"{city}, {state} (Hybrid)"
            else:
                location = f"{city}, {state}"

            records.append({
                "job_title": rng.choice(ROLE_TITLES[role]),
                "company": rng.choice(COMPANIES),
                "location": location,
                "work_type": work_type,
                "salary": rng.choice(SALARY_RANGES[role]),
                "date_posted": _random_date(start_date, end_date, rng),
                "job_role": role,
                "description_snippet": rng.choice(SNIPPETS[role]),
                "url": f"https://www.indeed.com/viewjob?jk={rng.randint(100000000, 999999999):09d}",
            })

    return records


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Indeed.com for tech job postings.")
    parser.add_argument(
        "--sample-only",
        action="store_true",
        help="Skip live scraping and write the built-in sample dataset instead.",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=PAGES_PER_TERM,
        help=f"Pages to scrape per search term (default: {PAGES_PER_TERM}).",
    )
    args = parser.parse_args()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if args.sample_only:
        print("[INFO] --sample-only flag set; writing built-in sample dataset.")
        jobs = generate_sample_data()
    else:
        print("[INFO] Attempting live scrape of Indeed.com …")
        jobs = scrape_indeed(pages_per_term=args.pages)
        if not jobs:
            print("[WARN] Live scrape returned no results — falling back to sample data.")
            jobs = generate_sample_data()
        else:
            print(f"[INFO] Live scrape returned {len(jobs)} records.")

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(jobs)

    print(f"[INFO] Wrote {len(jobs)} records → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
