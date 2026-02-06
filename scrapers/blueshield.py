"""
Blue Shield of California Job Scraper
Website: https://careers.blueshieldca.com/
Platform: Oracle Taleo (Oracle Cloud HCM)
Uses Playwright to establish session, then Oracle Taleo REST API for fast job fetching.
"""

import asyncio
import aiohttp
import random
from typing import List, Dict
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

SITE_NAME = "Blue Shield of California"
BASE_URL = "https://ecge.fa.us2.oraclecloud.com"
JOBS_PORTAL_URL = f"{BASE_URL}/hcmUI/CandidateExperience/en/sites/CX_1003"
SITE_NUMBER = "CX_1003"

# Oracle Taleo REST API endpoints
JOBS_LIST_API = f"{BASE_URL}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
JOB_DETAILS_API = f"{BASE_URL}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails"

# Delays (be polite)
PAGE_DELAY = 2
REQUEST_DELAY = 1


async def scrape_blueshield_jobs(search_queries=None, headless=False):
    """
    Scrapes Blue Shield of California jobs using infinite scroll.
    Scrolls down until all jobs are loaded, then extracts them from the DOM.
    
    Args:
        search_queries: List of keywords (unused - gets all jobs)
        headless: Run browser in headless mode
    
    Returns:
        List of job dictionaries
    """
    all_jobs = {}  # Dedup by link
    
    print(f"[Blue Shield] Loading jobs page and scrolling to load all jobs...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            slow_mo=100,  # Slower to be more reliable
            args=["--disable-dev-shm-usage", "--disable-gpu"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0"
        )
        page = await context.new_page()
        page.set_default_timeout(60000)
        
        try:
            # Navigate to jobs page
            await page.goto(f"{JOBS_PORTAL_URL}/jobs", timeout=60000)
            await page.wait_for_load_state("networkidle", timeout=30000)
            await asyncio.sleep(8)  # Wait longer for initial jobs to render
            
            print(f"[Blue Shield] Waiting for job list to appear...")
            
            # Wait for the job count text to appear (indicates page loaded)
            try:
                await page.wait_for_function(
                    "() => document.body.innerText.includes('Open Jobs') || document.body.innerText.includes('Job search results')",
                    timeout=30000
                )
                print("  Job list page loaded!")
            except:
                print("  Waiting for job list...")
            
            # Wait for job links to actually be in DOM
            await asyncio.sleep(8)  # Give time for JavaScript to render links
            
            # Check if links are there now (NOTE: Blue Shield uses /job/ singular, not /jobs/ plural)
            link_count = await page.evaluate("() => document.querySelectorAll('a[href*=\"/job/\"]').length")
            print(f"  Found {link_count} links containing '/job/'")
            
            if link_count == 0:
                # Wait even longer - Oracle Taleo might be slow
                print("  No links yet, waiting longer for JavaScript to render...")
                await asyncio.sleep(10)
                link_count = await page.evaluate("() => document.querySelectorAll('a[href*=\"/job/\"]').length")
                print(f"  After extra wait: {link_count} links")
            
            print(f"[Blue Shield] Scrolling to load all jobs (each scroll takes 5-10 seconds)...")
            
            # Helper function to count jobs - use very broad selector
            async def count_jobs():
                return await page.evaluate("""
                    () => {
                        // Find ALL links on the page
                        const allLinks = document.querySelectorAll('a');
                        let jobs = new Set();
                        
                        for (const link of allLinks) {
                            // Try both href attribute and href property
                            const href = link.href || link.getAttribute('href') || link.getAttribute('data-href') || '';
                            
                            // Match /job/12345 pattern (singular, not /jobs?query)
                            // NOTE: Blue Shield uses /job/ (singular) not /jobs/ (plural)
                            const match = href.match(/\\/job\\/(\\d+)/);
                            if (match) {
                                jobs.add(match[1]);
                            }
                        }
                        
                        return jobs.size;
                    }
                """)
            
            # Get initial job count
            last_job_count = await count_jobs()
            print(f"  Initial jobs found: {last_job_count}")
            
            if last_job_count == 0:
                print("  No jobs found initially. Waiting longer and checking page...")
                
                # Check if there's a cookie consent or other blocker
                try:
                    # Try to click "Accept" if cookie consent appears
                    accept_btn = await page.query_selector('button:has-text("Accept"), button:has-text("Accept All")')
                    if accept_btn:
                        await accept_btn.click()
                        await asyncio.sleep(2)
                except:
                    pass
                
                # Wait longer for jobs to render
                await asyncio.sleep(10)
                last_job_count = await count_jobs()
                print(f"  After extra wait: {last_job_count} jobs")
                
                if last_job_count == 0:
                    # Debug: check what links actually exist
                    debug_info = await page.evaluate("""
                        () => {
                            const allLinks = Array.from(document.querySelectorAll('a')).slice(0, 20);
                            return allLinks.map(link => ({
                                href: link.href || link.getAttribute('href'),
                                text: link.textContent?.trim().substring(0, 50)
                            })).filter(l => l.href && l.href.includes('/job'));
                        }
                    """)
                    print(f"  Debug: Found {len(debug_info)} links with '/job' in URL")
                    if debug_info:
                        print(f"  Sample links: {debug_info[:3]}")
                    
                    # Continue anyway - maybe jobs will load after scrolling
            
            no_new_jobs_count = 0
            scroll_attempts = 0
            max_scrolls = 20  # Should be enough
            min_scrolls = 10  # Always do at least 10 scrolls to be safe
            
            while scroll_attempts < max_scrolls:
                scroll_attempts += 1
                
                # Scroll down to trigger loading
                print(f"  Scroll {scroll_attempts}: Scrolling to bottom...", end=" ", flush=True)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                
                # Wait 10 seconds for jobs to load (user said 5-10 seconds, we'll do 10 to be safe)
                print("Waiting 10 seconds for jobs to load...", end=" ", flush=True)
                await asyncio.sleep(10)
                
                # Check job count again after waiting
                new_count = await count_jobs()
                
                # Check if we got new jobs
                if new_count == last_job_count:
                    no_new_jobs_count += 1
                    print(f"Found {new_count} jobs (no change)")
                    # Only stop if we've done at least min_scrolls (10) AND no new jobs for 2 scrolls
                    if scroll_attempts >= min_scrolls and no_new_jobs_count >= 2:
                        print(f"  No new jobs loaded after {no_new_jobs_count} consecutive scrolls (total {scroll_attempts} scrolls). Done!")
                        break
                else:
                    no_new_jobs_count = 0
                    print(f"Found {new_count} jobs (+{new_count - last_job_count} new)")
                
                last_job_count = new_count
            
            # Extract all jobs from the fully-loaded page
            print(f"\n[Blue Shield] Extracting jobs from page (found {last_job_count} during scrolling)...")
            
            # Wait a moment for any final rendering
            await asyncio.sleep(5)
            
            # Scroll to top then bottom one more time to ensure everything is loaded
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(2)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(5)
            
            jobs_data = await page.evaluate("""
                () => {
                    const jobs = [];
                    const seenJobIds = new Set();
                    
                    // Find ALL links on the page
                    const allLinks = document.querySelectorAll('a');
                    
                    for (const link of allLinks) {
                        try {
                            // Try multiple ways to get href
                            const href = link.href || 
                                       link.getAttribute('href') || 
                                       link.getAttribute('data-href') ||
                                       (link.onclick ? link.onclick.toString().match(/\\/job\\/(\\d+)/)?.[0] : null) ||
                                       '';
                            
                            // Extract job ID from URL: /job/20252085 (singular, must be numeric ID)
                            // NOTE: Blue Shield uses /job/ (singular) not /jobs/ (plural)
                            const jobIdMatch = href.match(/\\/job\\/(\\d+)/);
                            if (!jobIdMatch) {
                                continue;
                            }
                            
                            const jobId = jobIdMatch[1];
                            
                            // Skip if we've seen this job ID already
                            if (seenJobIds.has(jobId)) {
                                continue;
                            }
                            seenJobIds.add(jobId);
                            
                            // Get title - try link text first
                            let title = link.textContent?.trim() || link.innerText?.trim() || '';
                            
                            // If title is empty or too short, look at parent elements
                            if (!title || title.length < 5) {
                                let parent = link.parentElement;
                                for (let i = 0; i < 3 && parent; i++) {
                                    const parentText = parent.textContent?.trim() || '';
                                    // Look for text that looks like a job title (reasonable length, not too long)
                                    const lines = parentText.split(/[\\n\\r]/).map(l => l.trim()).filter(l => l.length > 5 && l.length < 200);
                                    if (lines.length > 0) {
                                        title = lines[0];
                                        break;
                                    }
                                    parent = parent.parentElement;
                                }
                            }
                            
                            // Clean up title
                            title = title.replace(/[\\n\\r\\t]/g, ' ').replace(/\\s+/g, ' ').trim();
                            if (!title || title.length < 3) {
                                title = 'Job Posting';
                            }
                            
                            // Extract location - look for patterns like "City, CA" or "City, CA, United States"
                            let location = 'California';
                            let searchElement = link.parentElement;
                            for (let i = 0; i < 5 && searchElement; i++) {
                                const text = searchElement.textContent || '';
                                const locMatch = text.match(/([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*,\\s*CA(?:,\\s*United States)?)/);
                                if (locMatch) {
                                    location = locMatch[1].trim();
                                    break;
                                }
                                searchElement = searchElement.parentElement;
                            }
                            
                            // Build full URL (use /job/ singular)
                            let fullUrl = href;
                            if (!href.startsWith('http')) {
                                if (href.startsWith('/')) {
                                    fullUrl = 'https://ecge.fa.us2.oraclecloud.com' + href;
                                } else {
                                    fullUrl = 'https://ecge.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1003/job/' + jobId;
                                }
                            }
                            
                            jobs.push({
                                title: title,
                                href: fullUrl,
                                location: location,
                                jobId: jobId,
                            });
                        } catch (e) {
                            continue;
                        }
                    }
                    
                    return jobs;
                }
            """)
            
            # Convert to our job format
            for job_data in jobs_data:
                job_link = job_data.get('href', '')
                if not job_link:
                    continue
                
                job = {
                    "title": job_data.get('title', 'Job Posting'),
                    "link": job_link,
                    "location": job_data.get('location', 'California'),
                    "date_posted": "N/A",
                    "source": SITE_NAME,
                    "_job_id": job_data.get('jobId'),  # Store for description fetching
                }
                
                all_jobs[job_link] = job
            
            print(f"[Blue Shield] Extracted {len(all_jobs)} unique jobs")
            
            # If we got 0 jobs but the page shows jobs, try one more simple extraction
            if len(all_jobs) == 0:
                print("[Blue Shield] No jobs extracted. Trying simpler extraction method...")
                await asyncio.sleep(5)
                
                # Try the absolute simplest approach - just get all links with job IDs
                simple_jobs = await page.evaluate("""
                    () => {
                        const jobs = [];
                        const seen = new Set();
                        const allLinks = document.querySelectorAll('a');
                        
                        for (const link of allLinks) {
                            const href = link.href || link.getAttribute('href') || '';
                            // NOTE: Blue Shield uses /job/ (singular) not /jobs/ (plural)
                            const match = href.match(/\\/job\\/(\\d+)/);
                            if (match && !seen.has(match[1])) {
                                seen.add(match[1]);
                                const jobId = match[1];
                                const title = link.textContent?.trim() || link.innerText?.trim() || 'Job Posting';
                                const fullUrl = href.startsWith('http') ? href : 
                                              'https://ecge.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1003/job/' + jobId;
                                
                                jobs.push({
                                    title: title.substring(0, 200),
                                    href: fullUrl,
                                    location: 'California',
                                    jobId: jobId
                                });
                            }
                        }
                        return jobs;
                    }
                """)
                
                for job_data in simple_jobs:
                    job_link = job_data.get('href', '')
                    if job_link:
                        job = {
                            "title": job_data.get('title', 'Job Posting'),
                            "link": job_link,
                            "location": job_data.get('location', 'California'),
                            "date_posted": "N/A",
                            "source": SITE_NAME,
                            "_job_id": job_data.get('jobId'),
                        }
                        all_jobs[job_link] = job
                
                print(f"[Blue Shield] Simple extraction found {len(all_jobs)} jobs")
            
        except Exception as e:
            print(f"[Blue Shield] Error during scraping: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await browser.close()
    
    result = list(all_jobs.values())
    print(f"\n[Blue Shield] Total unique jobs scraped: {len(result)}")
    return result


async def fetch_blueshield_descriptions_batch(jobs, headless=False):
    """
    Fetch full job descriptions from Blue Shield job detail API.
    
    Args:
        jobs: List of job dicts with 'link' field (or '_job_id' field)
        headless: Run browser in headless mode for session establishment
    
    Returns:
        Dict mapping job link -> description text
    """
    descriptions = {}
    
    if not jobs:
        return descriptions
    
    # Step 1: Establish session with Playwright (reuse same approach)
    print(f"[Blue Shield] Establishing session for description fetching...")
    cookies_dict = {}
    user_id = None
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, args=["--disable-dev-shm-usage"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0"
        )
        page = await context.new_page()
        
        try:
            await page.goto(f"{JOBS_PORTAL_URL}/jobs", timeout=60000)
            await page.wait_for_load_state("networkidle", timeout=30000)
            await asyncio.sleep(2)
            
            browser_cookies = await context.cookies()
            for cookie in browser_cookies:
                cookies_dict[cookie['name']] = cookie['value']
                if cookie['name'] in ['ORA_CX_USERID', 'ORA_CX_USERID_FUNCTIONAL']:
                    user_id = cookie['value']
            
            if not user_id:
                import uuid
                user_id = str(uuid.uuid4())
        except Exception as e:
            print(f"[Blue Shield] Error establishing session: {e}")
            await browser.close()
            return descriptions
        
        await browser.close()
    
    # Step 2: Use aiohttp with cookies for fast API calls
    cookie_str = "; ".join([f"{k}={v}" for k, v in cookies_dict.items()])
    
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
        "Accept": "*/*",
        "Accept-Language": "en",
        "Referer": f"{JOBS_PORTAL_URL}/jobs",
        "Content-Type": "application/vnd.oracle.adf.resourceitem+json;charset=utf-8",
        "Ora-Irc-Language": "en",
        "Ora-Irc-Cx-UserId": user_id,
        "Cookie": cookie_str,
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        for i, job in enumerate(jobs):
            try:
                # Extract job ID from link or use stored _job_id
                job_id = job.get("_job_id")
                if not job_id:
                    # Extract from link: /jobs/20252085
                    link = job.get("link", "")
                    if "/jobs/" in link:
                        job_id = link.split("/jobs/")[-1].split("/")[0].split("?")[0]
                    else:
                        descriptions[job['link']] = "Error: Could not extract job ID"
                        continue
                
                print(f"  [{i+1}/{len(jobs)}] Fetching Blue Shield: {job.get('title', 'Unknown')[:50]}...", end=" ", flush=True)
                
                # Build API URL
                params = {
                    "expand": "all",
                    "onlyData": "true",
                    "finder": f'ById;Id="{job_id}",siteNumber={SITE_NUMBER}',
                }
                
                async with session.get(JOB_DETAILS_API, params=params, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Extract description from response
                        items = data.get("items", [])
                        if items:
                            job_detail = items[0]
                            
                            # Combine all description fields
                            desc_parts = []
                            
                            # Short description
                            short_desc = job_detail.get("ShortDescriptionStr", "")
                            if short_desc:
                                desc_parts.append(short_desc)
                            
                            # External description
                            ext_desc = job_detail.get("ExternalDescriptionStr", "")
                            if ext_desc:
                                # Strip HTML tags
                                soup = BeautifulSoup(ext_desc, "html.parser")
                                desc_parts.append(soup.get_text(separator=" ", strip=True))
                            
                            # Organization description
                            org_desc = job_detail.get("OrganizationDescriptionStr", "")
                            if org_desc:
                                soup = BeautifulSoup(org_desc, "html.parser")
                                desc_parts.append(soup.get_text(separator=" ", strip=True))
                            
                            # Qualifications
                            quals = job_detail.get("ExternalQualificationsStr", "")
                            if quals:
                                soup = BeautifulSoup(quals, "html.parser")
                                desc_parts.append("Qualifications: " + soup.get_text(separator=" ", strip=True))
                            
                            # Responsibilities
                            resp_str = job_detail.get("ExternalResponsibilitiesStr", "")
                            if resp_str:
                                soup = BeautifulSoup(resp_str, "html.parser")
                                desc_parts.append("Responsibilities: " + soup.get_text(separator=" ", strip=True))
                            
                            full_desc = "\n\n".join(desc_parts)
                            descriptions[job['link']] = full_desc[:10000]  # Limit length
                            print("✓")
                        else:
                            descriptions[job['link']] = "Description not available"
                            print("⚠")
                    else:
                        descriptions[job['link']] = f"Error fetching (Status {resp.status})"
                        print(f"✗ {resp.status}")
                
                await asyncio.sleep(REQUEST_DELAY + random.uniform(0, 1))
            
            except Exception as e:
                descriptions[job['link']] = f"Error: {str(e)[:100]}"
                print(f"✗ {str(e)[:50]}")
                await asyncio.sleep(2)
    
    return descriptions


if __name__ == "__main__":
    async def test():
        jobs = await scrape_blueshield_jobs([], headless=False)
        print(f"\nFound {len(jobs)} jobs")
        for job in jobs[:3]:
            print(f"  - {job['title']} | {job['location']} | {job['link']}")
    
    asyncio.run(test())
