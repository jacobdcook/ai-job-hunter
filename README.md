# AI Job Hunter 🎯

An AI-powered job search automation tool that scrapes job listings, filters them based on your preferences, and uses AI to score how well each job matches your background.

## Features

- **Multi-site scraping**: Search multiple job boards (PG&E, SMUD, and more)
- **Smart filtering**: Automatically filters out senior/expert roles you're not targeting
- **AI-powered matching**: Uses Groq AI to score jobs 1-10 based on YOUR specific background
- **Excel export**: Generates a master Excel file with clickable apply links
- **Deduplication**: Tracks jobs in a local database so you never see duplicates
- **"Last Seen" tracking**: Know which jobs are still active vs. potentially closed

## Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/ai-job-hunter.git
cd ai-job-hunter
```

### 2. Set up Python environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure your profile
```bash
# Copy the template
cp config_template.py config.py

# Edit config.py with your background, skills, and target roles
nano config.py  # or use your preferred editor
```

### 4. Set up your API key
```bash
# Copy the example env file
cp .env.example .env

# Add your Groq API key (free at https://console.groq.com)
nano .env
```

### 5. Run the job hunter
```bash
python3 main.py
```

## Output

After running, you'll have:
- **`jobs_master.xlsx`**: Excel file with all jobs, sorted by match score
- **`jobs.db`**: SQLite database tracking all jobs (for deduplication)

### Priority Guide
| Score | Priority | Action |
|-------|----------|--------|
| 8-10 | ⭐ HIGH | Apply ASAP! |
| 5-7 | ✅ MEDIUM | Worth applying |
| 1-4 | 📋 LOW | Only if desperate |

## Configuration

### `config.py`

| Variable | Description |
|----------|-------------|
| `YOUR_BACKGROUND` | Your education, skills, projects, and target roles |
| `SEARCH_QUERIES` | Keywords to search for on job sites |
| `ENTRY_LEVEL_INDICATORS` | Words that mark a job as entry-level (always kept) |
| `NOISE_KEYWORDS` | Words that filter out senior roles |
| `ENABLED_SITES` | Toggle which job sites to search |

### `.env`

```
GROQ_API_KEY=your_api_key_here
```

Get a free API key at [console.groq.com](https://console.groq.com)

## Supported Job Sites

| Site | Status | Notes |
|------|--------|-------|
| PG&E | ✅ Working | Pacific Gas & Electric |
| SMUD | 🚧 Coming Soon | Sacramento Municipal Utility District |

## Commands

```bash
# Run full job search + AI analysis
python3 main.py

# Export current database to Excel (without re-scraping)
python3 export_excel.py
```

## How It Works

1. **Scrape**: Uses Playwright to search job sites for your keywords
2. **Filter**: Removes senior/expert roles (unless marked entry-level)
3. **Dedupe**: Checks against database to find only NEW jobs
4. **Fetch**: Gets full job descriptions for new jobs
5. **Analyze**: Sends each job to Groq AI for scoring
6. **Export**: Creates/updates master Excel file with all jobs

## Contributing

PRs welcome! To add a new job site:

1. Create a new scraper in `scrapers/` folder
2. Follow the interface pattern from `scrapers/pge.py`
3. Add the site to `ENABLED_SITES` in `config_template.py`
4. Submit a PR!

## License

MIT License - Use it, modify it, land that job! 🚀

## Disclaimer

This tool is for personal job searching only. Be respectful of job site rate limits and terms of service. The AI scores are suggestions, not guarantees - always read the full job description before applying.
