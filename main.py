import asyncio
import os
import sqlite3
from scrapers.pge import scrape_pge_jobs, fetch_pge_descriptions_batch
from scrapers.smud import scrape_smud_jobs, fetch_smud_descriptions_batch
from database import init_db, save_job, get_new_jobs, update_job_analysis, DB_NAME, reset_failed_analyses, get_jobs_needing_analysis, export_to_excel
from ai_analyzer import JobAnalyzer
from dotenv import load_dotenv
from config import SEARCH_QUERIES, NOISE_KEYWORDS, ENTRY_LEVEL_INDICATORS, ENABLED_SITES


def filter_jobs(jobs):
    """
    Filters out senior/expert/principal roles unless they're explicitly entry-level.
    """
    filtered_jobs = []
    
    for job in jobs:
        title = job["title"]
        title_lower = title.lower()
        
        # Check if it's an entry-level or foot-in-door role (overrides noise)
        is_entry_level = any(indicator.lower() in title_lower for indicator in ENTRY_LEVEL_INDICATORS)
        
        # Check for noise keywords
        has_noise = any(keyword.lower() in title_lower for keyword in NOISE_KEYWORDS)
        
        # Keep if it's explicitly entry-level OR has no noise
        if is_entry_level or not has_noise:
            filtered_jobs.append(job)
    
    return filtered_jobs


async def main():
    # 1. Initialize
    load_dotenv()
    init_db()
    analyzer = JobAnalyzer()
    
    print("\n" + "="*60)
    print("        🎯 AI JOB HUNTER - Multi-Site Job Search")
    print("="*60)
    
    # 2. Scrape Job Listings from all enabled sites
    all_raw_jobs = []
    print(f"\nSearch queries: {', '.join(SEARCH_QUERIES)}")
    print(f"Enabled sites: {[k for k, v in ENABLED_SITES.items() if v]}")
    print("-"*60)
    
    # PG&E
    if ENABLED_SITES.get("pge", False):
        print("\n📍 Scraping PG&E Jobs...")
        for query in SEARCH_QUERIES:
            raw_jobs = await scrape_pge_jobs(query, headless=False)
            all_raw_jobs.extend(raw_jobs)
    
    # SMUD
    if ENABLED_SITES.get("smud", False):
        print("\n📍 Scraping SMUD Jobs...")
        for query in SEARCH_QUERIES:
            raw_jobs = await scrape_smud_jobs(query, headless=False)
            all_raw_jobs.extend(raw_jobs)
    
    # Deduplicate by link
    unique_jobs_dict = {job['link']: job for job in all_raw_jobs}
    unique_jobs = list(unique_jobs_dict.values())
    
    print(f"\n{'='*60}")
    print(f"Total unique jobs scraped: {len(unique_jobs)}")
    
    # 3. Filter Noise
    filtered_jobs = filter_jobs(unique_jobs)
    print(f"Jobs remaining after noise filter: {len(filtered_jobs)}")
    
    # 4. Save New Jobs & Identify which need descriptions
    new_jobs_list = []
    for job in filtered_jobs:
        if save_job(job):
            new_jobs_list.append(job)
    
    print(f"\nFound {len(new_jobs_list)} NEW jobs (not seen before).")
    
    # 5. Fetch descriptions for new jobs in BATCH (one browser per site)
    if new_jobs_list:
        print(f"Fetching job descriptions...")
        
        # Group by source
        pge_jobs = [j for j in new_jobs_list if j.get('source') == 'PG&E']
        smud_jobs = [j for j in new_jobs_list if j.get('source') == 'SMUD']
        other_jobs = [j for j in new_jobs_list if j.get('source') not in ['PG&E', 'SMUD']]
        
        # Fetch PG&E descriptions
        if pge_jobs:
            descriptions = await fetch_pge_descriptions_batch(pge_jobs, headless=False)
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            for job in pge_jobs:
                job_id = job['link'].split('/')[-1] if '/' in job['link'] else job['link']
                desc = descriptions.get(job['link'], '')
                c.execute("UPDATE jobs SET description = ? WHERE id = ?", (desc, job_id))
            conn.commit()
            conn.close()
        
        # Fetch SMUD descriptions
        if smud_jobs:
            descriptions = await fetch_smud_descriptions_batch(smud_jobs, headless=False)
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            for job in smud_jobs:
                job_id = job['link'].split('/')[-1] if '/' in job['link'] else job['link']
                desc = descriptions.get(job['link'], '')
                c.execute("UPDATE jobs SET description = ? WHERE id = ?", (desc, job_id))
            conn.commit()
            conn.close()
        
        # Handle jobs without source (legacy)
        if other_jobs:
            descriptions = await fetch_pge_descriptions_batch(other_jobs, headless=False)
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            for job in other_jobs:
                job_id = job['link'].split('/')[-1] if '/' in job['link'] else job['link']
                desc = descriptions.get(job['link'], '')
                c.execute("UPDATE jobs SET description = ? WHERE id = ?", (desc, job_id))
            conn.commit()
            conn.close()
        
        print(f"Descriptions fetched and saved.")
    
    # 6. AI Analysis
    reset_count = reset_failed_analyses()
    if reset_count > 0:
        print(f"Reset {reset_count} jobs that failed previous analysis.")
    
    jobs_to_analyze = get_jobs_needing_analysis()
    if not jobs_to_analyze:
        print("No jobs requiring AI analysis.")
    else:
        print(f"\n🤖 Analyzing {len(jobs_to_analyze)} jobs with Groq AI (2 sec delay)...")
        for i, job_row in enumerate(jobs_to_analyze, 1):
            job_id, title, link, location, date, desc, score, missing, analysis, status, last_seen = job_row
            
            if not desc:
                print(f"  [{i}/{len(jobs_to_analyze)}] Skipping {title} (no description)")
                continue
                
            print(f"  [{i}/{len(jobs_to_analyze)}] {title}...", end=" ", flush=True)
            score, missing_skills, brief_analysis = analyzer.analyze_job(title, desc)
            
            update_job_analysis(job_id, score, missing_skills, brief_analysis)
            print(f"Score: {score}/10")
    
    # 7. Final Output
    print("\n" + "="*60)
    print("        📊 TOP RECOMMENDED MATCHES")
    print("="*60)
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT title, location, match_score, missing_skills, link 
        FROM jobs 
        WHERE match_score >= 1 
        ORDER BY match_score DESC 
        LIMIT 10
    """)
    top_matches = c.fetchall()
    conn.close()
    
    if not top_matches:
        print("No jobs analyzed yet. Make sure you have a GROQ_API_KEY in your .env file.")
    else:
        for title, loc, score, missing, link in top_matches:
            indicator = "⭐" if score >= 8 else "✅" if score >= 5 else "📋"
            print(f"\n{indicator} [{score}/10] {title}")
            print(f"   Location: {loc}")
            print(f"   Missing: {missing if missing else 'None'}")
            print(f"   Link: {link}")
    
    # 8. Export to Excel
    print("\n" + "="*60)
    print("        📁 EXPORTING TO EXCEL")
    print("="*60)
    export_to_excel()

if __name__ == "__main__":
    asyncio.run(main())
