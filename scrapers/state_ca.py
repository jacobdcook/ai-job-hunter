"""
State of California Job Scraper
Website: https://www.calcareers.ca.gov/

Search/pagination requires Playwright (ASP.NET AJAX UpdatePanel with
__VIEWSTATE chaining and JavaScript-dependent postbacks).
Description fetching uses plain HTTP (job detail pages are simple GETs).
"""

import asyncio
import random
import re
import aiohttp
from playwright.async_api import async_playwright

SITE_NAME = "State of California"
BASE_URL = "https://calcareers.ca.gov"
ADVANCED_SEARCH_URL = f"{BASE_URL}/CalHRPublic/Search/AdvancedJobSearch.aspx"

# Default location: Sacramento County
DEFAULT_LOCATION = "Sacramento County"

# Delay between actions (seconds) - generous to avoid timeouts on slow CalCareers responses
PAGE_DELAY = 12
SEARCH_DELAY = 8
# How long to wait for search results to load (ms) - "IT" and big result sets can be slow
SEARCH_RESULTS_TIMEOUT_MS = 90000  # 90 seconds
PAGE_DEFAULT_TIMEOUT_MS = 90000    # 90s default for page operations (slow CalCareers)


async def scrape_state_ca_jobs(search_queries=None, location=None, headless=False):
    """
    Scrapes State of California jobs using the Advanced Search form.
    Keeps browser open and reuses it for multiple keyword searches.
    Sets page size to 100 to minimize pagination.

    Args:
        search_queries: List of keywords to search (e.g., ["IT", "Security", "Analyst"])
        location: Location filter (e.g., "Sacramento County", or None for all)
        headless: Run browser in headless mode

    Returns:
        List of job dictionaries
    """
    all_jobs = {}  # Dedup by link

    if search_queries is None:
        search_queries = ["IT", "Security", "Analyst"]

    if location is None:
        location = DEFAULT_LOCATION

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            slow_mo=100,
            args=["--disable-dev-shm-usage", "--disable-gpu"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0"
        )
        page = await context.new_page()
        page.set_default_timeout(PAGE_DEFAULT_TIMEOUT_MS)
        page.set_default_navigation_timeout(90000)  # 90s for navigations

        print(f"[State CA] Opening Advanced Search page...")

        try:
            await page.goto(ADVANCED_SEARCH_URL, timeout=60000)
            await asyncio.sleep(3)

            for query_idx, query in enumerate(search_queries):
                print(f"\n[State CA] Searching for '{query}' ({location or 'All Locations'})...")

                # Navigate back to Advanced Search for subsequent queries
                if query_idx > 0:
                    try:
                        adv_link = await page.query_selector("a:has-text('Advanced Job Search')")
                        if adv_link:
                            await adv_link.click()
                            await page.wait_for_load_state("networkidle", timeout=45000)
                        else:
                            await page.goto(ADVANCED_SEARCH_URL, timeout=60000)
                    except Exception:
                        await page.goto(ADVANCED_SEARCH_URL, timeout=60000)
                    await asyncio.sleep(2)

                # Fill keyword
                keyword_input = await page.query_selector(
                    "#cphMainContent_txtKeyword, input[name='ctl00$cphMainContent$txtKeyword']"
                )
                if keyword_input:
                    await keyword_input.click()
                    await keyword_input.fill("")
                    await asyncio.sleep(0.5)
                    await keyword_input.fill(query)
                    print(f"[State CA] Entered keyword: {query}")
                else:
                    print(f"[State CA] ERROR: Could not find keyword input field")
                    continue

                # Set location filter
                if location:
                    try:
                        loc_input = await page.query_selector("#cphMainContent_ddlLocation_I")
                        if loc_input:
                            await loc_input.click()
                            await asyncio.sleep(0.5)
                            await loc_input.fill("")
                            await loc_input.type(location, delay=50)
                            await asyncio.sleep(1)
                            loc_option = await page.query_selector(
                                f".dxeListBoxItem:has-text('{location}')"
                            )
                            if loc_option:
                                await loc_option.click()
                                await asyncio.sleep(0.5)
                                print(f"[State CA] Location set to: {location}")
                            else:
                                await page.click(f"text='{location}'", timeout=3000)
                                print(f"[State CA] Location set to: {location}")
                        else:
                            loc_dropdown = await page.query_selector("[id*='ddlLocation']")
                            if loc_dropdown:
                                await loc_dropdown.select_option(label=location)
                                print(f"[State CA] Location set to: {location}")
                    except Exception as e:
                        print(f"[State CA] Warning: Could not set location filter: {e}")

                # Click Search
                search_btn = await page.query_selector(
                    "#cphMainContent_btnSearch, input[value='Search Jobs'], button:has-text('Search')"
                )
                if search_btn:
                    await search_btn.click()
                    print(f"[State CA] Clicked Search button, waiting for results (up to {SEARCH_RESULTS_TIMEOUT_MS // 1000}s)...")
                    await page.wait_for_load_state("networkidle", timeout=SEARCH_RESULTS_TIMEOUT_MS)
                    await asyncio.sleep(3)
                    # If CalCareers shows "No jobs found", skip this keyword and go to next (no 90s wait)
                    body_text = await page.evaluate("() => document.body ? document.body.innerText : ''")
                    if body_text and "No jobs found matching your search criteria" in body_text:
                        print(f"[State CA] No jobs found for '{query}', skipping to next keyword.")
                        if query != search_queries[-1]:
                            wait_time = SEARCH_DELAY + random.uniform(0, 2)
                            print(f"[State CA] Waiting {wait_time:.1f}s before next keyword...")
                            await asyncio.sleep(wait_time)
                        continue
                    # Wait for result count element (CalCareers can be slow for large result sets)
                    try:
                        await page.wait_for_selector("#cphMainContent_lblTotalResultCount", state="visible", timeout=SEARCH_RESULTS_TIMEOUT_MS)
                    except Exception as e:
                        print(f"[State CA] Warning: result count element did not appear in time: {e}")
                else:
                    print(f"[State CA] ERROR: Could not find Search button")
                    continue

                # Set page size, get result count, and paginate (one keyword) - catch timeout so we continue to next keyword
                try:
                    await _set_page_size(page, 50)

                    # Get total result count (element already waited for above)
                    total_text = await page.text_content("#cphMainContent_lblTotalResultCount")
                    if total_text:
                        print(f"[State CA] Total results for '{query}': {total_text.strip()}")

                    # Paginate through results
                    current_page = 0
                    consecutive_empty = 0
                    max_pages = 50

                    while current_page < max_pages:
                        current_page += 1
                        before_count = len(all_jobs)

                        jobs_on_page = await _extract_jobs_from_page(page)

                        for job in jobs_on_page:
                            all_jobs[job['link']] = job

                        new_count = len(all_jobs) - before_count
                        print(f"[State CA] Page {current_page}: {len(jobs_on_page)} jobs on page, +{new_count} new (total: {len(all_jobs)})")

                        if new_count == 0:
                            consecutive_empty += 1
                            if consecutive_empty >= 2:
                                print(f"[State CA] No new jobs for {consecutive_empty} pages, moving on")
                                break
                        else:
                            consecutive_empty = 0

                        # Find next page
                        next_btn = await _find_next_button(page, current_page + 1)

                        if not next_btn:
                            print(f"[State CA] No more pages for '{query}' (reached page {current_page})")
                            break

                        print(f"[State CA] Waiting {PAGE_DELAY}s before next page...")
                        await asyncio.sleep(PAGE_DELAY + random.uniform(0, 2))

                        try:
                            await next_btn.scroll_into_view_if_needed()
                            await asyncio.sleep(0.5)
                            await next_btn.evaluate("el => el.click()")
                            await asyncio.sleep(3)
                            await page.wait_for_load_state("networkidle", timeout=45000)
                            await asyncio.sleep(2)
                        except Exception as e:
                            print(f"[State CA] Error navigating to next page: {e}")
                            if "closed" in str(e).lower() or "crash" in str(e).lower():
                                print(f"[State CA] Browser lost, keeping {len(all_jobs)} jobs scraped so far")
                                break
                            await asyncio.sleep(2)
                            continue

                except Exception as e:
                    print(f"[State CA] Timeout or error for keyword '{query}' (continuing with next): {e}")

                if query != search_queries[-1]:
                    wait_time = SEARCH_DELAY + random.uniform(0, 2)
                    print(f"[State CA] Waiting {wait_time:.1f}s before next keyword...")
                    await asyncio.sleep(wait_time)

        except Exception as e:
            print(f"[State CA] Error during scraping: {e}")

        try:
            await browser.close()
        except Exception:
            pass

    result = list(all_jobs.values())
    print(f"\n[State CA] Total unique jobs scraped: {len(result)}")
    return result


async def _set_page_size(page, size=100):
    """
    Set the results page size dropdown to show more jobs per page.
    CalCareers supports 10, 20, 50, 100 via ddlRowCount.
    """
    try:
        dropdown = await page.query_selector("#cphMainContent_ddlRowCount")
        if dropdown:
            current = await dropdown.input_value()
            if current != str(size):
                await dropdown.select_option(str(size))
                print(f"[State CA] Set page size to {size} (was {current})")
                await asyncio.sleep(2)
                await page.wait_for_load_state("networkidle", timeout=45000)
                await asyncio.sleep(2)
    except Exception as e:
        print(f"[State CA] Could not set page size: {e}")


async def _extract_jobs_from_page(page):
    """
    Extract job listings from the current results page.
    Uses the structured card HTML from the CalCareers AJAX response:
    each job is a .card with well-defined .details rows.
    """
    jobs = []

    no_jobs = await page.query_selector("text='No jobs found matching your search criteria'")
    if no_jobs:
        return jobs

    # Extract all job cards using the known HTML structure
    job_data = await page.evaluate("""
        () => {
            const jobs = [];
            const cards = document.querySelectorAll('.card.card-default');

            for (const card of cards) {
                try {
                    // Title link: <a class="lead visitedLink" href="...JobPosting.aspx?JobControlId=XXXXXX">
                    const titleLink = card.querySelector('a.lead[href*="JobPosting"]');
                    if (!titleLink) continue;

                    const href = titleLink.getAttribute('href');
                    const classification = titleLink.textContent.trim();

                    // Helper to get a detail field value
                    function getDetail(className) {
                        const row = card.querySelector('.' + className + ' .job-details');
                        return row ? row.textContent.trim() : '';
                    }

                    const workingTitle = getDetail('working-title');
                    const salary = getDetail('salary-range');
                    const department = getDetail('department');
                    const location = getDetail('location');
                    const schedule = getDetail('schedule');
                    const telework = getDetail('telework');

                    // Filing deadline and publish date - use label/details structure
                    let filingDeadline = '';
                    let publishDate = '';
                    const dateRows = card.querySelectorAll('.filing-date');
                    for (const row of dateRows) {
                        const label = row.querySelector('.job-label');
                        const details = row.querySelector('.job-details');
                        if (!label) continue;
                        const labelText = label.textContent.trim();
                        const value = details ? details.textContent.trim() : '';
                        if (labelText.includes('Filing Deadline') && value) {
                            filingDeadline = value;
                        } else if (labelText.includes('Publish Date') && value) {
                            publishDate = value;
                        }
                    }

                    jobs.push({
                        classification: classification,
                        workingTitle: workingTitle,
                        href: href,
                        location: location || 'California',
                        filingDeadline: filingDeadline || 'N/A',
                        publishDate: publishDate || 'N/A',
                        salary: salary,
                        department: department,
                        schedule: schedule,
                        telework: telework
                    });
                } catch (e) {
                    continue;
                }
            }
            return jobs;
        }
    """)

    for job in job_data:
        try:
            href = job.get('href', '')
            if not href:
                continue

            if href.startswith("/"):
                full_link = BASE_URL + href
            elif href.startswith("http"):
                full_link = href
            else:
                full_link = f"{BASE_URL}/{href}"

            # Use working title if available, classification as fallback
            working_title = job.get('workingTitle', '')
            classification = job.get('classification', '')
            if working_title and classification and working_title != classification:
                title = f"{working_title} ({classification})"
            elif working_title:
                title = working_title
            elif classification:
                title = classification
            else:
                title = "Job Posting"

            # Build description from search result metadata
            desc_parts = []
            if classification:
                desc_parts.append(f"Classification: {classification}")
            if working_title and working_title != classification:
                desc_parts.append(f"Working Title: {working_title}")
            salary = job.get('salary', '')
            if salary:
                desc_parts.append(f"Salary Range: {salary}")
            department = job.get('department', '')
            if department:
                desc_parts.append(f"Department: {department}")
            schedule = job.get('schedule', '')
            if schedule:
                desc_parts.append(f"Schedule: {schedule}")
            telework = job.get('telework', '')
            if telework:
                desc_parts.append(f"Telework: {telework}")

            jobs.append({
                "title": title,
                "link": full_link,
                "location": job.get('location', 'California'),
                "date_posted": job.get('filingDeadline', 'N/A'),
                "source": SITE_NAME,
                # Extra metadata saved for reference
                "salary": salary,
                "department": department,
                "_search_desc": "\n".join(desc_parts),
            })

        except Exception:
            continue

    return jobs


async def _find_next_button(page, target_page):
    """
    Find the button for a specific page number in the CalCareers pager.
    The pager uses ASP.NET repeater buttons (btnPagerItem).
    If the exact page number isn't visible, looks for ">>" to jump forward.
    """
    try:
        pager_buttons = await page.query_selector_all("[id*='btnPagerItem']")

        if not pager_buttons:
            return None

        # First try to find exact page number
        for btn in pager_buttons:
            try:
                text = await btn.get_attribute("value")
                if not text:
                    text = await btn.inner_text()
                text = text.strip() if text else ""

                if text.isdigit() and int(text) == target_page:
                    is_disabled = await btn.get_attribute("disabled")
                    if is_disabled:
                        return None
                    return btn
            except Exception:
                continue

        # Exact page not found -- try ">>" button to jump forward
        for btn in pager_buttons:
            try:
                text = await btn.get_attribute("value")
                if not text:
                    text = await btn.inner_text()
                text = text.strip() if text else ""

                if text == ">>":
                    print(f"[State CA] Page {target_page} not in pager window, clicking >> to jump forward")
                    return btn
            except Exception:
                continue

        return None

    except Exception as e:
        print(f"[State CA] Error finding page button: {e}")

    return None


async def fetch_state_ca_descriptions_batch(jobs, headless=False):
    """
    Fetch descriptions for State CA jobs using plain HTTP requests.
    Job detail pages (JobPosting.aspx?JobControlId=X) are simple GETs
    with no auth/cookies/JavaScript needed.
    Returns (descriptions_dict, titles_dict). titles_dict has url -> parsed title
    for every page we successfully parsed (so "Job Posting" rows can be fixed).
    """
    if not jobs:
        return {}, {}

    results = {}
    titles = {}

    async with aiohttp.ClientSession(headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }) as session:

        total = len(jobs)
        for i, job in enumerate(jobs, 1):
            url = job['link']
            title = job.get('title', '') or 'Job Posting'
            print(f"  [{i}/{total}] Fetching State CA: {title[:50]}...")

            description = ""
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30),
                                       allow_redirects=True) as resp:
                    if resp.status != 200:
                        print(f"    HTTP {resp.status}")
                        results[url] = ""
                        continue

                    html = await resp.text()

                    # Check for block
                    if "Access Denied" in html or "blocked" in html.lower()[:500]:
                        print(f"    !!! BLOCKED by State CA. Stopping further fetches.")
                        break

                    description = _parse_job_description(html)
                    parsed_title = _parse_job_title_from_html(html)
                    if parsed_title:
                        titles[url] = parsed_title
                        print(f"    -> Got title: {parsed_title[:60]}{'...' if len(parsed_title) > 60 else ''}")

            except Exception as e:
                print(f"    Error: {e}")

            results[url] = description.strip() if description else ""

            # Polite delay between fetches
            if i < total:
                sleep_time = 3 + random.uniform(0, 2)
                await asyncio.sleep(sleep_time)

    return results, titles


def _parse_job_title_from_html(html):
    """
    Parse a CalCareers job posting HTML page and return the job title.
    Uses Working Title if present, else Primary Classification.
    CalCareers uses lblWorkingTitleHeader (not lblWorkingTitle) for the visible title.
    Returns empty string if neither found.
    """
    # Site uses lblWorkingTitleHeader for the job title; fallback to lblWorkingTitle
    wt_match = re.search(r'id="lblWorkingTitleHeader"[^>]*>([^<]+)<', html)
    if not wt_match:
        wt_match = re.search(r'id="lblWorkingTitle"[^>]*>([^<]+)<', html)
    working_title = wt_match.group(1).strip() if wt_match else ""
    cls_match = re.search(r'id="lblPrimaryClassification"[^>]*>([^<]+)<', html)
    classification = cls_match.group(1).strip() if cls_match else ""
    if working_title and classification and working_title != classification:
        return f"{working_title} ({classification})"
    if working_title:
        return working_title
    if classification:
        return classification
    return ""


def _parse_job_description(html):
    """
    Parse a CalCareers job posting HTML page and extract the description.
    The page uses jcBand sections with well-structured HTML.
    """
    # Try to find the JobDescription div first (most reliable)
    desc_match = re.search(
        r'id="JobDescription"[^>]*>(.*?)</div>\s*</div>\s*</div>',
        html, re.DOTALL | re.IGNORECASE
    )

    parts = []

    # Extract working title (CalCareers uses lblWorkingTitleHeader)
    wt_match = re.search(r'id="lblWorkingTitleHeader"[^>]*>([^<]+)<', html)
    if not wt_match:
        wt_match = re.search(r'id="lblWorkingTitle"[^>]*>([^<]+)<', html)
    if wt_match:
        parts.append(f"Working Title: {wt_match.group(1).strip()}")

    # Extract classification
    cls_match = re.search(r'id="lblPrimaryClassification"[^>]*>([^<]+)<', html)
    if cls_match:
        parts.append(f"Classification: {cls_match.group(1).strip()}")

    # Extract salary
    sal_match = re.search(r'id="lblSalaryRange"[^>]*>([^<]+)<', html)
    if sal_match:
        parts.append(f"Salary: {sal_match.group(1).strip()}")

    # Extract location
    loc_match = re.search(r'id="lblWorkLocation"[^>]*>([^<]+)<', html)
    if loc_match:
        parts.append(f"Location: {loc_match.group(1).strip()}")

    # Extract job type
    jt_match = re.search(r'id="lblJobType"[^>]*>([^<]+)<', html)
    if jt_match:
        parts.append(f"Job Type: {jt_match.group(1).strip()}")

    # Extract telework
    tw_match = re.search(r'id="lblTelework"[^>]*>([^<]+)<', html)
    if tw_match:
        parts.append(f"Telework: {tw_match.group(1).strip()}")

    # Extract department info
    dept_match = re.search(r'id="lblDepartmentInfo"[^>]*>(.*?)</span>', html, re.DOTALL)
    if dept_match:
        dept_text = re.sub(r'<[^>]+>', ' ', dept_match.group(1)).strip()
        dept_text = re.sub(r'\s+', ' ', dept_text)
        if dept_text:
            parts.append(f"Department: {dept_text}")

    if parts:
        parts.append("")  # separator

    # Main job description text - extract from all jcBand sections
    # These contain: Description, Requirements, Position Details, etc.
    band_sections = re.findall(
        r'<div[^>]*class="[^"]*jcBand[^"]*"[^>]*>(.*?)</div>\s*(?=<div[^>]*class="[^"]*jcBand|$)',
        html, re.DOTALL | re.IGNORECASE
    )

    for section in band_sections:
        # Strip HTML tags, decode entities
        text = re.sub(r'<br\s*/?>', '\n', section)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
        text = text.replace('&lt;', '<').replace('&gt;', '>')
        text = re.sub(r'\s+', ' ', text).strip()
        if text and len(text) > 20:
            parts.append(text)

    # If jcBand extraction didn't work, try a broader approach
    if not band_sections:
        # Fall back to getting text from the main content area
        main_match = re.search(
            r'id="cphMainContent_pnlJobDetails"[^>]*>(.*?)</div>\s*</div>\s*</div>',
            html, re.DOTALL | re.IGNORECASE
        )
        if main_match:
            text = re.sub(r'<br\s*/?>', '\n', main_match.group(1))
            text = re.sub(r'<[^>]+>', ' ', text)
            text = text.replace('&nbsp;', ' ')
            text = re.sub(r'\s+', ' ', text).strip()
            if text:
                parts.append(text)

    return "\n".join(parts)


# Backwards compatibility
async def scrape_all_state_ca_jobs(search_queries=None, location_id=None, headless=False):
    """Wrapper for backwards compatibility."""
    location_map = {
        "418": "Sacramento County",
        "382": "Los Angeles County",
        "417": "San Diego County",
        "": None,
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
            search_queries=["Information"],
            location="Sacramento County",
            headless=False
        )

        print(f"\nFound {len(jobs)} jobs:")
        for j in jobs[:10]:
            print(f"- {j['title'][:60]}... ({j['location']})")
            print(f"  {j['link']}")

        if jobs:
            print("\nTesting description fetch for first 2 jobs...")
            desc, titles = await fetch_state_ca_descriptions_batch(jobs[:2], headless=False)
            for url, d in desc.items():
                print(f"\nDescription length: {len(d)} chars")
                if d:
                    print(f"Preview: {d[:300]}...")

    asyncio.run(test())
