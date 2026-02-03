import asyncio
import os
import sqlite3
import sys
from web_setup_wizard import run_setup_wizard
from scrapers.pge import scrape_pge_jobs, fetch_pge_descriptions_batch
from scrapers.smud import scrape_smud_jobs, fetch_smud_descriptions_batch, scrape_all_smud_jobs
from scrapers.kaiser import scrape_kaiser_jobs, fetch_kaiser_descriptions_batch, scrape_all_kaiser_jobs
from scrapers.state_ca import scrape_state_ca_jobs, fetch_state_ca_descriptions_batch, scrape_all_state_ca_jobs
from scrapers.ucdavis import scrape_ucdavis_jobs, fetch_ucdavis_descriptions_batch
from scrapers.sutter import scrape_sutter_jobs, fetch_sutter_descriptions_batch
from scrapers.commonspirit import scrape_commonspirit_jobs, fetch_commonspirit_descriptions_batch
from database import init_db, save_job, get_new_jobs, get_new_jobs_as_dicts, update_job_analysis, update_job_failed_analysis, update_job_skip_reason, update_job_title, DB_NAME, reset_failed_analyses, get_jobs_needing_analysis, get_jobs_to_refilter, export_to_excel, generate_job_id
from ai_analyzer import JobAnalyzer
from dotenv import load_dotenv

# Try to import config, but handle missing config.py gracefully
try:
    from config import SEARCH_QUERIES, NOISE_KEYWORDS, ENTRY_LEVEL_INDICATORS, ENABLED_SITES, IGNORE_FIELDS, INTEREST_KEYWORDS
    from config import TITLE_MUST_CONTAIN, BOGUS_TITLES
    from config import STATE_CA_LOCATION, STATE_CA_KEYWORDS
    from config import UCDAVIS_KEYWORDS
    from config import SUTTER_KEYWORDS
    from config import COMMONSPIRIT_MAX_PAGES, COMMONSPIRIT_ZIP
except ImportError as e:
    # config.py doesn't exist - will prompt user in main()
    SEARCH_QUERIES = []
    NOISE_KEYWORDS = []
    ENTRY_LEVEL_INDICATORS = []
    ENABLED_SITES = {}
    IGNORE_FIELDS = []
    INTEREST_KEYWORDS = []
    TITLE_MUST_CONTAIN = ["IT", "Tech", "Security", "Cyber", "Analyst", "Engineer", "Developer", "Systems", "Network", "Data", "Software", "Support", "Customer Service", "Help Desk"]
    BOGUS_TITLES = ["train", "trained", "trainers", "trains", "rotation", "rotational"]
    STATE_CA_LOCATION = "Sacramento County"
    STATE_CA_KEYWORDS = ["Information", "IT", "Security", "Analyst"]
    UCDAVIS_KEYWORDS = ["IT", "Security", "Analyst", "Associate"]
    SUTTER_KEYWORDS = ["IT", "Security", "Analyst", "Help Desk", "Systems", "Network", "Cyber", "Infrastructure", "Support", "Technician"]
    COMMONSPIRIT_MAX_PAGES = 20
    COMMONSPIRIT_ZIP = None


# Map site keys to their display source names (must match scraper SITE_NAME values)
SITE_SOURCE_MAP = {
    "pge": "PG&E",
    "smud": "SMUD",
    "kaiser": "Kaiser Permanente",
    "state_ca": "State of California",
    "ucdavis": "UC Davis",
    "sutter": "Sutter Health",
    "commonspirit": "CommonSpirit",
}

import re

def word_match(keyword, text):
    """
    Check if keyword exists as a whole word in text (not as substring).
    E.g., "IT" should NOT match "conditions" but SHOULD match "IT Analyst"
    """
    # Escape special regex chars and use word boundaries
    pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
    return bool(re.search(pattern, text.lower()))

def filter_jobs(jobs, save_filtered_log=True):
    """
    Filters jobs based on keywords defined in config.py.
    Saves filtered-out jobs to a log file for review.

    Returns:
        tuple: (filtered_jobs, filtered_out) where filtered_out contains job dicts with 'reason' field
    """
    filtered_jobs = []
    filtered_out = []  # Track what we're filtering out and why

    for job in jobs:
        title = job["title"]
        title_lower = title.lower()
        source = job.get("source", "Unknown")

        # 1. Immediate discard: keywords in IGNORE_FIELDS (Medical/Nursing/etc.)
        matched_ignore = None
        for field in IGNORE_FIELDS:
            if field.lower() in title_lower:
                matched_ignore = field
                break

        if matched_ignore:
            filtered_out.append({
                **job,  # Include full job dict for DB update
                "reason": f"Filtered: '{matched_ignore}' matched IGNORE_FIELDS"
            })
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
        else:
            # Filtered out due to noise keywords (Senior/Manager/etc.)
            matched_noise = [kw for kw in NOISE_KEYWORDS if word_match(kw, title)]
            filtered_out.append({
                **job,  # Include full job dict for DB update
                "reason": f"Filtered: {matched_noise} matched NOISE_KEYWORDS (not in INTEREST_KEYWORDS)"
            })

    # Save filtered-out jobs to log file for review
    if save_filtered_log and filtered_out:
        log_path = "filtered_jobs.log"
        with open(log_path, "w") as f:
            f.write(f"FILTERED OUT JOBS - {len(filtered_out)} jobs removed\n")
            f.write("=" * 80 + "\n")
            f.write("Review this file to check if any jobs were incorrectly filtered.\n")
            f.write("If you see jobs you want, adjust IGNORE_FIELDS or NOISE_KEYWORDS in config.py\n")
            f.write("=" * 80 + "\n\n")

            # Group by reason
            by_reason = {}
            for item in filtered_out:
                reason = item["reason"].split(":")[0]  # Get reason category
                if reason not in by_reason:
                    by_reason[reason] = []
                by_reason[reason].append(item)

            for reason_cat, items in sorted(by_reason.items()):
                f.write(f"\n{'='*60}\n")
                f.write(f"{reason_cat} ({len(items)} jobs)\n")
                f.write(f"{'='*60}\n")
                for item in sorted(items, key=lambda x: x["title"]):
                    f.write(f"  [{item['source']}] {item['title']}\n")
                    f.write(f"    -> {item['reason']}\n")

        print(f"📋 Filtered jobs saved to: {log_path} (review to check for false positives)")

    return filtered_jobs, filtered_out


def refilter_existing_jobs():
    """
    Re-apply filters to all 'new' status jobs in the database.
    Useful after updating IGNORE_FIELDS or NOISE_KEYWORDS in config.py.
    """
    print("\n🔄 Re-filtering existing 'new' jobs in database...")
    new_jobs = get_new_jobs_as_dicts()

    if not new_jobs:
        print("No 'new' status jobs found in database.")
        return 0

    print(f"Found {len(new_jobs)} jobs with 'new' status")

    # Run through filter (don't save log - we'll report directly)
    _, filtered_out = filter_jobs(new_jobs, save_filtered_log=True)

    # Update database for filtered-out jobs
    if filtered_out:
        print(f"Marking {len(filtered_out)} jobs as filtered...")
        for job in filtered_out:
            job_id = job.get("id") or generate_job_id(job["link"])
            update_job_skip_reason(job_id, job["reason"])

    remaining = len(new_jobs) - len(filtered_out)
    print(f"✅ Done! {len(filtered_out)} jobs marked as filtered, {remaining} jobs remain as 'new'")
    return len(filtered_out)


def select_sites():
    """
    Interactive menu to select which sites to scrape.
    Returns: (selected_sites_dict, mode)
    mode: "scrape" | "reanalyze" | "unanalyzed"
    """
    print("\n" + "="*60)
    print("        🎯 AI JOB HUNTER - Multi-Site Job Search")
    print("="*60)
    print("\nSelect options:")
    print("  0) 🆕 SETUP WIZARD (Configure your profile)")
    print("  1) PG&E only")
    print("  2) SMUD only")
    print("  3) Kaiser Permanente only")
    print("  4) State of California only")
    print("  5) UC Davis only")
    print("  6) Sutter Health only")
    print("  7) CommonSpirit Health only")
    print("  8) All sites (PG&E + SMUD + Kaiser + State CA + UC Davis + Sutter + CommonSpirit)")
    print("  9) Use config.py settings")
    print(" 10) RE-ANALYZE DATABASE (Skip scraping, run AI on existing jobs)")
    print(" 11) REFILTER EXISTING JOBS (Apply new filters to all DB jobs)")
    print(" 12) ANALYZE UNANALYZED (Fetch missing descriptions + analyze all DB jobs)")

    all_false = {"pge": False, "smud": False, "kaiser": False, "state_ca": False, "ucdavis": False, "sutter": False, "commonspirit": False}

    while True:
        choice = input("\nEnter choice (0-12): ").strip()
        if choice == "0":
            # Run setup wizard and return to menu
            run_setup_wizard()
            return select_sites()  # Restart menu
        elif choice == "1":
            return {**all_false, "pge": True}, "scrape"
        elif choice == "2":
            return {**all_false, "smud": True}, "scrape"
        elif choice == "3":
            return {**all_false, "kaiser": True}, "scrape"
        elif choice == "4":
            return {**all_false, "state_ca": True}, "scrape"
        elif choice == "5":
            return {**all_false, "ucdavis": True}, "scrape"
        elif choice == "6":
            return {**all_false, "sutter": True}, "scrape"
        elif choice == "7":
            return {**all_false, "commonspirit": True}, "scrape"
        elif choice == "8":
            return {k: True for k in all_false}, "scrape"
        elif choice == "9":
            return ENABLED_SITES.copy(), "scrape"
        elif choice == "10":
            return {}, "reanalyze"
        elif choice == "11":
            return {}, "refilter"
        elif choice == "12":
            return {}, "unanalyzed"
        else:
            print("Invalid choice. Please enter 0-12.")


async def main():
    # 0. Check if config.py exists - if not, run setup wizard
    if not os.path.exists("config.py"):
        print("\n" + "="*70)
        print("⚠️  config.py not found!")
        print("="*70)
        print("\nWelcome to AI Job Hunter! Let's set up your profile.\n")

        run_setup = input("Run the setup wizard now? (y/n): ").strip().lower()
        if run_setup in ['y', 'yes']:
            run_setup_wizard()
            print("\n✅ Setup complete! Now restart the app: python main.py\n")
            sys.exit(0)
        else:
            print("\nYou can manually set up by copying the template:")
            print("  cp config_template.py config.py")
            print("  # Then edit config.py with your preferences\n")
            sys.exit(1)

    # 1. Initialize
    load_dotenv()
    init_db()
    analyzer = JobAnalyzer()

    # 2. Site Selection Menu
    selected_sites, mode = select_sites()

    # Track which sources are active for this run (for filtering top matches later)
    active_sources = [SITE_SOURCE_MAP[k] for k, v in selected_sites.items() if v] if selected_sites else []

    if mode == "scrape":
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
        
        # UC Davis - scrape multiple keywords
        if selected_sites.get("ucdavis", False):
            print(f"\n📍 Scraping UC Davis Jobs...")
            raw_jobs = await scrape_ucdavis_jobs(
                search_queries=UCDAVIS_KEYWORDS,
                headless=False
            )
            all_raw_jobs.extend(raw_jobs)

        # Sutter Health - scrape multiple keywords (pure HTTP, no browser)
        if selected_sites.get("sutter", False):
            print(f"\n📍 Scraping Sutter Health Jobs...")
            raw_jobs = await scrape_sutter_jobs(
                search_queries=SUTTER_KEYWORDS,
                headless=False
            )
            all_raw_jobs.extend(raw_jobs)

        # CommonSpirit Health - scrape all Sacramento area jobs (pure HTTP, no browser)
        if selected_sites.get("commonspirit", False):
            print(f"\n📍 Scraping CommonSpirit Health Jobs (Dignity Health, CHI)...")
            # Use zip code from config if provided, otherwise use default
            commonspirit_location = None
            if COMMONSPIRIT_ZIP:
                commonspirit_location = f"{COMMONSPIRIT_ZIP}, Sacramento, CA"
            raw_jobs = await scrape_commonspirit_jobs(
                max_pages=COMMONSPIRIT_MAX_PAGES,
                location=commonspirit_location,
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
        filtered_jobs, filtered_out_jobs = filter_jobs(unique_jobs)
        print(f"Jobs remaining after noise filter: {len(filtered_jobs)}")

        # Update database status for filtered-out jobs so Excel shows WHY they were filtered
        if filtered_out_jobs:
            print(f"Updating {len(filtered_out_jobs)} filtered jobs in database...")
            for job in filtered_out_jobs:
                job_id = generate_job_id(job["link"])
                update_job_skip_reason(job_id, job["reason"])
        
        # 5. AI Title Pre-Filtering (optional - user chooses)
        if len(filtered_jobs) > 10:
            run_prefilter = input(f"\n{len(filtered_jobs)} jobs passed noise filter. Run AI title pre-filter to narrow down? (y/N): ").strip().lower()
            if run_prefilter == 'y':
                print(f"🤖 AI is pre-filtering {len(filtered_jobs)} titles...")
                all_ai_filtered = []
                skipped_jobs = []

                for i in range(0, len(filtered_jobs), 100):
                    chunk = filtered_jobs[i:i+100]
                    ai_filtered_chunk = analyzer.filter_titles_with_ai(chunk)
                    all_ai_filtered.extend(ai_filtered_chunk)

                    kept_links = {j['link'] for j in ai_filtered_chunk}
                    for j in chunk:
                        if j['link'] not in kept_links:
                            skipped_jobs.append(j)

                if skipped_jobs:
                    print(f"AI skipped {len(skipped_jobs)} titles it thought were irrelevant.")
                    print(f"Example skipped: {', '.join([j['title'] for j in skipped_jobs[:3]])}...")

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
                print(f"Skipping AI pre-filter. All {len(filtered_jobs)} jobs will be analyzed.")
    elif mode == "reanalyze":
        print("\n📍 RE-ANALYZE MODE: Skipping scraping, pulling jobs from database...")

        # Show stats first so user knows what's available
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("""
            SELECT source, COUNT(*) FROM jobs
            WHERE match_score IS NULL OR match_score = 0 OR status = 'skipped_ai_title'
            GROUP BY source ORDER BY COUNT(*) DESC
        """)
        stats = c.fetchall()
        conn.close()
        if stats:
            print("\nUnanalyzed/failed jobs in database:")
            for source, count in stats:
                print(f"  {source or 'Unknown'}: {count}")

        print("\nWhich source would you like to re-analyze?")
        print("  1) State of California")
        print("  2) PG&E")
        print("  3) SMUD")
        print("  4) Kaiser Permanente")
        print("  5) UC Davis")
        print("  6) Sutter Health")
        print("  7) CommonSpirit Health")
        print("  8) ALL")

        source_choice = input("\nEnter choice (1-8): ").strip()
        source_map = {"1": "State of California", "2": "PG&E", "3": "SMUD", "4": "Kaiser Permanente", "5": "UC Davis", "6": "Sutter Health", "7": "CommonSpirit"}
        target_source = source_map.get(source_choice)
        if target_source:
            active_sources = [target_source]

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        if target_source:
            print(f"Filtering for source: {target_source}")
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

    elif mode == "refilter":
        refilter_existing_jobs()
        return # Exit after refilter, user can then run ANALYZE UNANALYZED

    elif mode == "unanalyzed":
        print("\n📍 ANALYZE UNANALYZED: Finding ALL DB jobs not yet successfully analyzed...")

        # Show stats by source - include jobs WITH and WITHOUT descriptions
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("""
            SELECT source,
                SUM(CASE WHEN description IS NOT NULL AND description != '' THEN 1 ELSE 0 END) as has_desc,
                SUM(CASE WHEN description IS NULL OR description = '' THEN 1 ELSE 0 END) as no_desc,
                COUNT(*) as total
            FROM jobs
            WHERE (status NOT IN ('analyzed', 'no_description', 'skipped_filter') OR match_score IS NULL OR match_score = 0)
            GROUP BY source ORDER BY COUNT(*) DESC
        """)
        stats = c.fetchall()
        total_unanalyzed = sum(total for _, _, _, total in stats) if stats else 0
        total_has_desc = sum(hd for _, hd, _, _ in stats) if stats else 0
        total_no_desc = sum(nd for _, _, nd, _ in stats) if stats else 0

        if not stats or total_unanalyzed == 0:
            c.execute("SELECT COUNT(*) FROM jobs")
            total_jobs = c.fetchone()[0]
            if total_jobs == 0:
                print("No jobs in database. Run a scrape first (options 1-9).")
            else:
                print("All jobs have been analyzed!")
            filtered_jobs = []
        else:
            print(f"\nUnanalyzed jobs ({total_unanalyzed} total):")
            print(f"  {total_has_desc} have descriptions (ready to analyze)")
            print(f"  {total_no_desc} missing descriptions (will attempt to fetch)")
            print()
            for source, has_desc, no_desc, total in stats:
                desc_note = f" ({no_desc} need desc fetch)" if no_desc > 0 else ""
                print(f"  {source or 'Unknown'}: {total}{desc_note}")

            print("\nWhich source to analyze?")
            for idx, (source, has_desc, no_desc, total) in enumerate(stats, 1):
                print(f"  {idx}) {source or 'Unknown'} ({total})")
            print(f"  {len(stats) + 1}) ALL ({total_unanalyzed})")

            source_choice = input(f"\nEnter choice (1-{len(stats) + 1}): ").strip()
            try:
                choice_idx = int(source_choice) - 1
                if 0 <= choice_idx < len(stats):
                    target_source = stats[choice_idx][0]
                    active_sources = [target_source]
                else:
                    target_source = None  # ALL
            except ValueError:
                target_source = None  # ALL

            c2 = conn.cursor()
            if target_source:
                print(f"Pulling unanalyzed jobs for: {target_source}")
                c2.execute("""
                    SELECT title, link, location, source FROM jobs
                    WHERE source = ? AND (status NOT IN ('analyzed', 'no_description', 'skipped_filter') OR match_score IS NULL OR match_score = 0)
                """, (target_source,))
            else:
                print("Pulling all unanalyzed jobs...")
                c2.execute("""
                    SELECT title, link, location, source FROM jobs
                    WHERE (status NOT IN ('analyzed', 'no_description', 'skipped_filter') OR match_score IS NULL OR match_score = 0)
                """)

            rows = c2.fetchall()
            all_unanalyzed = []
            for row in rows:
                all_unanalyzed.append({
                    'title': row[0],
                    'link': row[1],
                    'location': row[2],
                    'source': row[3]
                })

            # Apply IGNORE_FIELDS filter to skip obvious non-tech roles (medical, facility, etc.)
            # Write skip reasons to DB so Excel shows why each job was skipped
            filtered_jobs = []
            skipped_ignore = 0
            skipped_bogus = 0
            skipped_title = 0
            for job in all_unanalyzed:
                title = job.get("title") or ""
                title_lower = title.lower().strip()
                job_id = generate_job_id(job['link'])
                if any(field.lower() in title_lower for field in IGNORE_FIELDS):
                    skipped_ignore += 1
                    update_job_skip_reason(job_id, "Skipped: medical/non-tech (noise filter)")
                    continue
                if any(title_lower == b.lower() for b in BOGUS_TITLES) or len(title_lower) < 4:
                    skipped_bogus += 1
                    update_job_skip_reason(job_id, "Skipped: bogus/short title (e.g. train, trained)")
                    continue
                # Only keep if title suggests tech / support (don't fetch "Food Service Worker")
                if not any(word_match(kw, title) for kw in TITLE_MUST_CONTAIN):
                    skipped_title += 1
                    update_job_skip_reason(job_id, "Skipped: title does not look tech/support")
                    continue
                filtered_jobs.append(job)

            if skipped_ignore:
                print(f"Noise filter removed {skipped_ignore} obvious non-tech titles (medical, facility, etc.)")
            if skipped_bogus:
                print(f"Filtered out {skipped_bogus} bogus/short titles (e.g. train, trained).")
            if skipped_title:
                print(f"Skipped {skipped_title} titles that don't look tech/support (no fetch).")
            print(f"Found {len(filtered_jobs)} jobs to process.")
        conn.close()
    
    # 7. Identify jobs MISSING descriptions (ONLY from our filtered list)
    # Skip bogus titles and titles that don't look tech/support (no point fetching "Food Service Worker")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    jobs_needing_desc = []
    for job in filtered_jobs:
        title = (job.get("title") or "").strip()
        title_lower = title.lower()
        if any(title_lower == b.lower() for b in BOGUS_TITLES) or len(title_lower) < 4:
            continue
        if not any(word_match(kw, title) for kw in TITLE_MUST_CONTAIN):
            continue
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
        ucdavis_to_fetch = [j for j in jobs_needing_desc if j.get('source') == 'UC Davis']
        
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
            descriptions, titles = await fetch_state_ca_descriptions_batch(state_ca_to_fetch, headless=False)
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            for job in state_ca_to_fetch:
                job_id = generate_job_id(job['link'])
                desc = descriptions.get(job['link'], '')
                if desc:
                    c.execute("UPDATE jobs SET description = ? WHERE id = ?", (desc, job_id))
                # Fix "Job Posting" placeholder: use title parsed from the job page
                if (job.get('title') or '').strip() == 'Job Posting' and titles.get(job['link']):
                    c.execute("UPDATE jobs SET title = ? WHERE id = ?", (titles[job['link']], job_id))
            conn.commit()
            conn.close()
        
        # Fetch UC Davis descriptions
        if ucdavis_to_fetch:
            # UC Davis has rate limiting built into the scraper (10s delays)
            print(f"  [UC Davis] Fetching descriptions for {len(ucdavis_to_fetch)} jobs (this will take a while due to rate limiting)...")
            descriptions = await fetch_ucdavis_descriptions_batch(ucdavis_to_fetch, headless=False)
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            for job in ucdavis_to_fetch:
                job_id = generate_job_id(job['link'])
                desc = descriptions.get(job['link'], '')
                if desc:
                    c.execute("UPDATE jobs SET description = ? WHERE id = ?", (desc, job_id))
            conn.commit()
            conn.close()

        # Fetch Sutter Health descriptions
        sutter_to_fetch = [j for j in jobs_needing_desc if j.get('source') == 'Sutter Health']
        if sutter_to_fetch:
            print(f"  [Sutter] Fetching descriptions for {len(sutter_to_fetch)} jobs (pure HTTP, 3s delays)...")
            descriptions = await fetch_sutter_descriptions_batch(sutter_to_fetch, headless=False)
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            for job in sutter_to_fetch:
                job_id = generate_job_id(job['link'])
                desc = descriptions.get(job['link'], '')
                if desc:
                    c.execute("UPDATE jobs SET description = ? WHERE id = ?", (desc, job_id))
            conn.commit()
            conn.close()

        # Fetch CommonSpirit Health descriptions
        commonspirit_to_fetch = [j for j in jobs_needing_desc if j.get('source') == 'CommonSpirit']
        if commonspirit_to_fetch:
            print(f"  [CommonSpirit] Fetching descriptions for {len(commonspirit_to_fetch)} jobs (pure HTTP, 1s delays)...")
            descriptions = await fetch_commonspirit_descriptions_batch(commonspirit_to_fetch, headless=False)
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            for job in commonspirit_to_fetch:
                job_id = generate_job_id(job['link'])
                desc = descriptions.get(job['link'], '')
                if desc:
                    c.execute("UPDATE jobs SET description = ? WHERE id = ?", (desc, job_id))
            conn.commit()
            conn.close()

        print(f"Descriptions fetched and saved.")

        # Mark jobs that STILL have no description after fetch attempt
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        still_no_desc = 0
        for job in jobs_needing_desc:
            job_id = generate_job_id(job['link'])
            c.execute("SELECT description FROM jobs WHERE id = ?", (job_id,))
            row = c.fetchone()
            if row and (not row[0] or row[0].strip() == ""):
                c.execute("""
                    UPDATE jobs SET status = 'no_description',
                    analysis = 'Description could not be fetched from source website'
                    WHERE id = ?
                """, (job_id,))
                still_no_desc += 1
        conn.commit()
        conn.close()
        if still_no_desc:
            print(f"  {still_no_desc} jobs still have no description after fetch attempt (marked in Excel).")

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
    elif mode == "scrape":
        # If scraping mode and no filtered jobs, nothing to do
        jobs_to_analyze = []

    if not jobs_to_analyze:
        print("No NEW relevant jobs requiring AI analysis.")
    else:
        print(f"\n🤖 Analyzing {len(jobs_to_analyze)} jobs with Groq AI (2 sec delay)...")
        for i, job_row in enumerate(jobs_to_analyze, 1):
            job_id, title, link, location, date, desc, score, missing, analysis, status, last_seen, source = job_row

            if not desc:
                print(f"  [{i}/{len(jobs_to_analyze)}] Skipping {title} (no description)")
                # Mark in DB so Excel shows why
                conn_skip = sqlite3.connect(DB_NAME)
                c_skip = conn_skip.cursor()
                c_skip.execute("""
                    UPDATE jobs SET status = 'no_description',
                    analysis = 'Description could not be fetched from source website'
                    WHERE id = ?
                """, (job_id,))
                conn_skip.commit()
                conn_skip.close()
                continue

            print(f"  [{i}/{len(jobs_to_analyze)}] {title}...", end=" ", flush=True)
            try:
                score, missing_skills, brief_analysis = analyzer.analyze_job(title, desc)
                update_job_analysis(job_id, score, missing_skills, brief_analysis)
                print(f"Score: {score}/10")
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "rate limit" in err_msg.lower():
                    update_job_failed_analysis(job_id, err_msg, status="rate_limited")
                    print(f"Rate limited (will retry on ANALYZE UNANALYZED)")
                else:
                    update_job_failed_analysis(job_id, err_msg, status="failed")
                    print(f"Error: {err_msg[:60]}...")

    # 8. Final Output - Top Recommended Matches (filtered by current run sources)
    print("\n" + "="*60)
    print("        📊 TOP RECOMMENDED MATCHES")
    print("="*60)
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    if active_sources:
        placeholders = ",".join(["?" for _ in active_sources])
        source_label = ", ".join(active_sources)
        print(f"(Showing results for: {source_label})")
        c.execute(f"""
            SELECT title, location, match_score, missing_skills, link, source
            FROM jobs
            WHERE match_score >= 1 AND source IN ({placeholders})
            ORDER BY match_score DESC
            LIMIT 10
        """, active_sources)
    else:
        c.execute("""
            SELECT title, location, match_score, missing_skills, link, source
            FROM jobs
            WHERE match_score >= 1
            ORDER BY match_score DESC
            LIMIT 10
        """)

    top_matches = c.fetchall()
    c.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = c.fetchone()[0]
    conn.close()

    if not top_matches:
        if total_jobs == 0:
            print("No jobs in database. Run a scrape first (options 1-9).")
        else:
            print("No jobs with match score ≥ 1. Run a scrape and analyze, or set GROQ_API_KEY in .env.")
    else:
        for title, loc, score, missing, link, source in top_matches:
            indicator = "⭐" if score >= 8 else "✅" if score >= 5 else "📋"
            print(f"\n{indicator} [{score}/10] {title}")
            print(f"   Source: {source} | Location: {loc}")
            print(f"   Missing: {missing if missing else 'None'}")
            print(f"   Link: {link}")
    
    # 9. Export to Excel
    print("\n" + "="*60)
    print("        📁 EXPORTING TO EXCEL")
    print("="*60)
    export_to_excel()

if __name__ == "__main__":
    asyncio.run(main())
