import asyncio
import os
import sqlite3
from scrapers.pge import scrape_pge_jobs, fetch_pge_descriptions_batch
from scrapers.smud import scrape_smud_jobs, fetch_smud_descriptions_batch, scrape_all_smud_jobs
from scrapers.kaiser import scrape_kaiser_jobs, fetch_kaiser_descriptions_batch, scrape_all_kaiser_jobs
from scrapers.state_ca import scrape_state_ca_jobs, fetch_state_ca_descriptions_batch, scrape_all_state_ca_jobs
from database import init_db, save_job, get_new_jobs, update_job_analysis, DB_NAME, reset_failed_analyses, get_jobs_needing_analysis, export_to_excel, generate_job_id
from ai_analyzer import JobAnalyzer
from dotenv import load_dotenv
from config import SEARCH_QUERIES, NOISE_KEYWORDS, ENTRY_LEVEL_INDICATORS, ENABLED_SITES, IGNORE_FIELDS, INTEREST_KEYWORDS

# Import State CA config if available
try:
    from config import STATE_CA_LOCATION, STATE_CA_KEYWORDS
except ImportError:
    STATE_CA_LOCATION = "Sacramento County"  # Default location
    STATE_CA_KEYWORDS = ["Information", "IT", "Security", "Analyst"]


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
    Filters jobs based on keywords defined in config.py.
    """
    filtered_jobs = []
    
    for job in jobs:
        title = job["title"]
        title_lower = title.lower()
        
        # 1. Immediate discard: keywords in IGNORE_FIELDS (Medical/Nursing/etc.)
        if any(field.lower() in title_lower for field in IGNORE_FIELDS):
            continue
            
        # 2. Check if it's in the interest area keywords (Cyber, IT, Analyst, etc.)
        # If it's interesting, we keep it REGARDLESS of noise (Senior/Manager)
        # because the user wants the AI to decide, not a dumb string filter.
        is_interesting = any(word_match(interest, title) for interest in INTEREST_KEYWORDS)
        
        # 3. Check if it matches an entry-level indicator
        is_entry_level = any(word_match(indicator, title) for indicator in ENTRY_LEVEL_INDICATORS)
        
        # Keep if it's interesting OR entry level.
        # We only apply NOISE_KEYWORDS if it's NEITHER interesting nor entry level.
        has_noise = any(word_match(keyword, title) for keyword in NOISE_KEYWORDS)
        
        if is_interesting or is_entry_level:
            filtered_jobs.append(job)
        elif not has_noise:
            # If it's not explicitly interesting but also doesn't have noise, keep it anyway
            filtered_jobs.append(job)
    
    return filtered_jobs


def select_sites():
    """
    Interactive menu to select which sites to scrape.
    """
    print("\n" + "="*60)
    print("        🎯 AI JOB HUNTER - Multi-Site Job Search")
    print("="*60)
    print("\nSelect options:")
    print("  1) PG&E only")
    print("  2) SMUD only")
    print("  3) Kaiser Permanente only")
    print("  4) State of California only")
    print("  5) All sites (PG&E + SMUD + Kaiser + State CA)")
    print("  6) Use config.py settings")
    print("  7) RE-ANALYZE DATABASE (Skip scraping, run AI on existing jobs)")
    
    while True:
        choice = input("\nEnter choice (1-7): ").strip()
        if choice == "1":
            return {"pge": True, "smud": False, "kaiser": False, "state_ca": False}, False
        elif choice == "2":
            return {"pge": False, "smud": True, "kaiser": False, "state_ca": False}, False
        elif choice == "3":
            return {"pge": False, "smud": False, "kaiser": True, "state_ca": False}, False
        elif choice == "4":
            return {"pge": False, "smud": False, "kaiser": False, "state_ca": True}, False
        elif choice == "5":
            return {"pge": True, "smud": True, "kaiser": True, "state_ca": True}, False
        elif choice == "6":
            return ENABLED_SITES.copy(), False
        elif choice == "7":
            return {}, True
        else:
            print("Invalid choice. Please enter 1-7.")


async def main():
    # 1. Initialize
    load_dotenv()
    init_db()
    analyzer = JobAnalyzer()
    
    # 2. Site Selection Menu
    selected_sites, reanalyze_only = select_sites()
    
    if not reanalyze_only:
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
        
        # State of California - scrape multiple keywords with configured location
        if selected_sites.get("state_ca", False):
            print(f"\n📍 Scraping State of California Jobs ({STATE_CA_LOCATION or 'All Locations'})...")
            raw_jobs = await scrape_state_ca_jobs(
                search_queries=STATE_CA_KEYWORDS, 
                location=STATE_CA_LOCATION, 
                headless=False
            )
            all_raw_jobs.extend(raw_jobs)
        
        # Deduplicate by link
        unique_jobs_dict = {job['link']: job for job in all_raw_jobs}
        unique_jobs = list(unique_jobs_dict.values())
        
        print(f"\n{'='*60}")
        print(f"Total unique jobs scraped: {len(unique_jobs)}")
        
        # 6. Save ALL New Jobs to DB (so we don't lose them even if filter is picky)
        print(f"Saving {len(unique_jobs)} jobs to database...")
        for job in unique_jobs:
            save_job(job)
            
        # 4. Filter Noise
        filtered_jobs = filter_jobs(unique_jobs)
        print(f"Jobs remaining after noise filter: {len(filtered_jobs)}")
        
        # 5. AI Title Pre-Filtering (NEW)
        # If we have a lot of jobs, ask AI to pick the best ones before we fetch descriptions
        if len(filtered_jobs) > 10:
            print(f"\n🤖 AI is pre-filtering {len(filtered_jobs)} titles to save time/requests...")
            # Break into chunks of 100 titles for the AI if needed
            all_ai_filtered = []
            skipped_jobs = []
            
            for i in range(0, len(filtered_jobs), 100):
                chunk = filtered_jobs[i:i+100]
                ai_filtered_chunk = analyzer.filter_titles_with_ai(chunk)
                all_ai_filtered.extend(ai_filtered_chunk)
                
                # Identify which were skipped in this chunk
                kept_links = {j['link'] for j in ai_filtered_chunk}
                for j in chunk:
                    if j['link'] not in kept_links:
                        skipped_jobs.append(j)
            
            if skipped_jobs:
                print(f"AI skipped {len(skipped_jobs)} titles it thought were irrelevant (e.g., medical, non-tech).")
                print(f"Example skipped: {', '.join([j['title'] for j in skipped_jobs[:3]])}...")
                
                # Mark skipped jobs in DB so they don't appear in 'needed analysis' but are still there
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                for j in skipped_jobs:
                    job_id = generate_job_id(j['link'])
                    c.execute("UPDATE jobs SET status = 'skipped_ai_title' WHERE id = ?", (job_id,))
                conn.commit()
                conn.close()
            
            filtered_jobs = all_ai_filtered
            print(f"AI kept {len(filtered_jobs)} relevant titles for further analysis.")
    else:
        print("\n📍 RE-ANALYZE MODE: Skipping scraping, pulling jobs from database...")
        print("Which source would you like to re-analyze?")
        print("  1) State of California")
        print("  2) PG&E")
        print("  3) SMUD")
        print("  4) Kaiser Permanente")
        print("  5) ALL")
        
        source_choice = input("\nEnter choice (1-5): ").strip()
        source_map = {"1": "State of California", "2": "PG&E", "3": "SMUD", "4": "Kaiser Permanente"}
        target_source = source_map.get(source_choice)
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        if target_source:
            print(f"Filtering for source: {target_source}")
            # Include jobs that were previously skipped by AI title filter so they can be re-analyzed
            c.execute("SELECT title, link, location, source FROM jobs WHERE source = ? AND (match_score IS NULL OR match_score = 0 OR status = 'skipped_ai_title')", (target_source,))
        else:
            print("Analyzing all sources...")
            c.execute("SELECT title, link, location, source FROM jobs WHERE (match_score IS NULL OR match_score = 0 OR status = 'skipped_ai_title')")
        
        rows = c.fetchall()
        conn.close()
        
        filtered_jobs = []
        for row in rows:
            filtered_jobs.append({
                'title': row[0],
                'link': row[1],
                'location': row[2],
                'source': row[3]
            })
        print(f"Found {len(filtered_jobs)} jobs in DB to analyze.")
    
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
        state_ca_to_fetch = [j for j in jobs_needing_desc if j.get('source') == 'State of California']
        
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
        
        # Fetch State CA descriptions
        if state_ca_to_fetch:
            # State CA has rate limiting built into the scraper (10s delays)
            # So we can fetch all of them, just in batches
            print(f"  [State CA] Fetching descriptions for {len(state_ca_to_fetch)} jobs (this will take a while due to rate limiting)...")
            descriptions = await fetch_state_ca_descriptions_batch(state_ca_to_fetch, headless=False)
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            for job in state_ca_to_fetch:
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
    if filtered_jobs:
        filtered_links = {job['link'] for job in filtered_jobs}
        jobs_to_analyze = [j for j in jobs_to_analyze if j[2] in filtered_links]
    elif not reanalyze_only:
        # If not re-analyzing and no filtered jobs, nothing to do
        jobs_to_analyze = []

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
