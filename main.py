import asyncio
import os
import sqlite3
from scrapers.pge import scrape_pge_jobs, fetch_pge_descriptions_batch
from scrapers.smud import scrape_smud_jobs, fetch_smud_descriptions_batch, scrape_all_smud_jobs
from scrapers.kaiser import scrape_kaiser_jobs, fetch_kaiser_descriptions_batch, scrape_all_kaiser_jobs
from database import init_db, save_job, get_new_jobs, update_job_analysis, DB_NAME, reset_failed_analyses, get_jobs_needing_analysis, export_to_excel, generate_job_id
from ai_analyzer import JobAnalyzer
from dotenv import load_dotenv
from config import SEARCH_QUERIES, NOISE_KEYWORDS, ENTRY_LEVEL_INDICATORS, ENABLED_SITES, IGNORE_FIELDS, INTEREST_KEYWORDS


import re

def word_match(keyword, text):
    """
    Check if keyword exists as a whole word in text (not as substring).
    E.g., "IT" should NOT match "conditions" but SHOULD match "IT Analyst"
    """
    # Escape special regex chars and use word boundaries
    pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
    return bool(re.search(pattern, text.lower()))

def filter_jobs(jobs):
    """
    Filters out senior roles and clinical roles, focusing on Tech/Ops roles.
    Uses WHOLE WORD matching to avoid false positives (e.g., "IT" matching "conditions").
    """
    filtered_jobs = []
    
    for job in jobs:
        title = job["title"]
        title_lower = title.lower()
        
        # 1. Immediate discard: Clinical/Medical roles (substring is OK here - more aggressive)
        if any(field.lower() in title_lower for field in IGNORE_FIELDS):
            continue
            
        # 2. Check for noise keywords (Senior, Manager, etc.) - whole word match
        has_noise = any(word_match(keyword, title) for keyword in NOISE_KEYWORDS)
        
        # 3. Check if it's explicitly entry-level (Associate, Junior, etc.) - whole word match
        is_entry_level = any(word_match(indicator, title) for indicator in ENTRY_LEVEL_INDICATORS)
        
        # 4. Check if it's in our interest area (IT, Cyber, Ops, etc.) - whole word match
        is_interesting = any(word_match(interest, title) for interest in INTEREST_KEYWORDS)
        
        # Keep if:
        # (It's Tech/Ops related OR explicitly Entry Level) AND (Not a Senior/Manager role)
        if (is_interesting or is_entry_level) and not has_noise:
            filtered_jobs.append(job)
    
    return filtered_jobs


def select_sites():
    """
    Interactive menu to select which sites to scrape.
    """
    print("\n" + "="*60)
    print("        🎯 AI JOB HUNTER - Multi-Site Job Search")
    print("="*60)
    print("\nSelect sites to scrape:")
    print("  1) PG&E only")
    print("  2) SMUD only")
    print("  3) Kaiser Permanente only")
    print("  4) All (PG&E + SMUD + Kaiser)")
    print("  5) Use config.py settings")
    
    while True:
        choice = input("\nEnter choice (1-5): ").strip()
        if choice == "1":
            return {"pge": True, "smud": False, "kaiser": False}
        elif choice == "2":
            return {"pge": False, "smud": True, "kaiser": False}
        elif choice == "3":
            return {"pge": False, "smud": False, "kaiser": True}
        elif choice == "4":
            return {"pge": True, "smud": True, "kaiser": True}
        elif choice == "5":
            return ENABLED_SITES.copy()
        else:
            print("Invalid choice. Please enter 1, 2, 3, 4, or 5.")


async def main():
    # 1. Initialize
    load_dotenv()
    init_db()
    analyzer = JobAnalyzer()
    
    # 2. Site Selection Menu
    selected_sites = select_sites()
    
    print(f"\nSearch queries: {', '.join(SEARCH_QUERIES)}")
    print(f"Selected sites: {[k.upper() for k, v in selected_sites.items() if v]}")
    print("-"*60)
    
    # 3. Scrape Job Listings from selected sites
    all_raw_jobs = []
    
    # PG&E
    if selected_sites.get("pge", False):
        print("\n📍 Scraping PG&E Jobs...")
        for query in SEARCH_QUERIES:
            raw_jobs = await scrape_pge_jobs(query, headless=False)
            all_raw_jobs.extend(raw_jobs)
    
    # SMUD - scrape ALL categories + keyword searches in one go
    if selected_sites.get("smud", False):
        print("\n📍 Scraping SMUD Jobs (all categories + keywords)...")
        raw_jobs = await scrape_all_smud_jobs(SEARCH_QUERIES, headless=False)
        all_raw_jobs.extend(raw_jobs)
    
    # Kaiser Permanente - scrape ALL California jobs, then filter
    # (Kaiser's "View All" works properly unlike SMUD, so we get everything)
    if selected_sites.get("kaiser", False):
        print("\n📍 Scraping Kaiser Permanente Jobs (California - Full Dump)...")
        raw_jobs = await scrape_kaiser_jobs(headless=False)
        all_raw_jobs.extend(raw_jobs)
    
    # Deduplicate by link
    unique_jobs_dict = {job['link']: job for job in all_raw_jobs}
    unique_jobs = list(unique_jobs_dict.values())
    
    print(f"\n{'='*60}")
    print(f"Total unique jobs scraped: {len(unique_jobs)}")
    
    # 4. Filter Noise
    filtered_jobs = filter_jobs(unique_jobs)
    print(f"Jobs remaining after noise filter: {len(filtered_jobs)}")
    
    # 5. AI Title Pre-Filtering (NEW)
    # If we have a lot of jobs, ask AI to pick the best ones before we fetch descriptions
    if len(filtered_jobs) > 10:
        print(f"\n🤖 AI is pre-filtering {len(filtered_jobs)} titles to save time/requests...")
        # Break into chunks of 100 titles for the AI if needed
        all_ai_filtered = []
        for i in range(0, len(filtered_jobs), 100):
            chunk = filtered_jobs[i:i+100]
            ai_filtered_chunk = analyzer.filter_titles_with_ai(chunk)
            all_ai_filtered.extend(ai_filtered_chunk)
        
        filtered_jobs = all_ai_filtered
        print(f"AI kept {len(filtered_jobs)} relevant titles.")

    # 6. Save New Jobs
    for job in filtered_jobs:
        save_job(job)
    
    # 7. Identify jobs MISSING descriptions (ONLY from our filtered list)
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # We only care about fetching descriptions for the jobs that JUST passed our filters
    jobs_needing_desc = []
    for job in filtered_jobs:
        job_id = generate_job_id(job['link'])
        c.execute("SELECT description FROM jobs WHERE id = ?", (job_id,))
        row = c.fetchone()
        if row and (not row[0] or row[0].strip() == ""):
            jobs_needing_desc.append(job)
    
    conn.close()
    
    if jobs_needing_desc:
        print(f"\nFound {len(jobs_needing_desc)} relevant jobs missing descriptions. Fetching now...")
        
        # Group by source
        pge_to_fetch = [j for j in jobs_needing_desc if j.get('source') == 'PG&E']
        smud_to_fetch = [j for j in jobs_needing_desc if j.get('source') == 'SMUD']
        kaiser_to_fetch = [j for j in jobs_needing_desc if j.get('source') == 'Kaiser Permanente']
        
        # Fetch PG&E descriptions
        if pge_to_fetch:
            descriptions = await fetch_pge_descriptions_batch(pge_to_fetch, headless=False)
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            for job in pge_to_fetch:
                job_id = generate_job_id(job['link'])
                desc = descriptions.get(job['link'], '')
                c.execute("UPDATE jobs SET description = ? WHERE id = ?", (desc, job_id))
            conn.commit()
            conn.close()
        
        # Fetch SMUD descriptions
        if smud_to_fetch:
            descriptions = await fetch_smud_descriptions_batch(smud_to_fetch, headless=False)
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            for job in smud_to_fetch:
                job_id = generate_job_id(job['link'])
                desc = descriptions.get(job['link'], '')
                c.execute("UPDATE jobs SET description = ? WHERE id = ?", (desc, job_id))
            conn.commit()
            conn.close()
        
        # Fetch Kaiser descriptions
        if kaiser_to_fetch:
            # Kaiser is sensitive, so we only fetch a batch
            fetch_limit = 50 
            if len(kaiser_to_fetch) > fetch_limit:
                print(f"  [Kaiser] Limiting fetch to first {fetch_limit} jobs to avoid IP block...")
                kaiser_to_fetch = kaiser_to_fetch[:fetch_limit]
                
            descriptions = await fetch_kaiser_descriptions_batch(kaiser_to_fetch, headless=False)
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            for job in kaiser_to_fetch:
                job_id = generate_job_id(job['link'])
                desc = descriptions.get(job['link'], '')
                if desc:
                    c.execute("UPDATE jobs SET description = ? WHERE id = ?", (desc, job_id))
            conn.commit()
            conn.close()
        
        print(f"Descriptions fetched and saved.")
    
    # 8. AI Analysis
    reset_count = reset_failed_analyses()
    if reset_count > 0:
        print(f"Reset {reset_count} jobs that failed previous analysis.")
    
    # Only analyze jobs that passed our filter AND have descriptions
    jobs_to_analyze = get_jobs_needing_analysis()
    
    # Filter out anything that's not in our 'filtered_jobs' list (to avoid old junk in DB)
    filtered_links = {job['link'] for job in filtered_jobs}
    jobs_to_analyze = [j for j in jobs_to_analyze if j[2] in filtered_links]

    if not jobs_to_analyze:
        print("No NEW relevant jobs requiring AI analysis.")
    else:
        print(f"\n🤖 Analyzing {len(jobs_to_analyze)} jobs with Groq AI (2 sec delay)...")
        for i, job_row in enumerate(jobs_to_analyze, 1):
            job_id, title, link, location, date, desc, score, missing, analysis, status, last_seen, source = job_row
            
            if not desc:
                print(f"  [{i}/{len(jobs_to_analyze)}] Skipping {title} (no description)")
                continue
                
            print(f"  [{i}/{len(jobs_to_analyze)}] {title}...", end=" ", flush=True)
            score, missing_skills, brief_analysis = analyzer.analyze_job(title, desc)
            
            update_job_analysis(job_id, score, missing_skills, brief_analysis)
            print(f"Score: {score}/10")
    
    # 8. Final Output
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
    
    # 9. Export to Excel
    print("\n" + "="*60)
    print("        📁 EXPORTING TO EXCEL")
    print("="*60)
    export_to_excel()

if __name__ == "__main__":
    asyncio.run(main())
