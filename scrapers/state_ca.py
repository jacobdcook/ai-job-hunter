"""
State of California Job Scraper
Website: https://www.calcareers.ca.gov/

Uses the Advanced Search form to find jobs.
Keeps browser open between searches for efficiency.
"""

import asyncio
import random
from playwright.async_api import async_playwright

SITE_NAME = "State of California"
BASE_URL = "https://calcareers.ca.gov"
ADVANCED_SEARCH_URL = f"{BASE_URL}/CalHRPublic/Search/AdvancedJobSearch.aspx"

# Default location: Sacramento County
# To find your location: go to Advanced Search, select a county, and note the dropdown value
DEFAULT_LOCATION = "Sacramento County"

# Delay between actions to avoid being blocked (in seconds)
PAGE_DELAY = 10  # 10 seconds between pages like Kaiser
SEARCH_DELAY = 5  # 5 seconds between searches


async def scrape_state_ca_jobs(search_queries=None, location=None, headless=False):
    """
    Scrapes State of California jobs using the Advanced Search form.
    Keeps browser open and reuses it for multiple keyword searches.
    
    Args:
        search_queries: List of keywords to search (e.g., ["IT", "Security", "Analyst"])
        location: Location filter (e.g., "Sacramento County", or None for all)
        headless: Run browser in headless mode
    
    Returns:
        List of job dictionaries
    """
    all_jobs = {}  # Use dict for deduplication by link
    
    if search_queries is None:
        search_queries = ["IT", "Security", "Analyst"]
    
    if location is None:
        location = DEFAULT_LOCATION
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, slow_mo=100)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0"
        )
        page = await context.new_page()
        
        print(f"[State CA] Opening Advanced Search page...")
        
        try:
            # Go to Advanced Search page ONCE
            await page.goto(ADVANCED_SEARCH_URL, timeout=60000)
            await asyncio.sleep(3)  # Wait for page to load
            
            # Loop through each keyword (reusing same browser session)
            for query_idx, query in enumerate(search_queries):
                print(f"\n[State CA] Searching for '{query}' ({location or 'All Locations'})...")
                
                # If not the first search, we need to go back to Advanced Search
                if query_idx > 0:
                    # Click "Advanced Job Search" link or navigate back
                    try:
                        adv_link = await page.query_selector("a:has-text('Advanced Job Search')")
                        if adv_link:
                            await adv_link.click()
                            await page.wait_for_load_state("networkidle", timeout=30000)
                        else:
                            await page.goto(ADVANCED_SEARCH_URL, timeout=60000)
                    except:
                        await page.goto(ADVANCED_SEARCH_URL, timeout=60000)
                    
                    await asyncio.sleep(2)
                
                # Clear and fill the keyword input
                keyword_input = await page.query_selector("#cphMainContent_txtKeyword, input[name='ctl00$cphMainContent$txtKeyword']")
                if keyword_input:
                    await keyword_input.click()
                    await keyword_input.fill("")  # Clear first
                    await asyncio.sleep(0.5)
                    await keyword_input.fill(query)
                    print(f"[State CA] Entered keyword: {query}")
                else:
                    print(f"[State CA] ERROR: Could not find keyword input field")
                    continue
                
                # Set location filter if specified
                if location:
                    try:
                        # CalCareers uses DevExpress dropdowns with a specific structure
                        # We need to: 1) Click the dropdown, 2) Type/search, 3) Select the option
                        
                        # First, try clicking the dropdown input to open it
                        loc_input = await page.query_selector("#cphMainContent_ddlLocation_I")
                        if loc_input:
                            await loc_input.click()
                            await asyncio.sleep(0.5)
                            
                            # Clear and type the location name
                            await loc_input.fill("")
                            await loc_input.type(location, delay=50)
                            await asyncio.sleep(1)
                            
                            # Click on the matching option in the dropdown list
                            loc_option = await page.query_selector(f".dxeListBoxItem:has-text('{location}')")
                            if loc_option:
                                await loc_option.click()
                                await asyncio.sleep(0.5)
                                print(f"[State CA] Location set to: {location}")
                            else:
                                # Try clicking the first visible option that matches
                                await page.click(f"text='{location}'", timeout=3000)
                                print(f"[State CA] Location set to: {location}")
                        else:
                            # Fallback: try the older dropdown selector
                            loc_dropdown = await page.query_selector("[id*='ddlLocation']")
                            if loc_dropdown:
                                await loc_dropdown.select_option(label=location)
                                print(f"[State CA] Location set to: {location}")
                    except Exception as e:
                        print(f"[State CA] Warning: Could not set location filter: {e}")
                        print(f"[State CA] Results may include jobs from all locations")
                
                # Click the Search button
                search_btn = await page.query_selector("#cphMainContent_btnSearch, input[value='Search Jobs'], button:has-text('Search')")
                if search_btn:
                    await search_btn.click()
                    print(f"[State CA] Clicked Search button, waiting for results...")
                    
                    # Wait for results page to load
                    await page.wait_for_load_state("networkidle", timeout=45000)
                    await asyncio.sleep(3)  # Extra wait for dynamic content
                else:
                    print(f"[State CA] ERROR: Could not find Search button")
                    continue
                
                # Now extract jobs from the results page
                current_page = 0
                consecutive_empty = 0
                max_pages = 50  # Safety limit to prevent infinite loops
                
                while current_page < max_pages:
                    current_page += 1
                    before_count = len(all_jobs)
                    
                    # Extract jobs from the current results page
                    jobs_on_page = await _extract_jobs_from_page(page)
                    
                    for job in jobs_on_page:
                        all_jobs[job['link']] = job
                    
                    new_count = len(all_jobs) - before_count
                    print(f"[State CA] Page {current_page}: +{new_count} new jobs (total: {len(all_jobs)})")
                    
                    # Check for no new jobs
                    if new_count == 0:
                        consecutive_empty += 1
                        if consecutive_empty >= 2:
                            print(f"[State CA] No new jobs for {consecutive_empty} pages, moving to next keyword")
                            break
                    else:
                        consecutive_empty = 0
                    
                    # Look for Next page button - we track page number ourselves
                    next_btn = await _find_next_button(page, current_page + 1)
                    
                    if not next_btn:
                        print(f"[State CA] No more pages for '{query}' (reached page {current_page})")
                        break
                    
                    # Wait before clicking next (be respectful!)
                    print(f"[State CA] Waiting {PAGE_DELAY}s before next page...")
                    await asyncio.sleep(PAGE_DELAY + random.uniform(0, 2))
                    
                    # Click next page - ASP.NET buttons need special handling
                    try:
                        # Scroll to button to ensure it's visible
                        await next_btn.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        
                        # For ASP.NET postback buttons, use JavaScript click
                        # This triggers the __doPostBack properly
                        await next_btn.evaluate("el => el.click()")
                        
                        # Wait for AJAX update panel to refresh
                        await asyncio.sleep(3)  # Initial wait for AJAX
                        await page.wait_for_load_state("networkidle", timeout=30000)
                        await asyncio.sleep(2)  # Extra wait for dynamic content
                    except Exception as e:
                        print(f"[State CA] Error clicking next: {e}")
                        # Try to continue - maybe the page already changed
                        await asyncio.sleep(2)
                        continue
                
                # Wait between keyword searches
                if query != search_queries[-1]:
                    wait_time = SEARCH_DELAY + random.uniform(0, 2)
                    print(f"[State CA] Waiting {wait_time:.1f}s before next keyword...")
                    await asyncio.sleep(wait_time)
                
        except Exception as e:
            print(f"[State CA] Error during scraping: {e}")
        
        await browser.close()
    
    result = list(all_jobs.values())
    print(f"\n[State CA] Total unique jobs scraped: {len(result)}")
    return result


async def _extract_jobs_from_page(page):
    """Extract job listings from the current results page."""
    jobs = []
    
    # Check for "No jobs found" message
    no_jobs = await page.query_selector("text='No jobs found matching your search criteria'")
    if no_jobs:
        return jobs
    
    # CalCareers job listings are in a structured format with job cards/rows
    # Each job has: Title (link), Working Title, Job Control, Salary, Department, Location, Filing Deadline
    # We'll extract all this info by finding job containers and parsing their content
    
    # Try to get all job listing containers - they're typically in a list/table structure
    job_data = await page.evaluate("""
        () => {
            const jobs = [];
            
            // Find all job posting links
            const jobLinks = document.querySelectorAll('a[href*="JobPosting.aspx"]');
            
            for (const link of jobLinks) {
                try {
                    const href = link.getAttribute('href');
                    
                    // Find the parent container that holds all job info
                    // Walk up to find a container with filing deadline info
                    let container = link.parentElement;
                    for (let i = 0; i < 10 && container; i++) {
                        if (container.innerText && container.innerText.includes('Filing Deadline')) {
                            break;
                        }
                        container = container.parentElement;
                    }
                    
                    const containerText = container ? container.innerText : '';
                    
                    // Extract Classification Title (e.g., "INFORMATION TECHNOLOGY SPECIALIST I")
                    // Look for text before the link that looks like a job classification
                    let classification = '';
                    
                    // Try to find text node or element before the link
                    let prevSibling = link.previousSibling;
                    while (prevSibling && !classification) {
                        if (prevSibling.nodeType === 3) { // Text node
                            const text = prevSibling.textContent.trim();
                            if (text && text.length > 5 && /[A-Z]/.test(text)) {
                                classification = text;
                            }
                        } else if (prevSibling.nodeType === 1) { // Element
                            const text = prevSibling.textContent.trim();
                            if (text && text.length > 5 && /[A-Z]/.test(text)) {
                                classification = text;
                            }
                        }
                        prevSibling = prevSibling.previousSibling;
                    }
                    
                    // If still not found, try regex on container text
                    if (!classification) {
                        const classificationMatch = containerText.match(/^([A-Z][A-Z\\s&]+(?:SPECIALIST|ANALYST|TECHNICIAN|ENGINEER|OFFICER|ADMINISTRATOR|MANAGER|COORDINATOR|ASSISTANT|SUPERVISOR)[^\\n]*)/);
                        if (classificationMatch) {
                            classification = classificationMatch[1].trim();
                        }
                    }
                    
                    // Last resort: look for heading/strong tag
                    if (!classification && container) {
                        let heading = container.querySelector('h1, h2, h3, h4, h5, strong, b, .job-title');
                        if (heading) {
                            classification = heading.innerText.trim();
                        }
                    }
                    
                    // Extract Working Title (more specific than classification)
                    let workingTitle = '';
                    const workingTitleMatch = containerText.match(/Working Title[:\\s]*([^\\n]+)/i);
                    if (workingTitleMatch) {
                        workingTitle = workingTitleMatch[1].trim();
                    }
                    
                    // Use working title if available, otherwise classification
                    const displayTitle = workingTitle || classification || 'Job Posting';
                    
                    // Extract Filing Deadline
                    let filingDeadline = 'N/A';
                    const deadlineMatch = containerText.match(/Filing Deadline[:\\s]*([\\d\\/\\-]+)/i);
                    if (deadlineMatch) {
                        filingDeadline = deadlineMatch[1].trim();
                    }
                    
                    // Extract Location
                    let location = 'California';
                    const locationMatch = containerText.match(/Location[:\\s]*([^\\n]+)/i);
                    if (locationMatch) {
                        location = locationMatch[1].trim();
                    }
                    
                    // Extract Salary Range
                    let salary = '';
                    const salaryMatch = containerText.match(/Salary Range[:\\s]*([^\\n]+)/i);
                    if (salaryMatch) {
                        salary = salaryMatch[1].trim();
                    }
                    
                    // Extract Department
                    let department = '';
                    const deptMatch = containerText.match(/Department[:\\s]*([^\\n]+)/i);
                    if (deptMatch) {
                        department = deptMatch[1].trim();
                    }
                    
                    jobs.push({
                        title: displayTitle,
                        classification: classification || displayTitle,
                        href: href,
                        location: location,
                        filingDeadline: filingDeadline,
                        salary: salary,
                        department: department
                    });
                } catch (e) {
                    continue;
                }
            }
            
            return jobs;
        }
    """)
    
    # Process extracted data
    for job in job_data:
        try:
            href = job.get('href', '')
            if not href:
                continue
            
            # Build full URL
            if href.startswith("/"):
                full_link = BASE_URL + href
            elif href.startswith("http"):
                full_link = href
            else:
                full_link = f"{BASE_URL}/{href}"
            
            # Combine title with classification if different
            title = job.get('title', '')
            classification = job.get('classification', '')
            if classification and classification != title:
                title = f"{title} ({classification})"
            
            jobs.append({
                "title": title,
                "link": full_link,
                "location": job.get('location', 'California'),
                "date_posted": job.get('filingDeadline', 'N/A'),  # Use filing deadline as date_posted
                "filing_deadline": job.get('filingDeadline', 'N/A'),
                "salary": job.get('salary', ''),
                "department": job.get('department', ''),
                "source": SITE_NAME
            })
            
        except Exception as e:
            continue
    
    return jobs


async def _find_next_button(page, target_page):
    """
    Find the button for a specific page number.
    CalCareers uses ASP.NET buttons (btnPagerItem) for pagination, NOT links.
    The buttons are inside a repeater control with IDs like:
    cphMainContent_ucRepeaterPager_rptPager_ctl01_btnPagerItem (page 2)
    cphMainContent_ucRepeaterPager_rptPager_ctl02_btnPagerItem (page 3)
    etc.
    
    Args:
        page: Playwright page object
        target_page: The page number we want to go to
    """
    
    try:
        # CalCareers uses buttons with ID containing 'btnPagerItem'
        # These are input[type=submit] or button elements, NOT <a> links
        pager_buttons = await page.query_selector_all("[id*='btnPagerItem']")
        
        if not pager_buttons:
            print(f"[State CA] No pager buttons found")
            return None
        
        print(f"[State CA] Found {len(pager_buttons)} pager buttons, looking for page {target_page}")
        
        for btn in pager_buttons:
            try:
                # Get the button text (page number) - could be in 'value' attr or inner text
                text = await btn.get_attribute("value")
                if not text:
                    text = await btn.inner_text()
                text = text.strip() if text else ""
                
                if text.isdigit() and int(text) == target_page:
                    # Check if this button is clickable (not disabled)
                    is_disabled = await btn.get_attribute("disabled")
                    if is_disabled:
                        print(f"[State CA] Page {target_page} button is disabled (we're on that page)")
                        return None
                    
                    print(f"[State CA] Found clickable button for page {target_page}")
                    return btn
            except Exception as e:
                continue
        
        # Button for target page not found - might be at end of pagination or need to click "..."
        print(f"[State CA] Page {target_page} button not found in current pagination")
        return None
        
    except Exception as e:
        print(f"[State CA] Error finding page button: {e}")
    
    return None


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
                    ".job-details",
                    "#cphMainContent_pnlJobDetails",
                    "main article",
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


# Keep backwards compatibility with old function name
async def scrape_all_state_ca_jobs(search_queries=None, location_id=None, headless=False):
    """
    Wrapper for backwards compatibility.
    location_id is ignored - use location name directly in scrape_state_ca_jobs.
    """
    # Map common location IDs to names (for backwards compat)
    location_map = {
        "418": "Sacramento County",
        "382": "Los Angeles County",
        "417": "San Diego County",
        "": None,  # All locations
        None: None,
    }
    
    location = location_map.get(location_id, None)
    return await scrape_state_ca_jobs(search_queries, location, headless)


if __name__ == "__main__":
    async def test():
        print("Testing State CA scraper...")
        print("This will open a browser and search for 'Information' in Sacramento County")
        print("-" * 60)
        
        jobs = await scrape_state_ca_jobs(
            search_queries=["Information"],  # Use "Information" since that's what HAR used
            location="Sacramento County",
            headless=False
        )
        
        print(f"\nFound {len(jobs)} jobs:")
        for j in jobs[:10]:
            print(f"- {j['title'][:60]}... ({j['location']})")
            print(f"  {j['link']}")
        
        if jobs:
            print("\nTesting description fetch for first job...")
            desc = await fetch_state_ca_descriptions_batch(jobs[:1], headless=False)
            if desc:
                first_desc = list(desc.values())[0]
                print(f"Description length: {len(first_desc)} chars")
                if first_desc:
                    print(f"Preview: {first_desc[:300]}...")
    
    asyncio.run(test())
