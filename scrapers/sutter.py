"""
Sutter Health Job Scraper
Website: https://jobs.sutterhealth.org/
Platform: Phenom People (server-side rendered)

All job data is embedded in the HTML as phApp.ddo JSON -- no browser needed.
Search results: phApp.ddo.eagerLoadRefineSearch.data.jobs
Job detail: phApp.ddo.jobDetail.data.job.description
Pagination: ?keywords={kw}&from={offset}&s=1 (10 per page, fixed)
"""

import asyncio
import json
import math
import re
import aiohttp

SITE_NAME = "Sutter Health"
BASE_URL = "https://jobs.sutterhealth.org"
SEARCH_URL = f"{BASE_URL}/us/en/search-results"

# 10 results per page (fixed by Phenom platform)
PAGE_SIZE = 10

# Delays (be polite)
PAGE_DELAY = 2
SEARCH_DELAY = 3


def _extract_ddo(html):
    """
    Extract the phApp.ddo JSON object from the server-rendered HTML.
    Uses brace-matching since the JSON can contain nested braces in strings.
    """
    marker = "phApp.ddo = "
    start = html.find(marker)
    if start == -1:
        return None

    start += len(marker)

    # Find the matching closing brace
    depth = 0
    in_string = False
    escape_next = False
    i = start

    while i < len(html):
        ch = html[i]

        if escape_next:
            escape_next = False
            i += 1
            continue

        if ch == '\\' and in_string:
            escape_next = True
            i += 1
            continue

        if ch == '"' and not escape_next:
            in_string = not in_string
            i += 1
            continue

        if not in_string:
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    json_str = html[start:i + 1]
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        return None

        i += 1

    return None


def _build_search_url(keywords, offset=0):
    """Build search URL with pagination."""
    url = f"{SEARCH_URL}?keywords={keywords}"
    if offset > 0:
        url += f"&from={offset}&s=1"
    return url


async def scrape_sutter_jobs(search_queries=None, headless=False):
    """
    Scrapes Sutter Health jobs via direct HTTP requests.
    Job data is server-rendered in phApp.ddo JSON -- no browser needed.

    Args:
        search_queries: List of keywords (e.g., ["IT", "Security", "Analyst"])
        headless: Unused (kept for interface compatibility)

    Returns:
        List of job dictionaries
    """
    all_jobs = {}  # Dedup by reqId

    if search_queries is None:
        search_queries = ["IT", "Security", "Analyst", "Help Desk", "Systems", "Network", "Cyber", "Infrastructure", "Support", "Technician"]

    async with aiohttp.ClientSession(headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }) as session:

        for query_idx, query in enumerate(search_queries):
            print(f"\n[Sutter] Searching for '{query}'...")

            offset = 0
            total_hits = None

            while True:
                url = _build_search_url(query, offset)

                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        if resp.status != 200:
                            print(f"[Sutter] HTTP {resp.status} for '{query}' offset {offset}")
                            break
                        html = await resp.text()
                except Exception as e:
                    print(f"[Sutter] Request failed for '{query}' offset {offset}: {e}")
                    break

                ddo = _extract_ddo(html)
                if not ddo:
                    print(f"[Sutter] Could not extract phApp.ddo for '{query}' offset {offset}")
                    break

                # Get search results from eagerLoadRefineSearch
                search_data = ddo.get("eagerLoadRefineSearch", {})
                if search_data.get("status") != 200:
                    print(f"[Sutter] Search returned non-200 status for '{query}'")
                    break

                jobs_data = search_data.get("data", {}).get("jobs", [])

                if total_hits is None:
                    total_hits = search_data.get("totalHits", 0)
                    total_pages = math.ceil(total_hits / PAGE_SIZE) if total_hits > 0 else 0
                    print(f"[Sutter] Found {total_hits} total jobs for '{query}' ({total_pages} pages)")

                if not jobs_data:
                    break

                current_page = (offset // PAGE_SIZE) + 1
                before_count = len(all_jobs)

                for job in jobs_data:
                    req_id = job.get("reqId", "")
                    if not req_id:
                        continue

                    # Build job URL
                    title = job.get("title", "Unknown")
                    title_slug = re.sub(r'[^a-zA-Z0-9\s-]', '', title)
                    title_slug = re.sub(r'\s+', '-', title_slug.strip())
                    job_url = f"{BASE_URL}/us/en/job/{req_id}/{title_slug}"

                    # Location
                    city = job.get("city", "")
                    state = job.get("state", "")
                    location = job.get("cityStateCountry", "") or f"{city}, {state}".strip(", ")
                    if not location:
                        location = "Sutter Health"

                    # Build description from search listing metadata
                    desc_parts = []
                    teaser = job.get("descriptionTeaser", "")
                    if teaser:
                        desc_parts.append(teaser)
                    category = job.get("category", "")
                    if category:
                        desc_parts.append(f"Category: {category}")
                    department = job.get("department", "")
                    if department:
                        desc_parts.append(f"Department: {department}")
                    job_type = job.get("type", "")
                    if job_type:
                        desc_parts.append(f"Type: {job_type}")
                    schedule = job.get("jobSchedule", "")
                    if schedule:
                        desc_parts.append(f"Schedule: {schedule}")
                    shift = job.get("Shift", "")
                    if shift:
                        desc_parts.append(f"Shift: {shift}")
                    entity = job.get("Entity", "")
                    if entity:
                        desc_parts.append(f"Entity: {entity}")
                    remote = job.get("remoteType", "")
                    if remote:
                        desc_parts.append(f"Remote: {remote}")
                    hours = job.get("scheduledWeeklyHours", "")
                    if hours:
                        desc_parts.append(f"Weekly Hours: {hours}")
                    description = "\n".join(desc_parts)

                    all_jobs[req_id] = {
                        "title": title,
                        "link": job_url,
                        "location": location,
                        "date_posted": job.get("postedDate", "N/A"),
                        "source": SITE_NAME,
                        "description": description,
                    }

                new_count = len(all_jobs) - before_count
                print(f"[Sutter] Page {current_page}/{total_pages}: +{new_count} new jobs (total unique: {len(all_jobs)})")

                offset += PAGE_SIZE
                if offset >= total_hits:
                    break

                await asyncio.sleep(PAGE_DELAY)

            if query_idx < len(search_queries) - 1:
                await asyncio.sleep(SEARCH_DELAY)

    print(f"\n[Sutter] Total unique jobs scraped: {len(all_jobs)}")
    return list(all_jobs.values())


async def fetch_sutter_descriptions_batch(jobs, headless=False):
    """
    Fetch full descriptions for Sutter Health jobs via HTTP.
    Job detail pages embed full description in phApp.ddo.jobDetail.data.job.description.
    No browser needed.
    """
    if not jobs:
        return {}

    results = {}

    async with aiohttp.ClientSession(headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }) as session:

        total = len(jobs)
        for i, job in enumerate(jobs, 1):
            url = job["link"]
            title = job["title"]
            print(f"  [{i}/{total}] Fetching Sutter: {title[:50]}...")

            description = ""
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30),
                                       allow_redirects=True) as resp:
                    if resp.status != 200:
                        print(f"    HTTP {resp.status}")
                        results[url] = ""
                        continue

                    html = await resp.text()

                ddo = _extract_ddo(html)
                if ddo:
                    job_detail = ddo.get("jobDetail", {}).get("data", {}).get("job", {})

                    # Full HTML description
                    raw_desc = job_detail.get("description", "")
                    if raw_desc:
                        # Strip HTML tags for plain text
                        description = re.sub(r'<br\s*/?>', '\n', raw_desc)
                        description = re.sub(r'<[^>]+>', ' ', description)
                        description = description.replace('&nbsp;', ' ').replace('&amp;', '&')
                        description = re.sub(r'\s+', ' ', description).strip()

                    # Supplement with structured data if available
                    parts = []
                    if description:
                        parts.append(description)

                    ai_summary = job_detail.get("ai_summary", "")
                    if ai_summary:
                        parts.append(f"\nAI Summary: {ai_summary}")

                    category = job_detail.get("category", "")
                    if category:
                        parts.append(f"Category: {category}")
                    department = job_detail.get("department", "")
                    if department:
                        parts.append(f"Department: {department}")
                    job_type = job_detail.get("type", "")
                    if job_type:
                        parts.append(f"Type: {job_type}")
                    schedule = job_detail.get("jobSchedule", "")
                    if schedule:
                        parts.append(f"Schedule: {schedule}")

                    description = "\n".join(parts) if parts else description

            except Exception as e:
                print(f"    Error: {e}")

            results[url] = description.strip() if description else ""

            # Polite delay
            if i < total:
                await asyncio.sleep(3)

    return results


if __name__ == "__main__":
    async def test():
        jobs = await scrape_sutter_jobs(["IT", "Security"], headless=False)
        print(f"\nFound {len(jobs)} jobs:")
        for j in jobs[:5]:
            print(f"- {j['title']} | {j['location']} | Posted: {j['date_posted']}")
            desc = j.get("description", "")
            if desc:
                print(f"  Preview: {desc[:120]}...")

    asyncio.run(test())
