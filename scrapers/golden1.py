"""
Golden 1 Credit Union Job Scraper
Uses Dayforce HCM platform - browser-based scraping with pagination
Site has Cloudflare protection, so we use full browser automation
"""

import asyncio
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from playwright.async_api import async_playwright

# Golden 1 Dayforce configuration
BASE_URL = "https://jobs.dayforcehcm.com"
JOBS_PORTAL_URL = f"{BASE_URL}/en-US/golden1/CANDIDATEPORTAL"

SITE_NAME = "Golden 1 Credit Union"


def clean_html(html_text: str) -> str:
    """Strip HTML tags and clean up text."""
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "html.parser")
    text = soup.get_text(separator="\n", strip=True)
    # Clean up excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


async def scrape_golden1_jobs(
    search_queries: List[str] = None,
    max_pages: int = 15,
    headless: bool = False
) -> List[Dict]:
    """
    Scrape all jobs from Golden 1 Credit Union careers page using browser.
    
    The site uses Dayforce HCM with Cloudflare protection.
    We paginate through pages using ?page=1, ?page=2, etc.
    When we go past the last page, it redirects to page 1.
    
    Args:
        search_queries: Not used for Golden 1 (we scrape all jobs)
        max_pages: Maximum pages to fetch (default 15, usually ~7 pages)
        headless: Run browser in headless mode
        
    Returns:
        List of job dictionaries
    """
    all_jobs = {}
    first_page_jobs = set()  # Track first page jobs to detect redirect
    
    print(f"[Golden 1] Scraping jobs via browser (max {max_pages} pages)...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0"
        )
        page = await context.new_page()
        
        try:
            for page_num in range(1, max_pages + 1):
                url = f"{JOBS_PORTAL_URL}?page={page_num}"
                print(f"  Page {page_num}: Loading...", end=" ", flush=True)
                
                # Navigate - use longer timeout, don't wait for networkidle
                try:
                    await page.goto(url, timeout=90000, wait_until="domcontentloaded")
                except Exception as e:
                    print(f"Navigation error: {e}")
                    await asyncio.sleep(5)
                    continue
                
                # Wait for page to render - this site is slow
                print("waiting for content...", end=" ", flush=True)
                await asyncio.sleep(12)
                
                # Try to wait for job content indicators
                try:
                    await page.wait_for_selector('text=Req#', timeout=20000)
                    print("found jobs...", end=" ", flush=True)
                except:
                    print("no Req# found, trying longer wait...", end=" ", flush=True)
                    await asyncio.sleep(10)
                
                # Extract jobs by finding actual links on the page
                # The "Read More" or job title links contain the real jobPostingId
                jobs_data = await page.evaluate("""
                    () => {
                        const jobs = [];
                        const seen = new Set();
                        
                        // Find all links that go to job detail pages
                        // Pattern: /en-US/golden1/CANDIDATEPORTAL/jobs/{id}
                        const allLinks = document.querySelectorAll('a[href*="/jobs/"]');
                        
                        for (const link of allLinks) {
                            const href = link.href || '';
                            
                            // Extract jobPostingId from URL
                            const match = href.match(/\\/jobs\\/(\\d+)/);
                            if (!match) continue;
                            
                            const jobId = match[1];
                            if (seen.has(jobId)) continue;
                            seen.add(jobId);
                            
                            // Get job info from surrounding content
                            // The link might be on "Read More" or the job title
                            let title = '';
                            let location = 'Sacramento, CA';
                            let datePosted = 'N/A';
                            let reqNum = '';
                            
                            // Look at parent container for job info
                            let container = link.closest('div');
                            // Go up a few levels to get the full job card
                            for (let i = 0; i < 5 && container; i++) {
                                const text = container.innerText || '';
                                if (text.includes('Posted') && text.includes('Req#')) {
                                    break;
                                }
                                container = container.parentElement;
                            }
                            
                            if (container) {
                                const text = container.innerText || '';
                                const lines = text.split('\\n').map(l => l.trim()).filter(l => l);
                                
                                for (const line of lines) {
                                    // Skip navigation/utility text
                                    if (line.length < 10) continue;
                                    if (['Search Jobs', 'Sign In', 'Read More', 'Skip to'].some(x => line.includes(x))) continue;
                                    
                                    // First substantial line with job keywords is likely the title
                                    if (!title && line.length > 15 && line.length < 150) {
                                        if ([' - ', 'Branch', 'Specialist', 'Manager', 'Analyst', 'Developer', 
                                             'Director', 'IT ', 'HR ', 'Supervisor', 'Coordinator', 'Partner',
                                             'Assistant', 'Writer', 'Investigator', 'Executive'].some(x => line.includes(x))) {
                                            if (!line.includes('USA') && !line.includes('Posted')) {
                                                title = line;
                                            }
                                        }
                                    }
                                    
                                    // Location line contains USA or Virtual
                                    if (line.includes('USA') || (line.includes('Virtual') && line.length < 100)) {
                                        location = line.replace(/•/g, ',').trim();
                                    }
                                    
                                    // Date line
                                    const dateMatch = line.match(/Posted\\s+(\\w+,\\s+\\w+\\s+\\d+,\\s+\\d+)/);
                                    if (dateMatch) {
                                        datePosted = dateMatch[1];
                                    }
                                    
                                    // Req number
                                    const reqMatch = line.match(/Req#\\s*(\\d+)/);
                                    if (reqMatch) {
                                        reqNum = reqMatch[1];
                                    }
                                }
                            }
                            
                            // Only add if we got a title
                            if (title) {
                                jobs.push({
                                    title: title,
                                    jobId: jobId,
                                    reqNum: reqNum,
                                    url: href,
                                    location: location,
                                    datePosted: datePosted
                                });
                            }
                        }
                        
                        return jobs;
                    }
                """)
                
                if not jobs_data or len(jobs_data) == 0:
                    if page_num == 1:
                        # Debug: get page text for troubleshooting
                        page_text = await page.evaluate("() => document.body.innerText")
                        print(f"0 jobs found. Content length: {len(page_text) if page_text else 0}")
                        if page_text:
                            print(f"    First 300 chars: {page_text[:300]}")
                        await asyncio.sleep(5)
                        continue
                    else:
                        print("No more jobs found. Done!")
                        break
                
                # Check for redirect to page 1 (seeing same jobs)
                current_job_ids = {j['jobId'] for j in jobs_data}
                if page_num == 1:
                    first_page_jobs = current_job_ids
                elif page_num > 1 and current_job_ids == first_page_jobs:
                    print(f"Same jobs as page 1 - redirected. Done!")
                    break
                
                new_count = 0
                for job in jobs_data:
                    job_url = job.get('url', '')
                    job_id = job.get('jobId', '')
                    
                    if not job_url:
                        continue
                    
                    if job_url not in all_jobs:
                        all_jobs[job_url] = {
                            "title": job.get('title', 'Job Posting'),
                            "link": job_url,
                            "location": job.get('location', 'Sacramento, CA'),
                            "date_posted": job.get('datePosted', 'N/A'),
                            "source": SITE_NAME,
                            "_job_id": job_id,
                            "_req_num": job.get('reqNum', ''),
                        }
                        new_count += 1
                
                print(f"Found {len(jobs_data)} jobs (+{new_count} new, total: {len(all_jobs)})")
                
                # If no new jobs, we've seen all
                if new_count == 0 and page_num > 1:
                    print("  No new jobs. Done!")
                    break
                
                # Wait between pages
                await asyncio.sleep(5)
                    
        except Exception as e:
            print(f"[Golden 1] Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()
    
    jobs_list = list(all_jobs.values())
    print(f"\n[Golden 1] Total unique jobs scraped: {len(jobs_list)}")
    
    return jobs_list


async def fetch_golden1_descriptions_batch(
    jobs: List[Dict],
    headless: bool = False
) -> Dict[str, str]:
    """
    Fetch job descriptions for Golden 1 jobs by visiting each job page.
    
    Args:
        jobs: List of job dictionaries (must have 'link')
        headless: Run browser in headless mode
        
    Returns:
        Dict mapping job URLs to descriptions
    """
    descriptions = {}
    
    if not jobs:
        return descriptions
    
    print(f"[Golden 1] Fetching descriptions for {len(jobs)} jobs...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0"
        )
        page = await context.new_page()
        
        for i, job in enumerate(jobs):
            job_url = job.get("link", "")
            job_title = job.get("title", "")[:50]
            
            if not job_url or "search=" in job_url:
                # Skip jobs without proper URLs
                continue
            
            try:
                print(f"  [{i+1}/{len(jobs)}] {job_title}...", end=" ", flush=True)
                
                # Navigate to job detail page
                await page.goto(job_url, timeout=45000, wait_until="domcontentloaded")
                await asyncio.sleep(5)
                
                # Extract description from page
                description = await page.evaluate("""
                    () => {
                        // Look for job description content
                        const body = document.body.innerText || '';
                        
                        // Find the main content area
                        // Usually after "GENERAL DESCRIPTION:" or similar headers
                        const descMatch = body.match(/GENERAL DESCRIPTION[:\\s]*([\\s\\S]*?)(?:TASKS|PHYSICAL|QUALIFICATIONS|ORGANIZATIONAL|$)/i);
                        if (descMatch) {
                            return descMatch[1].trim().substring(0, 5000);
                        }
                        
                        // Alternative: get all text after job title until footer
                        const titleMatch = body.match(/JOB TITLE[:\\s]*([\\s\\S]*?)(?:©|Privacy|Accessibility|$)/i);
                        if (titleMatch) {
                            return titleMatch[1].trim().substring(0, 8000);
                        }
                        
                        // Fallback: get main content
                        return body.substring(0, 8000);
                    }
                """)
                
                if description and len(description) > 100:
                    descriptions[job_url] = clean_html(description)
                    print("✓")
                else:
                    print("(short/no description)")
                
                # Rate limit
                await asyncio.sleep(3)
                
            except Exception as e:
                print(f"Error: {e}")
                continue
        
        await browser.close()
    
    return descriptions


# For testing
if __name__ == "__main__":
    async def main():
        print("Testing Golden 1 Credit Union scraper...")
        jobs = await scrape_golden1_jobs(headless=False)
        
        print(f"\nFound {len(jobs)} jobs")
        for job in jobs[:5]:
            print(f"  - {job['title']}")
            print(f"    URL: {job['link']}")
            print(f"    Location: {job['location']}")
            desc_preview = job.get('description', '')[:100]
            print(f"    Description: {desc_preview}...")
            print()
    
    asyncio.run(main())
