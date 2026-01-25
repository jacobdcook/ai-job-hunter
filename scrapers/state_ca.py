"""
State of California Job Scraper
Website: https://www.calcareers.ca.gov/

Uses URL-based search with filters:
- kw=keyword (e.g., "Information", "IT", "Security")
- locid=418 (Sacramento County) - can be configured

Location IDs (common ones):
- 418 = Sacramento County
- 382 = Los Angeles County
- 417 = San Diego County
- (empty) = All locations
"""

import asyncio
import random
from playwright.async_api import async_playwright

SITE_NAME = "State of California"
BASE_URL = "https://calcareers.ca.gov"
SEARCH_URL = f"{BASE_URL}/CalHRPublic/Search/JobSearchResults.aspx"

# Default location: Sacramento County (locid=418)
# Set to empty string "" for all locations
DEFAULT_LOCATION_ID = "418"

# Delay between actions to avoid being blocked (in seconds)
PAGE_DELAY = 10  # 10 seconds between pages like Kaiser


async def scrape_state_ca_jobs(search_query="IT", location_id=None, headless=False):
    """
    Scrapes State of California jobs using URL-based search.
    
    Args:
        search_query: Keyword to search (e.g., "IT", "Security", "Analyst")
        location_id: Location filter (418=Sacramento, None=all locations)
        headless: Run browser in headless mode
    
    Returns:
        List of job dictionaries
    """
    all_jobs = {}  # Use dict for deduplication by link
    
    if location_id is None:
        location_id = DEFAULT_LOCATION_ID
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, slow_mo=100)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0"
        )
        page = await context.new_page()
        
        # Build search URL
        if location_id:
            search_url = f"{SEARCH_URL}#kw={search_query}&locid={location_id}"
            location_name = f"locid={location_id}"
        else:
            search_url = f"{SEARCH_URL}#kw={search_query}"
            location_name = "All Locations"
        
        print(f"[State CA] Searching for '{search_query}' ({location_name})...")
        
        try:
            # Navigate to search URL
            await page.goto(search_url, timeout=60000)
            await asyncio.sleep(3)  # Wait for page to load
            
            # Wait for results to load (or no results message)
            try:
                await page.wait_for_selector(".job-result-item, .search-result-item, #cphMainContent_lvJobs, .no-results", timeout=15000)
            except:
                print(f"[State CA] Could not find results container for '{search_query}'")
            
            current_page = 0
            consecutive_empty = 0
            
            while True:
                current_page += 1
                
                # Extract jobs from current page
                before_count = len(all_jobs)
                
                # Try multiple selectors for job items
                job_items = await page.query_selector_all(".job-result-item a, .search-result-item a, #cphMainContent_lvJobs a[href*='JobPosting']")
                
                # If no jobs found with those selectors, try finding all links to JobPosting
                if not job_items:
                    job_items = await page.query_selector_all("a[href*='JobPosting.aspx']")
                
                for item in job_items:
                    try:
                        href = await item.get_attribute("href")
                        if not href or "JobPosting.aspx" not in href:
                            continue
                        
                        # Get title - might be the link text or a child element
                        title = await item.inner_text()
                        title = title.strip()
                        
                        if not title or len(title) < 3:
                            # Try to get title from parent or sibling
                            parent = await item.evaluate_handle("el => el.closest('tr, .job-result-item, .search-result-item')")
                            if parent:
                                title_elem = await parent.as_element().query_selector("h2, h3, .job-title, strong")
                                if title_elem:
                                    title = await title_elem.inner_text()
                                    title = title.strip()
                        
                        if not title or len(title) < 3:
                            continue
                        
                        # Build full URL
                        if href.startswith("/"):
                            full_link = BASE_URL + href
                        elif href.startswith("http"):
                            full_link = href
                        else:
                            full_link = f"{BASE_URL}/{href}"
                        
                        # Extract location from the row/item
                        location = "California"
                        try:
                            parent = await item.evaluate_handle("el => el.closest('tr, .job-result-item, .search-result-item')")
                            if parent:
                                loc_elem = await parent.as_element().query_selector(".location, td:nth-child(3), [class*='location']")
                                if loc_elem:
                                    location = await loc_elem.inner_text()
                                    location = location.strip() if location else "California"
                        except:
                            pass
                        
                        # Clean up location
                        if location and location != "California":
                            # Remove extra whitespace
                            location = " ".join(location.split())
                        
                        all_jobs[full_link] = {
                            "title": title,
                            "link": full_link,
                            "location": location,
                            "date_posted": "N/A",
                            "source": SITE_NAME
                        }
                    except Exception as e:
                        continue
                
                new_count = len(all_jobs) - before_count
                print(f"[State CA] Page {current_page}: +{new_count} new jobs (total: {len(all_jobs)})")
                
                # Check for no new jobs
                if new_count == 0:
                    consecutive_empty += 1
                    if consecutive_empty >= 2:
                        print(f"[State CA] No new jobs for {consecutive_empty} pages, stopping")
                        break
                else:
                    consecutive_empty = 0
                
                # Look for next page button (ASP.NET pagination)
                # Common patterns: "Next", ">", page number links
                next_btn = None
                
                # Try various selectors for the "Next" button
                next_selectors = [
                    "a:has-text('Next')",
                    "a:has-text('>')",
                    ".pagination a.next",
                    "a[href*='Page$Next']",
                    ".pager a:has-text('Next')",
                    "#cphMainContent_ucRepeaterPager_rptPager a:last-child"
                ]
                
                for selector in next_selectors:
                    try:
                        btn = await page.query_selector(selector)
                        if btn and await btn.is_visible():
                            # Check if it's not disabled
                            is_disabled = await btn.get_attribute("disabled")
                            class_attr = await btn.get_attribute("class") or ""
                            if not is_disabled and "disabled" not in class_attr.lower():
                                next_btn = btn
                                break
                    except:
                        continue
                
                if not next_btn:
                    print(f"[State CA] No more pages (next button not found)")
                    break
                
                # Wait before clicking next (be respectful!)
                print(f"[State CA] Waiting {PAGE_DELAY}s before next page...")
                await asyncio.sleep(PAGE_DELAY + random.uniform(0, 2))
                
                # Click next page
                try:
                    await next_btn.click()
                    await page.wait_for_load_state("networkidle", timeout=30000)
                    await asyncio.sleep(2)  # Extra wait for AJAX content
                except Exception as e:
                    print(f"[State CA] Error clicking next: {e}")
                    break
            
        except Exception as e:
            print(f"[State CA] Error during scraping: {e}")
        
        await browser.close()
    
    result = list(all_jobs.values())
    print(f"[State CA] Total unique jobs scraped for '{search_query}': {len(result)}")
    return result


async def scrape_all_state_ca_jobs(search_queries=None, location_id=None, headless=False):
    """
    Comprehensive State CA scraper that searches multiple keywords.
    
    Args:
        search_queries: List of keywords to search
        location_id: Location filter (418=Sacramento, None=all locations)
        headless: Run browser in headless mode
    
    Returns:
        List of unique job dictionaries
    """
    all_jobs = {}
    
    if not search_queries:
        search_queries = ["IT", "Security", "Analyst"]
    
    for query in search_queries:
        jobs = await scrape_state_ca_jobs(query, location_id, headless)
        for job in jobs:
            all_jobs[job['link']] = job
        
        # Wait between different keyword searches
        if query != search_queries[-1]:
            wait_time = PAGE_DELAY + random.uniform(0, 3)
            print(f"[State CA] Waiting {wait_time:.1f}s before next keyword...")
            await asyncio.sleep(wait_time)
    
    result = list(all_jobs.values())
    print(f"\n[State CA] Finished. Found {len(result)} total unique jobs.")
    return result


async def fetch_state_ca_descriptions_batch(jobs, headless=False):
    """
    Fetch descriptions for multiple State CA jobs using ONE browser instance.
    Uses slow delays to avoid being blocked.
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
            print(f"  [{i}/{total}] Fetching State CA: {title[:50]}...")
            
            description = ""
            try:
                await page.goto(url, timeout=45000, wait_until="domcontentloaded")
                
                # Check for block page
                page_content = await page.content()
                if "Access Denied" in page_content or "blocked" in page_content.lower():
                    print(f"    !!! BLOCKED by State CA. Stopping further fetches.")
                    break
                
                # Wait with jitter to appear human-like
                sleep_time = PAGE_DELAY + random.uniform(0, 3)
                await asyncio.sleep(sleep_time)
                
                # Try multiple selectors for job description
                selectors = [
                    "#cphMainContent_lblJobDescription",
                    "#cphMainContent_pnlJobDescription",
                    ".job-description",
                    "#job-description",
                    "[id*='Description']",
                    "[id*='JobPosting']",
                    ".job-details",
                    "main article",
                    "#main-content"
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
                print(f"    Error fetching State CA description: {e}")
            
            results[url] = description.strip()
        
        await browser.close()
    
    return results


if __name__ == "__main__":
    async def test():
        # Test with Sacramento County (locid=418) and IT keyword
        print("Testing State CA scraper...")
        jobs = await scrape_state_ca_jobs("IT", location_id="418", headless=False)
        print(f"\nFound {len(jobs)} jobs:")
        for j in jobs[:5]:
            print(f"- {j['title']} ({j['location']})")
        
        if jobs:
            print("\nTesting description fetch for first job...")
            desc = await fetch_state_ca_descriptions_batch(jobs[:1], headless=False)
            if desc:
                first_desc = list(desc.values())[0]
                print(f"Description length: {len(first_desc)} chars")
                print(f"Preview: {first_desc[:300]}...")
    
    asyncio.run(test())
