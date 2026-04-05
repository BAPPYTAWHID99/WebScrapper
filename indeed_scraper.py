import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def scrape_indeed(base_url, job_type, category, max_pages=5):
    options = Options()
    # options.add_argument("--headless=new")   # ← Comment out headless (recommended right now)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    jobs = []
    current_url = base_url
    
    for page in range(1, max_pages + 1):
        print(f" [{category}] Scraping page {page} - {job_type}...")
        driver.get(current_url)
        time.sleep(random.uniform(6, 10))  # Longer polite delay
        
        # Scroll to trigger lazy loading
        driver.execute_script("window.scrollTo(0, 600);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.7);")
        time.sleep(2)
        
        try:
            # Wait for at least one job card
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.job_seen_beacon"))
            )
        except:
            print(f"   ⚠️ No cards found for {category} {job_type} (page {page}). Moving on.")
            break
        
        job_cards = driver.find_elements(By.CSS_SELECTOR, "div.job_seen_beacon")
        print(f"   Found {len(job_cards)} job cards")
        
        for card in job_cards:
            try:
                # Improved title extraction (handles <span> inside <a>)
                title_elem = card.find_element(By.CSS_SELECTOR, "h2.jobTitle a")
                title = title_elem.text.strip() or title_elem.find_element(By.TAG_NAME, "span").text.strip()
                if not title or len(title) < 5:
                    continue
                
                link = title_elem.get_attribute("href")
                
                # Company (data-testid is stable)
                company_elem = card.find_elements(By.CSS_SELECTOR, "span[data-testid='company-name']")
                company = company_elem[0].text.strip() if company_elem else "N/A"
                
                # Location
                location_elem = card.find_elements(By.CSS_SELECTOR, "div[data-testid='text-location']")
                location = location_elem[0].text.strip() if location_elem else "N/A"
                
                # Salary
                salary_elem = card.find_elements(By.CSS_SELECTOR, "div[data-testid='salary-snippet']")
                salary = salary_elem[0].text.strip() if salary_elem else "N/A"
                
                jobs.append({
                    'category': category,
                    'title': title,
                    'company': company,
                    'location': location,
                    'salary': salary,
                    'type': job_type,
                    'link': link,
                    'source': 'Indeed'
                })
            except Exception as e:
                continue  # Skip broken cards
        
        # Next page
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, "a[data-testid='pagination-button-next']")
            if next_button.get_attribute("aria-disabled") == "true":
                break
            current_url = next_button.get_attribute("href")
            time.sleep(random.uniform(4, 7))
        except:
            break  # No more pages
    
    driver.quit()
    return jobs

#  CONFIGURATION 
categories = ["Software Engineer", "Data Analyst", "Cybersecurity", "DevOps"]
all_jobs = []

for cat in categories:
    query = cat.replace(" ", "+")
    
    # Remote filter (updated stable parameter)
    remote_url = f"https://www.indeed.com/jobs?q={query}&remotejob=032b3046-06a3-4876-8dfd-474eb5e7ed11"
    all_jobs.extend(scrape_indeed(remote_url, "Remote", cat, max_pages=6))
    
    # Hybrid filter
    hybrid_url = f"https://www.indeed.com/jobs?q={query}&sc=0kf%3Aattr(DSQF7)%3B"
    all_jobs.extend(scrape_indeed(hybrid_url, "Hybrid", cat, max_pages=6))
    
    # On-site (exclude remote/hybrid)
    onsite_url = f"https://www.indeed.com/jobs?q={query}&sc=0kf%3Aocc(NOT+remote)%3B"
    all_jobs.extend(scrape_indeed(onsite_url, "On-site", cat, max_pages=4))

# SAVE & ANALYZE
df = pd.DataFrame(all_jobs)

if df.empty:
    print("No data collected at all. Try running again with browser visible.")
else:
    df.to_csv("job_research_2026.csv", index=False)
    print(f"\nSUCCESS! Collected {len(df)} jobs. File 'job_research_2026.csv' created.")
    
    # Safe groupby
    if 'category' in df.columns and 'type' in df.columns:
        print("\nJobs by Category and Type:")
        print(df.groupby(['category', 'type']).size())
    else:
        print("Warning: Missing category or type columns.")

print("\nTop companies:")
print(df['company'].value_counts().head(10))