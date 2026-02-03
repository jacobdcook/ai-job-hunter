"""
UC Davis Job Scraper
Uses the University of California public JSON API directly.
API: https://jobs.universityofcalifornia.edu/api/jobs
No browser needed for search -- Cloudflare is only on the Drupal front-end,
the API itself has open CORS (access-control-allow-origin: *).
"""

import asyncio
import aiohttp
from urllib.parse import urlencode
from playwright.async_api import async_playwright

SITE_NAME = "UC Davis"
API_URL = "https://jobs.universityofcalifornia.edu/api/jobs"

# UC Davis campus codes
CAMPUS_CODES = ["DV", "DVMC"]  # DV = UC Davis, DVMC = UC Davis Health

# Delay between API pages (be polite even though it's open)
PAGE_DELAY = 1
SEARCH_DELAY = 2


def _build_api_url(keywords=None, page=1, sortby="posting_date"):
    """Build the API URL with proper query parameters."""
    params = [("format", "json")]
    for campus in CAMPUS_CODES:
        params.append(("MCampus[]", campus))
    if keywords:
        params.append(("keywords", keywords))
    params.append(("sortby", sortby))
    if page > 1:
        params.append(("page", str(page)))
    return f"{API_URL}?{urlencode(params)}"


async def scrape_ucdavis_jobs(search_queries=None, headless=False):
    """
    Scrapes UC Davis jobs using the UC system public JSON API.
    No browser automation needed -- direct HTTP requests.

    Args:
        search_queries: List of keywords to search (e.g., ["IT", "Security", "Analyst"])
        headless: Unused (kept for interface compatibility with other scrapers)

    Returns:
        List of job dictionaries
    """
    all_jobs = {}  # Dedup by job URL

    if search_queries is None:
        search_queries = ["IT", "Security", "Analyst", "Associate"]

    async with aiohttp.ClientSession(headers={
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0"
    }) as session:

        for query_idx, query in enumerate(search_queries):
            print(f"\n[UC Davis] Searching for '{query}'...")

            page_num = 1
            total_pages = None

            while True:
                url = _build_api_url(keywords=query, page=page_num)

                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        if resp.status != 200:
                            print(f"[UC Davis] API returned status {resp.status} for '{query}' page {page_num}")
                            break
                        data = await resp.json(content_type=None)
                except Exception as e:
                    print(f"[UC Davis] API request failed for '{query}' page {page_num}: {e}")
                    break

                jobs_list = data.get("jobs", [])

                if total_pages is None:
                    total_pages = data.get("total_page", 1)
                    total_jobs = data.get("total_jobs", 0)
                    print(f"[UC Davis] Found {total_jobs} total jobs for '{query}' ({total_pages} pages)")

                if not jobs_list:
                    break

                before_count = len(all_jobs)
                for job in jobs_list:
                    job_url = job.get("url", "")
                    if not job_url:
                        continue

                    # Build location from work_location and location fields
                    work_loc = job.get("work_location", "")
                    campus_loc = job.get("location", "")
                    location = work_loc or campus_loc or "UC Davis"

                    # Build description from API metadata so it's saved to DB
                    # on first pass (avoids needing browser fetch later)
                    desc_parts = []
                    summary = job.get("position_summary", "")
                    if summary:
                        desc_parts.append(summary)
                    salary = job.get("salary_range", "")
                    if salary:
                        desc_parts.append(f"Salary Range: {salary}")
                    categories = job.get("categories_str", "")
                    if categories:
                        desc_parts.append(f"Category: {categories}")
                    ft_pt = job.get("ft_pt", "")
                    if ft_pt:
                        desc_parts.append(f"Type: {ft_pt}")
                    closing = job.get("closing_date", "")
                    if closing:
                        desc_parts.append(f"Closing Date: {closing}")
                    description = "\n".join(desc_parts)

                    all_jobs[job_url] = {
                        "title": job.get("job_title", "Unknown"),
                        "link": job_url,
                        "location": location,
                        "date_posted": job.get("posting_date", "N/A"),
                        "source": SITE_NAME,
                        "description": description,
                    }

                new_count = len(all_jobs) - before_count
                print(f"[UC Davis] Page {page_num}/{total_pages}: +{new_count} new jobs (total unique: {len(all_jobs)})")

                if page_num >= total_pages:
                    break
                page_num += 1
                await asyncio.sleep(PAGE_DELAY)

            if query_idx < len(search_queries) - 1:
                await asyncio.sleep(SEARCH_DELAY)

    print(f"\n[UC Davis] Total unique jobs scraped: {len(all_jobs)}")
    return list(all_jobs.values())


async def fetch_ucdavis_descriptions_batch(jobs, headless=False):
    """
    Fetch full descriptions for UC Davis jobs via browser.

    Normally descriptions are already saved from the API during scraping.
    This function is a fallback for any jobs that ended up with empty
    descriptions (e.g. API returned no position_summary). It fetches
    the full PeopleSoft/HRMS posting page via Playwright.
    """
    if not jobs:
        return {}

    results = {}

    print(f"[UC Davis] Fetching descriptions for {len(jobs)} jobs via browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0"
        )
        page = await context.new_page()

        total = len(jobs)
        for i, job in enumerate(jobs, 1):
            url = job["link"]
            title = job["title"]
            print(f"  [{i}/{total}] Fetching: {title[:50]}...")

            description = ""
            try:
                await page.goto(url, timeout=30000)
                await asyncio.sleep(3)

                # PeopleSoft job pages: try common selectors
                selectors = [
                    "#win0divHRS_CE_WRK2_DESCRLONG1",
                    ".ps_box-group",
                    "#ACE_HRS_CE_JO_EXT_VW",
                    "#win0divHRS_APPL_WRK_HRS_FULL_DESCR100",
                    "main",
                    "body"
                ]
                for selector in selectors:
                    try:
                        elem = await page.query_selector(selector)
                        if elem:
                            description = await elem.inner_text()
                            if description and len(description) > 100:
                                break
                    except Exception:
                        continue

            except Exception as e:
                print(f"    Error: {e}")

            results[url] = description.strip() if description else ""

            if i < total:
                await asyncio.sleep(10)

        await browser.close()

    return results


if __name__ == "__main__":
    async def test():
        jobs = await scrape_ucdavis_jobs(["IT", "Security"], headless=False)
        print(f"\nFound {len(jobs)} jobs:")
        for j in jobs[:5]:
            print(f"- {j['title']} | {j['location']} | Posted: {j['date_posted']}")
            desc = j.get('description', '')
            if desc:
                print(f"  Description preview: {desc[:120]}...")

    asyncio.run(test())
