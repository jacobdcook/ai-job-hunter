"""
Kaiser Permanente Job Scraper
Website: https://www.kaiserpermanentejobs.org

Scrapes California jobs from Kaiser Permanente careers site.
Uses JavaScript pagination (clicking "Next" button) rather than URL-based pagination.
"""

import asyncio
import re
from playwright.async_api import async_playwright
try:
    from config import KAISER_LOCATION_URL, KAISER_KEYWORD_URL_TEMPLATE
except ImportError:
    # Fallback for standalone testing or if not configured
    KAISER_LOCATION_URL = "/search-jobs/California%2C%20US/641/3/6252001-5332921/37x25022/-119x75126/25/2"
    KAISER_KEYWORD_URL_TEMPLATE = "/search-jobs/{keyword}/California%2C%20US/641/1/3/6252001-5332921/37x25022/-119x75126/25/2"

SITE_NAME = "Kaiser Permanente"
BASE_URL = "https://www.kaiserpermanentejobs.org"

# California search URL - pagination is done via JavaScript, not URL
CALIFORNIA_SEARCH_URL = KAISER_LOCATION_URL
# Keyword search URL template for California
KEYWORD_SEARCH_URL = KAISER_KEYWORD_URL_TEMPLATE
JOBS_PER_PAGE = 15  # Kaiser shows 15 jobs per page


async def _dismiss_cookie_banner(page):
    """
    Dismiss the cookie consent banner if present.
    """
    try:
        # Try to click 'Accept' or the close button
        selectors = [
            '#ot-sdk-btn-accept',       # OneTrust Accept
            '#cookie-accept',           # Generic Accept
            '.accept-cookies',          # Generic class
            'button:has-text("Accept")', # Text-based search
            '.system-ialert-close-button', 
            '#system-ialert-close', 
            '[class*="close"]'
        ]
        
        for selector in selectors:
            try:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(0.5)
                    return
            except:
                continue
        
        # Fallback: remove the element via JavaScript if it's still there
        await page.evaluate('() => { const el = document.getElementById("system-ialert") || document.querySelector(".optanon-alert-box-wrapper") || document.querySelector("#onetrust-banner-sdk"); if(el) el.remove(); }')
    except:
        pass


async def _get_total_job_count(page):
    """
    Extract total job count from the search results page.
    Returns the total number of jobs found.
    """
    try:
        # Look for the job count header like "1887 Job Results"
        # The h2 inside #search-results-list has format "N Job Results in ..."
        headers = await page.query_selector_all("h2")
        for header in headers:
            text = await header.inner_text()
            match = re.search(r'(\d[\d,]*)\s*Job\s*Results?', text, re.IGNORECASE)
            if match:
                return int(match.group(1).replace(',', ''))
    except Exception as e:
        print(f"[Kaiser] Error getting job count: {e}")
    return 0


async def _extract_jobs_from_page(page):
    """
    Extract job listings from the current search results page.
    Returns a list of job dicts with title, link, location.
    """
    jobs = []
    
    # Get all job listing links
    job_links = await page.query_selector_all("#search-results-list li > a")
    
    for link in job_links:
        try:
            href = await link.get_attribute("href")
            if not href or "/job/" not in href:
                continue
            
            # Extract title from the h2 inside the link
            title_elem = await link.query_selector("h2")
            if title_elem:
                title = await title_elem.inner_text()
                title = title.strip().replace("##", "").strip()
            else:
                # Fallback: extract from URL
                parts = href.split("/job/")
                if len(parts) > 1:
                    title = parts[1].split("/")[1].replace("-", " ").title()
                else:
                    continue
            
            # Extract location/details from the link text
            full_text = await link.inner_text()
            # Format is typically: "Title\nCity, State, Work Mode, Schedule, Shift"
            lines = [l.strip() for l in full_text.split("\n") if l.strip()]
            
            # Second line usually has location info
            location = "California"  # Default
            if len(lines) > 1:
                loc_parts = lines[1].split(",")
                if len(loc_parts) >= 2:
                    city = loc_parts[0].strip()
                    state = loc_parts[1].strip()
                    location = f"{city}, {state}"
                else:
                    location = lines[1].strip()
            
            # Build full URL
            full_link = BASE_URL + href if href.startswith("/") else href
            
            jobs.append({
                "title": title,
                "link": full_link,
                "location": location,
                "date_posted": "N/A",
                "source": SITE_NAME
            })
        except Exception as e:
            continue
    
    return jobs


async def scrape_kaiser_jobs(search_query="", headless=False, max_pages=None):
    """
    Scrapes Kaiser Permanente California job listings.
    
    Uses JavaScript pagination by clicking the "Next" button since
    the site doesn't support URL-based pagination for job listings.
    
    Args:
        search_query: Optional keyword to filter results (not fully implemented yet)
        headless: Run browser in headless mode
        max_pages: Maximum number of pages to scrape (None = all pages)
    
    Returns:
        List of job dictionaries
    """
    all_jobs = {}  # Use dict for deduplication by link
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, slow_mo=50)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0"
        )
        page = await context.new_page()
        
        start_url = BASE_URL + CALIFORNIA_SEARCH_URL
        print(f"[Kaiser] Loading California jobs...")
        
        try:
            await page.goto(start_url, timeout=60000)
            await asyncio.sleep(2)  # Let page fully load
            
            # Dismiss cookie banner
            await _dismiss_cookie_banner(page)
            
            # Get total job count
            total_jobs = await _get_total_job_count(page)
            if total_jobs == 0:
                print("[Kaiser] Could not determine job count, will scrape until no more pages")
                total_jobs = 2000  # Fallback estimate
            
            estimated_pages = (total_jobs + JOBS_PER_PAGE - 1) // JOBS_PER_PAGE
            if max_pages:
                estimated_pages = min(estimated_pages, max_pages)
            
            print(f"[Kaiser] Found approximately {total_jobs} jobs (~{estimated_pages} pages)")
            
            current_page = 0
            consecutive_empty = 0
            
            while True:
                current_page += 1
                
                # Check if we've hit max pages
                if max_pages and current_page > max_pages:
                    print(f"[Kaiser] Reached max pages limit ({max_pages})")
                    break
                
                # Wait for job listings
                try:
                    await page.wait_for_selector("#search-results-list li a", timeout=10000)
                except:
                    print(f"[Kaiser] No job listings found on page {current_page}")
                    break
                
                # Extract jobs from current page
                jobs = await _extract_jobs_from_page(page)
                before_count = len(all_jobs)
                for job in jobs:
                    all_jobs[job['link']] = job
                new_count = len(all_jobs) - before_count
                
                # Progress logging
                if current_page % 10 == 0 or current_page <= 3:
                    print(f"[Kaiser] Page {current_page}: +{new_count} new jobs (total: {len(all_jobs)})")
                
                # Check for no new jobs (might be at end or stuck)
                if new_count == 0:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        print(f"[Kaiser] No new jobs for {consecutive_empty} pages, stopping")
                        break
                else:
                    consecutive_empty = 0
                
                # Try to click next page
                next_btn = await page.query_selector('a.next:not(.disabled)')
                if not next_btn:
                    print(f"[Kaiser] No more pages (next button disabled/missing)")
                    break
                
                # Use JavaScript click to avoid overlay issues
                try:
                    await next_btn.evaluate('el => el.click()')
                    await asyncio.sleep(1.5)  # Wait for AJAX to complete
                except Exception as e:
                    print(f"[Kaiser] Error clicking next: {e}")
                    break
            
        except Exception as e:
            print(f"[Kaiser] Error during scraping: {e}")
        
        await browser.close()
    
    result = list(all_jobs.values())
    print(f"[Kaiser] Total unique jobs scraped: {len(result)}")
    return result


async def fetch_kaiser_descriptions_batch(jobs, headless=False):
    """
    Fetch descriptions for multiple Kaiser jobs using ONE browser instance.
    
    Args:
        jobs: List of job dictionaries with 'link' key
        headless: Run browser in headless mode
    
    Returns:
        Dictionary mapping job URLs to descriptions
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
            print(f"  [{i}/{total}] Fetching Kaiser: {title[:50]}...")
            
            description = ""
            try:
                # Use a slightly longer timeout and wait for network idle
                await page.goto(url, timeout=45000, wait_until="domcontentloaded")
                
                # Check for "Access Denied" or other block pages
                if "Access Denied" in await page.title() or "Access Denied" in await page.content():
                    print(f"    !!! BLOCKED by Kaiser (IP block). Stopping further fetches.")
                    break
                
                # 10 second delay as requested by user + small jitter
                import random
                sleep_time = 10.0 + random.uniform(0, 2)
                await asyncio.sleep(sleep_time) 
                
                # Dismiss cookie banner if present
                await _dismiss_cookie_banner(page)
                
                # Try multiple selectors for job description
                selectors = [
                    ".job-description",
                    "[class*='job-description']",
                    ".ats-description",
                    "#job-description",
                    ".job-details",
                    "article",
                    "main"
                ]
                
                for selector in selectors:
                    try:
                        desc_elem = await page.wait_for_selector(selector, timeout=3000)
                        if desc_elem:
                            description = await desc_elem.inner_text()
                            if description and len(description.strip()) > 100:
                                break
                    except:
                        continue
                
            except Exception as e:
                print(f"    Error fetching Kaiser description: {e}")
            
            results[url] = description.strip()
            await asyncio.sleep(0.3)
        
        await browser.close()
    
    return results


async def scrape_all_kaiser_jobs(search_queries=None, headless=False, max_pages=None):
    """
    Comprehensive Kaiser scraper.
    - If search_queries are provided, searches for each keyword.
    - If no queries, scrapes all California jobs (most thorough).
    
    Args:
        search_queries: List of keywords to search
        headless: Run browser in headless mode
        max_pages: Maximum pages to scrape per search (None = all)
    
    Returns:
        List of unique job dictionaries
    """
    all_jobs_dict = {}
    
    if not search_queries:
        # Most thorough: scrape every single job in California
        print(f"[Kaiser] No keywords provided, starting full California scrape...")
        jobs = await scrape_kaiser_jobs(headless=headless, max_pages=max_pages)
        return jobs
    
    # Otherwise, loop through keywords like PG&E/SMUD
    print(f"[Kaiser] Searching for {len(search_queries)} keywords...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, slow_mo=50)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0"
        )
        
        for query in search_queries:
            page = await context.new_page()
            # Construct keyword-specific URL
            search_url = BASE_URL + KEYWORD_SEARCH_URL.format(keyword=query)
            print(f"\n[Kaiser] Searching for '{query}'...")
            
            try:
                await page.goto(search_url, timeout=60000)
                await asyncio.sleep(2)
                await _dismiss_cookie_banner(page)
                
                total_jobs = await _get_total_job_count(page)
                if total_jobs == 0:
                    print(f"[Kaiser] No jobs found for '{query}'")
                    await page.close()
                    continue
                
                # Scrape pages for this keyword
                current_page = 0
                while True:
                    current_page += 1
                    if max_pages and current_page > max_pages:
                        break
                        
                    # Extract jobs
                    jobs = await _extract_jobs_from_page(page)
                    new_count = 0
                    for job in jobs:
                        if job['link'] not in all_jobs_dict:
                            all_jobs_dict[job['link']] = job
                            new_count += 1
                    
                    print(f"  [Kaiser] '{query}' Page {current_page}: +{new_count} new (Total unique: {len(all_jobs_dict)})")
                    
                    if new_count == 0 and current_page > 1:
                        break
                        
                    # Next button
                    next_btn = await page.query_selector('a.next:not(.disabled)')
                    if not next_btn:
                        break
                    
                    await next_btn.evaluate('el => el.click()')
                    await asyncio.sleep(1.5)
                    
            except Exception as e:
                print(f"[Kaiser] Error searching '{query}': {e}")
            
            await page.close()
            
        await browser.close()
        
    result = list(all_jobs_dict.values())
    print(f"\n[Kaiser] Finished. Found {len(result)} total unique jobs across all keywords.")
    return result


if __name__ == "__main__":
    async def test():
        # Test with limited pages first
        print("Testing Kaiser scraper (5 pages)...")
        jobs = await scrape_kaiser_jobs(headless=True, max_pages=5)
        print(f"\nFound {len(jobs)} jobs from 5 pages:")
        for j in jobs[:10]:
            print(f"- {j['title']} @ {j['location']}")
        
        if jobs:
            print("\nFetching description for first job...")
            desc = await fetch_kaiser_descriptions_batch(jobs[:1], headless=True)
            if desc:
                first_desc = list(desc.values())[0]
                print(f"Description length: {len(first_desc)} chars")
                print(f"Preview: {first_desc[:300]}...")
    
    asyncio.run(test())
