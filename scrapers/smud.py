"""
SMUD (Sacramento Municipal Utility District) Job Scraper
Website: https://careers.smud.org

NOTE: SMUD's "View All Jobs" doesn't actually show ALL jobs.
Each category page can have different jobs, so we scrape ALL categories.
"""

import asyncio
from playwright.async_api import async_playwright
import re

SITE_NAME = "SMUD"
BASE_URL = "https://careers.smud.org"

# All SMUD category pages - "View All Jobs" doesn't actually show everything!
# These are direct URLs to each category (more reliable than clicking links)
CATEGORY_URLS = [
    ("View All Jobs", "/go/View-all-jobs/9107900/"),
    ("Accounting/Financial", "/go/AccountingFinancial/9107400/"),
    ("Administrative/Clerical", "/go/AdministrativeClerical/9107800/"),
    ("Communications/PR", "/go/CommunicationsPublic-Relations/9111100/"),
    ("Customer Service", "/go/Customer-Service/9111200/"),
    ("Engineering/Technical", "/go/EngineeringTechnical/9107500/"),
    ("Health and Safety", "/go/Health-and-Safety/9111400/"),
    ("Human Resources", "/go/Human-Resources/9111500/"),
    ("Information Technology", "/go/Information-TechnologyTelecommunications/9107600/"),
    ("Legal", "/go/Legal/9111300/"),
    ("Marketing/Sales", "/go/MarketingSales/9107700/"),
    ("Miscellaneous", "/go/Miscellaneous/9111700/"),
    ("Procurement/Supply Chain", "/go/ProcurementSupply-Chain/9111800/"),
    ("Skilled/Craft/Trades", "/go/SkilledCraftTrades/9111600/"),
    ("Student", "/go/Student/9108000/"),
    ("Utility System Mgmt", "/go/Utility-System-ManagementOperations/9108100/"),
]


async def _extract_jobs_from_page(page):
    """
    Extract job listings from the current page.
    Returns a list of job dicts.
    """
    jobs = []
    
    # Click "More Search Results" until all jobs are loaded
    while True:
        more_button = await page.query_selector("#tile-more-results")
        if more_button and await more_button.is_visible():
            await more_button.click()
            await asyncio.sleep(0.5)
        else:
            break
    
    job_tiles = await page.query_selector_all("li.job-tile")
    
    for tile in job_tiles:
        try:
            link_elem = await tile.query_selector("a.jobTitle-link")
            if not link_elem:
                continue
                
            title = await link_elem.inner_text()
            href = await link_elem.get_attribute("href")
            
            if not href:
                continue
                
            full_link = BASE_URL + href if href.startswith("/") else href
            
            # Default location for SMUD
            location = "Sacramento, CA"
            match = re.search(r'/job/([^/]+)-\d+/', href)
            if match:
                loc_part = match.group(1).replace("-", " ")
                if "Pollock Pines" in loc_part:
                    location = "Pollock Pines, CA"
            
            jobs.append({
                "title": title.strip(),
                "link": full_link,
                "location": location,
                "date_posted": "N/A",
                "source": SITE_NAME
            })
        except Exception as e:
            continue
    
    return jobs


async def scrape_smud_jobs(search_query="", headless=False):
    """
    Scrapes SMUD job listings.
    - First scrapes ALL category pages (since View All Jobs doesn't show everything)
    - Then searches by keyword if provided
    - Deduplicates by link
    """
    all_jobs = {}  # Use dict for deduplication by link
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, slow_mo=50)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0"
        )
        page = await context.new_page()
        
        # 1. Scrape ALL category pages first (only on first query to avoid repetition)
        if search_query == "" or search_query.lower() in ["security", "cyber"]:  # First query triggers full scrape
            print(f"[SMUD] Scraping all {len(CATEGORY_URLS)} category pages...")
            for cat_name, cat_path in CATEGORY_URLS:
                try:
                    url = BASE_URL + cat_path
                    await page.goto(url, timeout=30000)
                    await asyncio.sleep(0.5)
                    
                    # Wait for job list or "no results"
                    try:
                        await page.wait_for_selector(".job-tile", timeout=5000)
                    except:
                        # No jobs in this category
                        continue
                    
                    jobs = await _extract_jobs_from_page(page)
                    before_count = len(all_jobs)
                    for job in jobs:
                        all_jobs[job['link']] = job
                    new_count = len(all_jobs) - before_count
                    if new_count > 0:
                        print(f"  [SMUD] {cat_name}: +{new_count} new (total: {len(all_jobs)})")
                except Exception as e:
                    print(f"  [SMUD] Error scraping {cat_name}: {e}")
                    continue
        
        # 2. Also search by keyword if provided
        if search_query:
            search_url = f"{BASE_URL}/search/?q={search_query}"
            print(f"[SMUD] Searching for '{search_query}'...")
            
            try:
                await page.goto(search_url, timeout=60000)
                try:
                    await page.wait_for_selector(".job-tile", timeout=10000)
                except:
                    if await page.query_selector("#noresults"):
                        print(f"[SMUD] No results found for '{search_query}'")
                    # Continue anyway - we have category results
                
                jobs = await _extract_jobs_from_page(page)
                before_count = len(all_jobs)
                for job in jobs:
                    all_jobs[job['link']] = job
                new_count = len(all_jobs) - before_count
                print(f"[SMUD] Search '{search_query}': {len(jobs)} found, +{new_count} new (total: {len(all_jobs)})")
            except Exception as e:
                print(f"[SMUD] Error searching '{search_query}': {e}")
        
        await browser.close()
    
    result = list(all_jobs.values())
    print(f"[SMUD] Total unique jobs: {len(result)}")
    return result


async def scrape_all_smud_jobs(search_queries=None, headless=False):
    """
    Comprehensive SMUD scraper that:
    1. Scrapes ALL category pages
    2. Searches ALL keywords
    3. Returns deduplicated results
    
    Use this instead of calling scrape_smud_jobs() in a loop.
    """
    all_jobs = {}  # Dedupe by link
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, slow_mo=50)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0"
        )
        page = await context.new_page()
        
        # 1. Scrape ALL category pages
        print(f"[SMUD] Scraping {len(CATEGORY_URLS)} category pages...")
        for cat_name, cat_path in CATEGORY_URLS:
            try:
                url = BASE_URL + cat_path
                await page.goto(url, timeout=30000)
                await asyncio.sleep(0.3)
                
                try:
                    await page.wait_for_selector(".job-tile", timeout=5000)
                except:
                    continue
                
                jobs = await _extract_jobs_from_page(page)
                before_count = len(all_jobs)
                for job in jobs:
                    all_jobs[job['link']] = job
                new_count = len(all_jobs) - before_count
                if new_count > 0:
                    print(f"  [SMUD] {cat_name}: +{new_count} new (total: {len(all_jobs)})")
            except Exception as e:
                print(f"  [SMUD] Error scraping {cat_name}: {e}")
        
        # 2. Search each keyword (may find jobs not in categories)
        if search_queries:
            print(f"[SMUD] Searching {len(search_queries)} keywords...")
            for query in search_queries:
                try:
                    search_url = f"{BASE_URL}/search/?q={query}"
                    await page.goto(search_url, timeout=30000)
                    await asyncio.sleep(0.3)
                    
                    try:
                        await page.wait_for_selector(".job-tile", timeout=5000)
                    except:
                        continue
                    
                    jobs = await _extract_jobs_from_page(page)
                    before_count = len(all_jobs)
                    for job in jobs:
                        all_jobs[job['link']] = job
                    new_count = len(all_jobs) - before_count
                    if new_count > 0:
                        print(f"  [SMUD] Search '{query}': +{new_count} new")
                except Exception as e:
                    continue
        
        await browser.close()
    
    result = list(all_jobs.values())
    print(f"[SMUD] Total unique jobs scraped: {len(result)}")
    return result


async def fetch_smud_descriptions_batch(jobs, headless=False):
    """
    Fetch descriptions for multiple SMUD jobs using ONE browser instance.
    """
    if not jobs:
        return {}
    
    results = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0"
        )
        page = await context.new_page()
        
        total = len(jobs)
        for i, job in enumerate(jobs, 1):
            url = job['link']
            title = job['title']
            print(f"  [{i}/{total}] Fetching SMUD: {title[:50]}...")
            
            description = ""
            try:
                await page.goto(url, timeout=30000)
                selectors = [".jobdescription", "span[itemprop='description']", ".job", "#content"]
                for selector in selectors:
                    try:
                        desc_elem = await page.wait_for_selector(selector, timeout=5000)
                        if desc_elem:
                            description = await desc_elem.inner_text()
                            if description and len(description.strip()) > 100:
                                break
                    except:
                        continue
                
            except Exception as e:
                print(f"    Error fetching SMUD description: {e}")
            
            results[url] = description.strip()
            await asyncio.sleep(0.5)
        
        await browser.close()
    
    return results


if __name__ == "__main__":
    async def test():
        # Test comprehensive scrape
        from config import SEARCH_QUERIES
        jobs = await scrape_all_smud_jobs(SEARCH_QUERIES, headless=False)
        print(f"\nFound {len(jobs)} total unique jobs:")
        for j in jobs[:10]:
            print(f"- {j['title']}")
            
        if jobs:
            print("\nFetching description for first job...")
            desc = await fetch_smud_descriptions_batch(jobs[:1], headless=False)
            print(f"Description length: {len(list(desc.values())[0])}")
    
    asyncio.run(test())
