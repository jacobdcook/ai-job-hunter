"""
Los Rios Community College District Job Scraper
Website: https://jobs.losrios.edu/
Platform: NEOGOV/SchoolJobs.com (same platform as GovernmentJobs.com)
Uses HTTP requests - NEOGOV sites typically have search URLs.
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict
import random

SITE_NAME = "Los Rios Community College District"
BASE_URL = "https://jobs.losrios.edu"
CAREERS_BASE = f"{BASE_URL}/careers/losriosccd"

# Delays
PAGE_DELAY = 2
SEARCH_DELAY = 3


async def scrape_losrios_jobs(search_queries=None, headless=False):
    """
    Scrapes Los Rios jobs from NEOGOV/SchoolJobs.com platform.
    
    Args:
        search_queries: List of keywords (e.g., ["IT", "Security", "Analyst"])
        headless: Unused (kept for interface compatibility)
    
    Returns:
        List of job dictionaries
    """
    all_jobs = {}  # Dedup by link
    
    if search_queries is None:
        search_queries = ["IT", "Security", "Analyst", "Support", "Technician"]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        for query_idx, query in enumerate(search_queries):
            print(f"\n[Los Rios] Searching for '{query}'...")
            
            # NEOGOV/SchoolJobs search URL pattern
            search_url = f"{CAREERS_BASE}/jobs?keywords={query}"
            
            try:
                async with session.get(search_url, timeout=15) as resp:
                    if resp.status != 200:
                        print(f"[Los Rios] Error {resp.status} for '{query}'")
                        continue
                    
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # Extract jobs (NEOGOV uses similar structure to GovernmentJobs)
                    jobs_on_page = _extract_jobs_from_page(soup, BASE_URL)
                    
                    for job in jobs_on_page:
                        all_jobs[job['link']] = job
                    
                    print(f"[Los Rios] Found {len(jobs_on_page)} jobs for '{query}' (total unique: {len(all_jobs)})")
                    
                    # Try pagination (check for "Next" link)
                    # For now, just get first page - can enhance later
                    
                    if query_idx < len(search_queries) - 1:
                        await asyncio.sleep(SEARCH_DELAY + random.uniform(0, 1))
            
            except Exception as e:
                print(f"[Los Rios] Error searching '{query}': {e}")
                continue
    
    result = list(all_jobs.values())
    print(f"\n[Los Rios] Total unique jobs scraped: {len(result)}")
    return result


def _extract_jobs_from_page(soup, base_url):
    """Extract job listings from NEOGOV/SchoolJobs.com page."""
    jobs = []
    
    # NEOGOV uses various structures - try common patterns
    job_items = soup.find_all("li", class_="job-item") or \
                soup.find_all("div", class_="job-item") or \
                soup.find_all("tr", class_="job-item") or \
                soup.find_all("a", href=lambda x: x and "/job/" in x)
    
    for item in job_items:
        try:
            # Find link
            link_elem = item.find("a", href=True) if item.name != "a" else item
            if not link_elem:
                continue
            
            href = link_elem.get("href", "")
            if not href:
                continue
            
            # Make absolute URL
            if href.startswith("/"):
                full_link = base_url + href
            elif href.startswith("http"):
                full_link = href
            else:
                full_link = f"{base_url}/{href}"
            
            # Extract title
            title = link_elem.get_text(strip=True) or \
                   item.find(class_="job-title") or \
                   item.find("h3") or \
                   item.find("h4")
            
            if isinstance(title, str):
                title_text = title.strip()
            else:
                title_text = title.get_text(strip=True) if title else "Job Posting"
            
            # Extract location
            location_elem = item.find(class_="job-location") or \
                           item.find(class_="location") or \
                           item.find("span", string=lambda x: x and ("CA" in x or "Sacramento" in x))
            location = location_elem.get_text(strip=True) if location_elem else "Sacramento, CA"
            
            jobs.append({
                "title": title_text,
                "link": full_link,
                "location": location,
                "date_posted": "N/A",
                "source": SITE_NAME,
            })
        
        except Exception:
            continue
    
    return jobs


async def fetch_losrios_descriptions_batch(jobs, headless=False):
    """
    Fetch full job descriptions from Los Rios job detail pages.
    
    Args:
        jobs: List of job dicts with 'link' field
        headless: Unused (kept for interface compatibility)
    
    Returns:
        Dict mapping job link -> description text
    """
    descriptions = {}
    
    if not jobs:
        return descriptions
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        for i, job in enumerate(jobs):
            try:
                print(f"  [{i+1}/{len(jobs)}] Fetching Los Rios: {job.get('title', 'Unknown')[:50]}...", end=" ", flush=True)
                
                async with session.get(job['link'], timeout=15) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, "html.parser")
                        
                        # Extract description (NEOGOV structure)
                        desc_elem = soup.find("div", class_="job-description") or \
                                   soup.find("div", id="jobDescription") or \
                                   soup.find("div", class_="description")
                        
                        if desc_elem:
                            desc = desc_elem.get_text(separator=" ", strip=True)
                            descriptions[job['link']] = desc[:5000]  # Limit length
                            print("✓")
                        else:
                            descriptions[job['link']] = "Description not available"
                            print("⚠")
                    else:
                        descriptions[job['link']] = f"Error fetching (Status {resp.status})"
                        print(f"✗ {resp.status}")
                
                await asyncio.sleep(random.uniform(2, 4))
            
            except Exception as e:
                descriptions[job['link']] = f"Error: {str(e)[:100]}"
                print(f"✗ {str(e)[:50]}")
                await asyncio.sleep(2)
    
    return descriptions


if __name__ == "__main__":
    async def test():
        jobs = await scrape_losrios_jobs(["IT", "Security"], headless=False)
        print(f"\nFound {len(jobs)} jobs")
        for job in jobs[:3]:
            print(f"  - {job['title']} | {job['location']}")
    
    asyncio.run(test())
