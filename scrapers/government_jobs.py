"""
GovernmentJobs.com scraper for security analyst and SOC roles.
Supports keyword search, pagination, and extracts job details.
"""

import asyncio
import aiohttp
import time
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import random

# Default location: Sacramento, CA (95826)
DEFAULT_LOCATION = "95826"
DEFAULT_DISTANCE = 100

SITE_NAME = "GovernmentJobs.com"


async def scrape_government_jobs(
    keywords: List[str],
    location: str = DEFAULT_LOCATION,
    distance: int = DEFAULT_DISTANCE,
    max_pages: int = 20,
) -> List[Dict]:
    """
    Scrape government jobs from GovernmentJobs.com

    Args:
        keywords: List of search keywords (e.g., ["SOC Analyst", "Security Analyst"])
        location: Zip code or location (default: 95826)
        distance: Search radius in miles (default: 100)
        max_pages: Maximum pages to scrape per keyword

    Returns:
        List of job dictionaries with title, link, company, location, salary
    """
    jobs = []
    seen_urls = set()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        for keyword in keywords:
            print(f"\n🔍 Searching GovernmentJobs: '{keyword}' near {location}")

            page = 1
            consecutive_empty = 0
            while page <= max_pages:
                try:
                    # Build search URL
                    url = (
                        f"https://www.governmentjobs.com/jobs?"
                        f"page={page}&keyword={keyword}&location={location}&distance={distance}"
                        f"&isTransfer=False&isPromotional=False"
                    )

                    print(f"  Page {page}...", end=" ", flush=True)

                    async with session.get(url, timeout=10) as resp:
                        if resp.status != 200:
                            print(f"Error {resp.status}")
                            break

                        html = await resp.text()
                        soup = BeautifulSoup(html, "html.parser")

                        # Extract jobs from this page
                        page_jobs = _extract_jobs_from_page(soup)

                        if not page_jobs:
                            print("No jobs found on page")
                            break

                        # Filter duplicates by URL
                        new_jobs = 0
                        for job in page_jobs:
                            if job["link"] not in seen_urls:
                                jobs.append(job)
                                seen_urls.add(job["link"])
                                new_jobs += 1

                        print(f"Found {new_jobs} new jobs", end="")

                        # Stop if no new jobs found (all were duplicates)
                        if new_jobs == 0:
                            consecutive_empty += 1
                            print(f" (page {consecutive_empty} with no new results)")
                            if consecutive_empty >= 2:
                                print(f"  Stopping: 2 consecutive pages with no new jobs")
                                break
                        else:
                            consecutive_empty = 0
                            print()

                        # Rate limiting
                        await asyncio.sleep(random.uniform(2, 4))
                        page += 1

                except asyncio.TimeoutError:
                    print("Timeout - skipping page")
                    await asyncio.sleep(5)
                    continue
                except Exception as e:
                    print(f"Error: {e}")
                    await asyncio.sleep(2)
                    continue

    print(f"\n✅ Scraped {len(jobs)} total jobs from GovernmentJobs.com")
    return jobs


def _extract_jobs_from_page(soup: BeautifulSoup) -> List[Dict]:
    """Extract job listings from a GovernmentJobs page"""
    jobs = []

    # Look for job listing containers
    job_elements = soup.find_all("a", class_="jobTitleLink")

    if not job_elements:
        # Try alternative selectors
        job_elements = soup.find_all("a", {"class": lambda x: x and "job" in x.lower()})

    for element in job_elements:
        try:
            # Extract job title and link
            job_url = element.get("href", "")
            if not job_url:
                continue

            # Make absolute URL if relative
            if not job_url.startswith("http"):
                job_url = f"https://www.governmentjobs.com{job_url}"

            title = element.get_text(strip=True)
            if not title:
                continue

            # Extract job details from parent containers
            job_row = element.find_parent("div", class_="job")
            if not job_row:
                job_row = element.find_parent("tr")
            if not job_row:
                job_row = element.find_parent("li")

            if not job_row:
                continue

            # Company and location
            company_elem = job_row.find("span", class_="jobCompany")
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"

            location_elem = job_row.find("span", class_="jobLocation")
            location = location_elem.get_text(strip=True) if location_elem else "Unknown"

            # Salary
            salary_elem = job_row.find("span", class_="jobSalary")
            salary = salary_elem.get_text(strip=True) if salary_elem else "Not posted"

            job = {
                "title": title,
                "link": job_url,
                "company": company,
                "location": location,
                "salary": salary,
                "source": SITE_NAME,
            }

            jobs.append(job)

        except Exception as e:
            continue

    return jobs


async def fetch_job_details(
    jobs: List[Dict],
    batch_size: int = 3,
) -> List[Dict]:
    """
    Fetch full job details from individual job pages

    Args:
        jobs: List of jobs with 'link' field
        batch_size: Number of concurrent requests

    Returns:
        Jobs with added 'description' field
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        for i, job in enumerate(jobs):
            try:
                print(f"  Fetching description {i+1}/{len(jobs)}...", end=" ", flush=True)

                async with session.get(job["link"], timeout=10) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, "html.parser")

                        # Extract job description
                        description_elem = soup.find("div", class_="jobDescription")
                        if not description_elem:
                            description_elem = soup.find("div", id="jobDescription")
                        if not description_elem:
                            description_elem = soup.find("div", {"class": lambda x: x and "description" in x.lower()})

                        if description_elem:
                            description = description_elem.get_text(separator=" ", strip=True)
                            job["description"] = description[:2000]  # Limit to 2000 chars
                            print("✓")
                        else:
                            job["description"] = "Description not available"
                            print("⚠ No description found")
                    else:
                        job["description"] = f"Error fetching (Status {resp.status})"
                        print(f"✗ {resp.status}")

                # Rate limiting
                await asyncio.sleep(random.uniform(1, 3))

            except Exception as e:
                job["description"] = f"Error: {str(e)}"
                print(f"✗ {str(e)}")
                await asyncio.sleep(2)

    return jobs


if __name__ == "__main__":
    # Test with SOC analyst keywords tailored to Jacob's profile
    test_keywords = [
        "SOC Analyst",
        "Security Analyst",
        "Security Operations",
        "Threat Detection",
        "Incident Response",
    ]

    async def test():
        jobs = await scrape_government_jobs(
            keywords=test_keywords,
            location="95826",
            distance=100,
            max_pages=3,
        )

        print(f"\n📊 Results:")
        for job in jobs[:5]:
            print(f"\n  Title: {job['title']}")
            print(f"  Company: {job['company']}")
            print(f"  Location: {job['location']}")
            print(f"  Salary: {job['salary']}")
            print(f"  Link: {job['link']}")

    asyncio.run(test())
