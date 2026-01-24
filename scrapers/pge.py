"""
PG&E (Pacific Gas & Electric) Job Scraper
Website: https://jobs.pge.com
"""

import asyncio
from playwright.async_api import async_playwright
import re

SITE_NAME = "PG&E"
BASE_URL = "https://jobs.pge.com"


async def scrape_pge_jobs(search_query="Security", headless=False):
    """
    Scrapes ALL pages of PG&E job results for a given search query.
    Uses the site's internal API for pagination (much more reliable).
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, slow_mo=100)
        context = await browser.new_context()
        page = await context.new_page()
        
        api_url = f"{BASE_URL}/search-jobs/results"
        
        all_jobs = []
        current_page = 1
        total_pages = 1
        
        print(f"[PG&E] Searching for '{search_query}'...")
        
        search_url = f"{BASE_URL}/search-jobs?k={search_query}"
        await page.goto(search_url, timeout=60000)
        
        try:
            await page.wait_for_selector("#search-results", timeout=15000)
        except:
            print(f"[PG&E] No results found for '{search_query}'")
            await browser.close()
            return []
        
        # Get total pages
        try:
            total_pages_elem = await page.query_selector(".pagination-total-pages")
            if total_pages_elem:
                total_pages_text = await total_pages_elem.inner_text()
                match = re.search(r'(\d+)', total_pages_text)
                if match:
                    total_pages = int(match.group(1))
        except:
            total_pages = 1
        
        print(f"[PG&E] Found {total_pages} page(s) for '{search_query}'")
        
        while current_page <= total_pages:
            print(f"[PG&E] Processing page {current_page}/{total_pages} for '{search_query}'...")
            
            job_cards = await page.query_selector_all("#search-results-list ul li")
            
            for card in job_cards:
                link_elem = await card.query_selector("a")
                if not link_elem:
                    continue
                    
                title_elem = await card.query_selector("h2")
                title = await title_elem.inner_text() if title_elem else await link_elem.inner_text()
                href = await link_elem.get_attribute("href")
                
                if not href:
                    continue
                    
                full_link = BASE_URL + href if href.startswith("/") else href
                
                location_elem = await card.query_selector(".job-location")
                location = await location_elem.inner_text() if location_elem else "Unknown"
                
                all_jobs.append({
                    "title": title.strip(),
                    "link": full_link,
                    "location": location.strip(),
                    "date_posted": "N/A",
                    "source": SITE_NAME
                })
            
            if current_page < total_pages:
                current_page += 1
                
                params = {
                    "ActiveFacetID": "0",
                    "CurrentPage": str(current_page),
                    "RecordsPerPage": "15",
                    "Distance": "50",
                    "RadiusUnitType": "0",
                    "Keywords": search_query,
                    "Location": "",
                    "ShowRadius": "False",
                    "IsPagination": "False",
                    "CustomFacetName": "",
                    "FacetTerm": "",
                    "FacetType": "0",
                    "SearchResultsModuleName": "Banner+-+Search+Results",
                    "SearchFiltersModuleName": "Search+Filters",
                    "SortCriteria": "0",
                    "SortDirection": "0",
                    "SearchType": "1",
                    "OrganizationIds": "29673",
                    "PostalCode": "",
                    "ResultsType": "0"
                }
                
                query_string = "&".join([f"{k}={v}" for k, v in params.items()])
                full_api_url = f"{api_url}?{query_string}"
                
                response = await page.evaluate(f"""
                    async () => {{
                        const resp = await fetch("{full_api_url}", {{
                            headers: {{
                                "X-Requested-With": "XMLHttpRequest",
                                "Accept": "application/json"
                            }}
                        }});
                        return await resp.json();
                    }}
                """)
                
                if response and response.get("results"):
                    await page.evaluate(f"""
                        document.querySelector('#search-results-list').innerHTML = 
                            new DOMParser().parseFromString(`{response['results']}`, 'text/html')
                            .querySelector('#search-results-list').innerHTML;
                    """)
                    await asyncio.sleep(0.5)
                else:
                    print(f"[PG&E] Failed to fetch page {current_page}")
                    break
            else:
                break
        
        print(f"[PG&E] Scraped {len(all_jobs)} jobs for '{search_query}'")
        await browser.close()
        return all_jobs


async def fetch_pge_descriptions_batch(jobs, headless=False):
    """
    Fetch descriptions for multiple PG&E jobs using ONE browser instance.
    """
    if not jobs:
        return {}
    
    results = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        
        total = len(jobs)
        for i, job in enumerate(jobs, 1):
            url = job['link']
            title = job['title']
            print(f"  [{i}/{total}] Fetching: {title[:50]}...")
            
            description = ""
            try:
                await page.goto(url, timeout=20000)
                selectors = [".job-description", ".ats-description", ".job-info", "#job-details"]
                for selector in selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=3000)
                        desc_elem = await page.query_selector(selector)
                        if desc_elem:
                            description = await desc_elem.inner_text()
                            if description:
                                break
                    except:
                        continue
            except Exception as e:
                print(f"    Error: {e}")
            
            results[url] = description.strip()
        
        await browser.close()
    
    return results


if __name__ == "__main__":
    async def test():
        jobs = await scrape_pge_jobs("Associate", headless=False)
        print(f"\nFound {len(jobs)} jobs:")
        for j in jobs[:5]:
            print(f"- {j['title']} ({j['location']})")
    
    asyncio.run(test())
