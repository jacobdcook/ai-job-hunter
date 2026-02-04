"""
Intel Corporation scraper using Workday API.
Scrapes IT, engineering, and technical roles from Intel's careers site.
Pure HTTP implementation - no browser automation needed.
"""

import asyncio
import aiohttp
import time
from typing import List, Dict
import random
from bs4 import BeautifulSoup

SITE_NAME = "Intel"

# API endpoints
BASE_URL = "https://intel.wd1.myworkdayjobs.com"
JOBS_API = f"{BASE_URL}/wday/cxs/intel/External/jobs"
JOB_DETAIL_API = f"{BASE_URL}/wday/cxs/intel/External/job"

# Location filters (Sacramento area: Folsom + nearby locations)
# These IDs come from Intel's Workday site filters
SACRAMENTO_LOCATIONS = [
    "1e4a4eb3adf101cc4e292078bf8199d0",  # Folsom, CA
    "1e4a4eb3adf1019ec42cde77bf8158d0",  # Additional Sacramento area location 1
    "1e4a4eb3adf1018c4bf78f77bf8112d0",  # Additional Sacramento area location 2
]


async def scrape_intel_jobs(
    use_location_filter: bool = True,
    max_jobs: int = 200,
) -> List[Dict]:
    """
    Scrape Intel jobs from Workday careers site.

    Args:
        use_location_filter: If True, filter to Sacramento area (Folsom + nearby).
                            If False, get all Intel jobs nationwide.
        max_jobs: Maximum number of jobs to scrape (default 200)

    Returns:
        List of job dictionaries with title, link, location, date_posted
    """
    jobs = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        offset = 0
        limit = 20  # Workday default page size
        first_total = None  # Track the first total we see (Workday API can be inconsistent)

        print(f"\n🔍 Scraping Intel jobs (Sacramento area filter: {use_location_filter})...")

        while offset < max_jobs:
            try:
                # Build API request payload
                payload = {
                    "limit": limit,
                    "offset": offset,
                    "searchText": ""
                }

                # Add location filter if requested
                if use_location_filter:
                    payload["appliedFacets"] = {
                        "locations": SACRAMENTO_LOCATIONS
                    }

                print(f"  Fetching jobs {offset+1}-{offset+limit}...", end=" ", flush=True)

                async with session.post(JOBS_API, json=payload, timeout=15) as resp:
                    if resp.status != 200:
                        print(f"Error {resp.status}")
                        break

                    data = await resp.json()

                    total_jobs = data.get("total", 0)
                    job_postings = data.get("jobPostings", [])

                    # Track the first non-zero total (Workday API sometimes returns 0 on later pages)
                    if first_total is None and total_jobs > 0:
                        first_total = total_jobs
                        print(f"[DEBUG] Set first_total={first_total} from API total={total_jobs}")
                    else:
                        print(f"[DEBUG] Page {offset//limit + 1}: API total={total_jobs}, first_total={first_total}, jobs_returned={len(job_postings)}")

                    if not job_postings:
                        print("No more jobs found")
                        break

                    # Extract job info
                    for job_posting in job_postings:
                        title = job_posting.get("title", "")
                        external_path = job_posting.get("externalPath", "")
                        location = job_posting.get("locationsText", "Unknown")
                        posted_on = job_posting.get("postedOn", "")

                        # Build full job URL
                        if external_path:
                            # externalPath format: "/job/US-California-Folsom/Senior-GPU-Validation-Engineer_JR0279452"
                            # We need just the last part: "Senior-GPU-Validation-Engineer_JR0279452"
                            job_slug = external_path.split("/")[-1]
                            job_url = f"{BASE_URL}/en-US/External/details/{job_slug}"
                        else:
                            continue  # Skip if no path

                        job = {
                            "title": title,
                            "link": job_url,
                            "location": location,
                            "date_posted": posted_on,
                            "source": SITE_NAME,
                            "_api_path": job_slug,  # Store for description fetching
                        }

                        jobs.append(job)

                    # Show progress with the authoritative total (first non-zero total we saw)
                    display_total = first_total if first_total else total_jobs
                    print(f"Got {len(job_postings)} jobs (total available: {display_total})")

                    # Check if we've retrieved all jobs (use first_total if available)
                    jobs_retrieved = offset + len(job_postings)
                    print(f"[DEBUG] Check stop: jobs_retrieved={jobs_retrieved}, first_total={first_total}, should_stop={first_total and jobs_retrieved >= first_total if first_total else False}")
                    if first_total and jobs_retrieved >= first_total:
                        print(f"  Reached end of results ({first_total} total)")
                        break

                    offset += limit

                    # Rate limiting
                    await asyncio.sleep(random.uniform(1, 2))

            except asyncio.TimeoutError:
                print("Timeout - skipping page")
                await asyncio.sleep(3)
                continue
            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(2)
                continue

    print(f"\n✅ Scraped {len(jobs)} total jobs from Intel")
    return jobs


async def fetch_intel_descriptions_batch(
    jobs: List[Dict],
    batch_size: int = 3,
) -> List[Dict]:
    """
    Fetch full job descriptions from Intel job detail pages.

    Args:
        jobs: List of jobs with '_api_path' field
        batch_size: Number of concurrent requests

    Returns:
        Jobs with added 'description' field
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }

    print(f"\n📄 Fetching Intel job descriptions ({len(jobs)} jobs)...")

    async with aiohttp.ClientSession(headers=headers) as session:
        for i, job in enumerate(jobs):
            try:
                api_path = job.get("_api_path", "")
                if not api_path:
                    job["description"] = "No API path available"
                    continue

                print(f"  [{i+1}/{len(jobs)}] {job['title'][:50]}...", end=" ", flush=True)

                # Build API URL (remove /en-US/External/details/ prefix for API)
                detail_url = f"{JOB_DETAIL_API}/{api_path}"

                async with session.get(detail_url, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()

                        job_info = data.get("jobPostingInfo", {})
                        description_html = job_info.get("jobDescription", "")

                        if description_html:
                            # Parse HTML and extract text
                            soup = BeautifulSoup(description_html, "html.parser")
                            description_text = soup.get_text(separator=" ", strip=True)

                            # Limit description length
                            job["description"] = description_text[:2000]
                            print("✓")
                        else:
                            # API didn't return description - try web page as fallback
                            web_url = job.get("link", "")
                            if web_url:
                                try:
                                    async with session.get(web_url, timeout=15) as web_resp:
                                        if web_resp.status == 200:
                                            web_html = await web_resp.text()
                                            web_soup = BeautifulSoup(web_html, "html.parser")

                                            # Try to find job description in page
                                            desc_div = web_soup.find("div", {"data-automation-id": "jobPostingDescription"})
                                            if not desc_div:
                                                desc_div = web_soup.find("div", class_=lambda x: x and "description" in x.lower())

                                            if desc_div:
                                                description_text = desc_div.get_text(separator=" ", strip=True)
                                                job["description"] = description_text[:2000]
                                                print("✓ (web)")
                                            else:
                                                job["description"] = "No description available"
                                                print("⚠ No description")
                                        else:
                                            job["description"] = "No description available"
                                            print("⚠ No description")
                                except:
                                    job["description"] = "No description available"
                                    print("⚠ No description")
                            else:
                                job["description"] = "No description available"
                                print("⚠ No description")
                    else:
                        job["description"] = f"Error fetching (Status {resp.status})"
                        print(f"✗ {resp.status}")

                # Rate limiting
                await asyncio.sleep(random.uniform(1, 2))

            except asyncio.TimeoutError:
                job["description"] = "Timeout fetching description"
                print("✗ Timeout")
                await asyncio.sleep(3)
            except Exception as e:
                job["description"] = f"Error: {str(e)}"
                print(f"✗ {str(e)[:30]}")
                await asyncio.sleep(2)

        # Remove internal API path field before returning
        for job in jobs:
            job.pop("_api_path", None)

    return jobs


if __name__ == "__main__":
    # Test scraper
    async def test():
        # Scrape Sacramento area Intel jobs
        jobs = await scrape_intel_jobs(
            use_location_filter=True,
            max_jobs=100
        )

        if jobs:
            print(f"\n📊 Sample jobs (showing first 5):")
            for job in jobs[:5]:
                print(f"\n  Title: {job['title']}")
                print(f"  Location: {job['location']}")
                print(f"  Posted: {job['date_posted']}")
                print(f"  Link: {job['link']}")

            # Test fetching description for first job
            print(f"\n📄 Testing description fetch for first job...")
            jobs_with_desc = await fetch_intel_descriptions_batch([jobs[0]])
            if jobs_with_desc:
                print(f"\nDescription: {jobs_with_desc[0].get('description', 'N/A')[:300]}...")

    asyncio.run(test())
