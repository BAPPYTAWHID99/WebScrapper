import pandas as pd
import re
import matplotlib.pyplot as plt
from pathlib import Path

# LOAD ALL RAW FILES
raw_files = ["job_research_2026.csv"]

dfs = []
for file in raw_files:
    file_path = Path(file)
    if file_path.exists():
        try:
            df_temp = pd.read_csv(file_path)
            print(f"Loaded {len(df_temp)} rows from {file}")
            dfs.append(df_temp)
        except Exception as e:
            print(f"Error loading {file}: {e}")

if not dfs:
    print("No raw files found. Run your scraper first.")
    exit()

df = pd.concat(dfs, ignore_index=True)

print(f"\nTotal raw rows before cleaning: {len(df)}")

# DATA CLEANING STEPS

# 1. Drop completely empty or useless rows
df = df.dropna(subset=['title', 'company'])
df = df[df['title'].str.strip().str.len() > 5]      # Remove very short titles
df = df[df['company'].str.strip() != ""]            # Remove blank companies
df = df[df['company'].str.lower() != "n/a"]

# 2. Standardize text (remove extra spaces, normalize case for cleaning)
df['title'] = df['title'].str.strip()
df['company'] = df['company'].str.strip()
df['location'] = df['location'].str.strip().fillna("N/A")
df['type'] = df['type'].str.strip().fillna("Unknown")

# 3. Remove exact duplicates (same job likely posted on multiple platforms)
df = df.drop_duplicates(subset=['title', 'company', 'link'], keep='first')

# 4. Remove near-duplicates (very similar titles + same company)
# This helps reduce redundancy
df['title_lower'] = df['title'].str.lower()
df = df.drop_duplicates(subset=['title_lower', 'company'], keep='first')
df = df.drop(columns=['title_lower'])

# 5. Basic salary cleaning (extract approximate yearly number when possible)
def extract_salary(salary_str):
    if pd.isna(salary_str) or salary_str == "N/A":
        return None
    # Find numbers like 120000, $120k, 100-150k etc.
    numbers = re.findall(r'(\d{1,3}(?:,\d{3})*|\d+k)', str(salary_str).replace(',', ''))
    if numbers:
        # Take the highest number and convert k to thousands
        max_num = max(numbers, key=lambda x: int(x.replace('k','000').replace(',','')))
        return int(max_num.replace('k','000').replace(',',''))
    return None

df['salary_numeric'] = df['salary'].apply(extract_salary)

# 6. Add a simple 'has_salary' flag and clean summary if needed
df['has_salary_info'] = df['salary_numeric'].notna()
df['source'] = df.get('source', 'Indeed')  # Ensure source column exists

print(f"After cleaning: {len(df)} high-quality rows")

# ANALYSIS & STATS
print("\n=== Remote vs Hybrid vs On-site Count ===")
print(df['type'].value_counts())

print("\n=== Jobs by Category and Type ===")
if {'category', 'type'}.issubset(df.columns):
    print(df.groupby(['category', 'type']).size())

print("\n=== Top 10 Companies ===")
print(df['company'].value_counts().head(10))

print("\n=== Percentage with Salary Info ===")
print(df.groupby('type')['has_salary_info'].mean() * 100)

# SAVE CLEAN DATA
df.to_csv("jobs_remote_vs_hybrid_clean_final.csv", index=False)
print("\nCleaned data saved to 'jobs_remote_vs_hybrid_clean_final.csv'")

# VISUALIZATION FOR POWERPOINT
plt.figure(figsize=(10, 6))
type_counts = df['type'].value_counts()
type_counts.plot(kind='bar', color=['#1f77b4', '#ff7f0e', '#2ca02c'])
plt.title('Remote vs Hybrid vs On-site Job Postings (April 2026 Data)')
plt.ylabel('Number of Jobs')
plt.xlabel('Work Type')
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig('remote_vs_hybrid_chart.png')
plt.show()

print("Chart saved as 'remote_vs_hybrid_chart.png' — use this in your slides!")