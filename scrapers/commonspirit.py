"""
CommonSpirit Health Job Scraper
Website: https://www.commonspirit.careers
Platform: TalentBrew

Brands included: Dignity Health, CHI, Virginia Mason Franciscan Health

Search: URL-path based with AJAX pagination API returning JSON with HTML results.
Job details: JSON-LD structured data embedded in page.
"""

import asyncio
import json
import re
import aiohttp
from urllib.parse import quote, urlencode

SITE_NAME = "CommonSpirit"
BASE_URL = "https://www.commonspirit.careers"

# Sacramento area search parameters
DEFAULT_LOCATION = "95826, Sacramento, CA"
DEFAULT_LATITUDE = "38.55390"
DEFAULT_LONGITUDE = "-121.36930"
DEFAULT_RADIUS = 50
DEFAULT_ORG_ID = "35300"  # CommonSpirit Health organization
LOCATION_TYPE = "4"
LOCATION_PATH = "6252001-5332921-5389519-5389489"  # California > Sacramento County > Sacramento

# Pagination
RECORDS_PER_PAGE = 11

# Delays (be polite)
PAGE_DELAY = 2
DESC_DELAY = 1


def _build_search_url(location=None):
    """Build initial search page URL for specified location (default: Sacramento area)."""
    loc = location or DEFAULT_LOCATION
    location_encoded = quote(loc, safe='')
    lat = DEFAULT_LATITUDE.replace('.', 'x')
    lon = DEFAULT_LONGITUDE.replace('.', 'x')

    return (
        f"{BASE_URL}/search-jobs/{location_encoded}/{DEFAULT_ORG_ID}/"
        f"{LOCATION_TYPE}/{LOCATION_PATH}/{lat}/{lon}/{DEFAULT_RADIUS}/2"
    )


def _build_results_api_url(page, location=None, total_results=None):
    """Build AJAX pagination API URL."""
    loc = location or DEFAULT_LOCATION
    params = {
        "ActiveFacetID": "0",
        "CurrentPage": str(page),
        "RecordsPerPage": str(RECORDS_PER_PAGE),
        "TotalContentResults": str(total_results) if total_results else "",
        "Distance": str(DEFAULT_RADIUS),
        "RadiusUnitType": "0",
        "Keywords": "",
        "Location": loc,
        "Latitude": DEFAULT_LATITUDE,
        "Longitude": DEFAULT_LONGITUDE,
        "ShowRadius": "True",
        "IsPagination": "True",
        "CustomFacetName": "",
        "FacetTerm": "",
        "FacetType": "0",
        "SearchResultsModuleName": "Section 6 - Search Results List",
        "SearchFiltersModuleName": "Section 6 - Search Filters",
        "SortCriteria": "0",
        "SortDirection": "0",
        "SearchType": "1",
        "LocationType": LOCATION_TYPE,
        "LocationPath": LOCATION_PATH,
        "OrganizationIds": DEFAULT_ORG_ID,
        "PostalCode": "",
        "ResultsType": "0",
    }
    return f"{BASE_URL}/search-jobs/results?{urlencode(params)}"


def _parse_jobs_from_html(html):
    """Parse job listings from HTML returned by the API."""
    jobs = []

    # Extract job links with IDs and titles
    job_pattern = r'<a class="search-results-list__job-link" href="([^"]+)" data-job-id="(\d+)"[^>]*>([^<]+)</a>'
    matches = re.findall(job_pattern, html)

    # Build a dict to track jobs by URL (for dedup and matching extra data)
    job_data = {}
    for href, job_id, title in matches:
        url = f"{BASE_URL}{href}" if href.startswith('/') else href
        job_data[url] = {
            "job_id": job_id,
            "title": title.strip(),
        }

    # Extract departments - each <li class="search-results-list__item"> contains one job
    # Match job items to get full context
    item_pattern = r'<li class="search-results-list__item[^"]*">(.*?)</li>'
    items = re.findall(item_pattern, html, re.DOTALL)

    for item in items:
        # Get job link from item
        link_match = re.search(r'href="([^"]+)"[^>]*data-job-id="(\d+)"', item)
        if not link_match:
            continue

        href = link_match.group(1)
        url = f"{BASE_URL}{href}" if href.startswith('/') else href

        if url not in job_data:
            continue

        job_info = job_data[url]

        # Extract department
        dept_match = re.search(r'job-department[^>]*>\s*([^<]+)', item)
        department = dept_match.group(1).strip() if dept_match else ""

        # Extract facility
        facility_match = re.search(r'job-detail-facility[^>]*>\s*([^<]+)', item)
        facility = facility_match.group(1).strip() if facility_match else ""

        # Extract location
        loc_match = re.search(r'job-detail-location[^>]*>\s*([^<]+)', item)
        location = loc_match.group(1).strip() if loc_match else ""

        # Build location string
        location_parts = [p for p in [location, facility] if p]
        location_str = " - ".join(location_parts) if location_parts else "Sacramento, CA"

        jobs.append({
            "title": job_info["title"],
            "link": url,
            "location": location_str,
            "date_posted": "N/A",  # Will be filled from job detail page
            "source": SITE_NAME,
            "department": department,
        })

    return jobs


def _extract_total_results(html):
    """Extract total results count from the search results HTML."""
    match = re.search(r'data-total-results="(\d+)"', html)
    if match:
        return int(match.group(1))

    # Fallback: look for text like "168 Search Results"
    match = re.search(r'(\d+)\s+Search Results', html)
    if match:
        return int(match.group(1))

    return 0


async def scrape_commonspirit_jobs(max_pages=20, location=None, headless=False):
    """
    Scrapes CommonSpirit Health jobs via direct HTTP requests.

    Args:
        max_pages: Maximum number of pages to scrape
        location: Zip code and location string (e.g., "95826, Sacramento, CA"). Uses default if None.
        headless: Unused (kept for interface compatibility)

    Returns:
        List of job dictionaries
    """
    loc = location or DEFAULT_LOCATION
    all_jobs = {}  # Dedup by URL

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": _build_search_url(location=loc),
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        print(f"\n[CommonSpirit] Searching jobs in {loc}...")

        # First, load the search page to establish session
        search_url = _build_search_url(location=loc)
        try:
            async with session.get(search_url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    print(f"[CommonSpirit] Failed to load search page: HTTP {resp.status}")
                    return []

                html = await resp.text()
                total_results = _extract_total_results(html)

                if total_results == 0:
                    print("[CommonSpirit] No jobs found")
                    return []

                total_pages = (total_results + RECORDS_PER_PAGE - 1) // RECORDS_PER_PAGE
                print(f"[CommonSpirit] Found {total_results} total jobs ({total_pages} pages)")

                # Parse first page jobs from initial HTML
                first_page_jobs = _parse_jobs_from_html(html)
                for job in first_page_jobs:
                    all_jobs[job['link']] = job
                print(f"[CommonSpirit] Page 1/{total_pages}: +{len(first_page_jobs)} jobs")

        except Exception as e:
            print(f"[CommonSpirit] Error loading search page: {e}")
            return []

        await asyncio.sleep(PAGE_DELAY)

        # Paginate through remaining pages
        pages_to_scrape = min(total_pages, max_pages)

        for page in range(2, pages_to_scrape + 1):
            api_url = _build_results_api_url(page, location=loc, total_results=total_results)

            try:
                async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        print(f"[CommonSpirit] HTTP {resp.status} on page {page}")
                        break

                    data = await resp.json()
                    results_html = data.get("results", "")

                    if not results_html:
                        print(f"[CommonSpirit] No results in page {page} response")
                        break

                    page_jobs = _parse_jobs_from_html(results_html)

                    if not page_jobs:
                        print(f"[CommonSpirit] No more jobs on page {page}")
                        break

                    before_count = len(all_jobs)
                    for job in page_jobs:
                        all_jobs[job['link']] = job

                    new_count = len(all_jobs) - before_count
                    print(f"[CommonSpirit] Page {page}/{total_pages}: +{new_count} jobs (total unique: {len(all_jobs)})")

            except Exception as e:
                print(f"[CommonSpirit] Error on page {page}: {e}")
                break

            await asyncio.sleep(PAGE_DELAY)

    print(f"\n[CommonSpirit] Total unique jobs scraped: {len(all_jobs)}")
    return list(all_jobs.values())


def _extract_json_ld(html):
    """Extract JSON-LD structured data from job detail page."""
    pattern = r'<script type="application/ld\+json">(.*?)</script>'
    match = re.search(pattern, html, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


def _clean_html(html_text):
    """Strip HTML tags and clean up text."""
    if not html_text:
        return ""
    # Convert <br> to newlines
    text = re.sub(r'<br\s*/?>', '\n', html_text)
    # Remove all other HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Clean up entities
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
    text = text.replace('&rsquo;', "'").replace('&ndash;', '-')
    text = text.replace('&mdash;', '-').replace('&quot;', '"')
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


async def fetch_commonspirit_descriptions_batch(jobs, batch_size=5, headless=False):
    """
    Fetch full descriptions for CommonSpirit Health jobs.
    Uses JSON-LD structured data embedded in job detail pages.

    Args:
        jobs: List of job dictionaries with 'link' key
        batch_size: Unused (kept for compatibility)
        headless: Unused (kept for compatibility)

    Returns:
        Dict mapping job URL to description text
    """
    if not jobs:
        return {}

    results = {}

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        total = len(jobs)

        for i, job in enumerate(jobs, 1):
            url = job["link"]
            title = job["title"]
            print(f"  [{i}/{total}] Fetching CommonSpirit: {title[:50]}...")

            description = ""
            date_posted = "N/A"

            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30),
                                       allow_redirects=True) as resp:
                    if resp.status != 200:
                        print(f"    HTTP {resp.status}")
                        results[url] = ""
                        continue

                    html = await resp.text()

                # Extract JSON-LD structured data
                json_ld = _extract_json_ld(html)

                if json_ld:
                    # Get description (contains HTML)
                    raw_desc = json_ld.get("description", "")
                    description = _clean_html(raw_desc)

                    # Get qualifications
                    qualifications = json_ld.get("qualifications", "")
                    if qualifications:
                        qual_text = _clean_html(qualifications)
                        if qual_text and qual_text not in description:
                            description = f"{description}\n\nQualifications:\n{qual_text}"

                    # Get date posted
                    date_posted = json_ld.get("datePosted", "N/A")

                    # Get employment type
                    emp_type = json_ld.get("employmentType", "")
                    if emp_type:
                        description = f"{description}\n\nEmployment Type: {emp_type}"

                    # Get work hours
                    hours = json_ld.get("workHours", "")
                    if hours:
                        description = f"{description}\nScheduled Hours: {hours}"

                    # Update job's date_posted
                    job["date_posted"] = date_posted

                # Fallback: try to extract from HTML if JSON-LD failed
                if not description:
                    desc_match = re.search(r'class="[^"]*job-description[^"]*"[^>]*>(.*?)</div>',
                                          html, re.DOTALL | re.IGNORECASE)
                    if desc_match:
                        description = _clean_html(desc_match.group(1))

            except Exception as e:
                print(f"    Error: {e}")

            results[url] = description.strip() if description else ""

            # Polite delay
            if i < total:
                await asyncio.sleep(DESC_DELAY)

    return results


if __name__ == "__main__":
    async def test():
        print("Testing CommonSpirit Health scraper...")

        # Test scraping (limit to 3 pages for quick test)
        jobs = await scrape_commonspirit_jobs(max_pages=3)

        print(f"\nFound {len(jobs)} jobs:")
        for j in jobs[:8]:
            print(f"- {j['title']}")
            print(f"  Location: {j['location']}")
            print(f"  Department: {j.get('department', 'N/A')}")
            print(f"  Link: {j['link']}")
            print()

        # Test description fetching for first job
        if jobs:
            print("\nTesting description fetch for first job...")
            test_jobs = jobs[:1]
            descriptions = await fetch_commonspirit_descriptions_batch(test_jobs)

            for url, desc in descriptions.items():
                print(f"\nURL: {url}")
                print(f"Description preview ({len(desc)} chars):")
                print(desc[:500] + "..." if len(desc) > 500 else desc)

    asyncio.run(test())
