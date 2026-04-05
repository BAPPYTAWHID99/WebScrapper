# Remote vs Hybrid Tech Jobs Analysis (April 2026)

## Project Overview
This repository contains the data and code for my individual research project analyzing the distribution of **Remote**, **Hybrid**, and **On-site** job postings in four high-demand IT categories:

- Software Engineer
- Data Analyst
- Cybersecurity
- DevOps

**Key Finding:** In April 2026, **Remote** jobs dominated (58%), followed by **Hybrid** (42%), with **zero** On-site roles detected despite targeted filtering.

## Repository Contents

- **`indeed_scraper.py`** – Selenium-based web scraper that collects job postings from Indeed.com using stable URL filters for Remote, Hybrid, and On-site.
- **`clean_data.py`** – Data cleaning, deduplication, salary extraction, and visualization script using pandas and matplotlib.
- **`job_research_2026.csv`** – Raw scraped data (125 records).
- **`jobs_remote_vs_hybrid_clean_final.csv`** – Cleaned final dataset (107 high-quality records).
- **`remote_vs_hybrid_chart.png`** – Bar chart showing Remote vs Hybrid job counts.
- **`job_postings_analysis.xlsx`** – Excel version of the cleaned data + summary statistics (added for easy viewing).

## Methodology
- **Data Source**: Indeed.com (real-time scraping in April 2026)
- **Tools**: Python 3.13, Selenium WebDriver, pandas, matplotlib
- **Scraping Approach**: Category-specific searches with official Indeed remote/hybrid filters + polite delays
- **Cleaning**: Duplicate removal, text standardization, and basic salary parsing

## Key Results
- Total cleaned jobs: **107**
- Remote: **62** (58%)
- Hybrid: **45** (42%)
- On-site: **0**
- Top companies: CACI, KPMG, TikTok, Veeva Systems

## How to Reproduce
1. Install dependencies:
   ```bash
   pip install selenium webdriver-manager pandas matplotlib
