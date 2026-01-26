# Quick Setup Guide 🚀

Follow these steps to get AI Job Hunter running in 5 minutes:

## Step 1: Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

## Step 2: Configure Your Profile

```bash
# Copy the template
cp config_template.py config.py

# Edit with your info
nano config.py  # or use VS Code, vim, etc.
```

**Important:** Fill in `YOUR_BACKGROUND` with:
- Your name, education, certifications
- Your technical skills (Python, Linux, etc.)
- Your projects
- Your work experience
- Your target job roles

## Step 3: Get API Key

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up (free)
3. Create an API key
4. Copy it

## Step 4: Add API Key

```bash
# Copy the example
cp .env.example .env

# Edit and paste your key
nano .env
```

Your `.env` should look like:
```
GROQ_API_KEY=gsk_your_actual_key_here
```

## Step 5: Customize Your Search

Edit `config.py` to match your needs:

- **`SEARCH_QUERIES`**: Keywords for PG&E/SMUD searches
- **`STATE_CA_KEYWORDS`**: Keywords for State CA searches (e.g., ["IT", "Security", "Analyst"])
- **`STATE_CA_LOCATION`**: Your county (e.g., "Sacramento County") or `None` for all
- **`INTEREST_KEYWORDS`**: Tech keywords you care about (used for AI filtering)
- **`NOISE_KEYWORDS`**: Words to filter out (e.g., "Senior", "Manager")
- **`IGNORE_FIELDS`**: Fields to completely ignore (e.g., "Nurse", "Physician")

## Step 6: Run It!

```bash
# Make sure venv is activated
source venv/bin/activate

# Run the job hunter
python3 main.py
```

Choose an option:
- **Option 4**: State of California only
- **Option 5**: All sites
- **Option 6**: Use your config.py settings
- **Option 7**: Re-analyze existing jobs (skip scraping)

## Step 7: Check Your Results

After it finishes, open `jobs_master.xlsx`:
- **All Jobs** tab: Everything sorted by match score
- **State CA** tab: Just State of California jobs
- **Other tabs**: Per-site breakdowns

## Troubleshooting

**"ModuleNotFoundError"**: Make sure venv is activated (`source venv/bin/activate`)

**"GROQ_API_KEY not found"**: Check your `.env` file exists and has the key

**No jobs found**: Check your keywords in `config.py` match what's on the job sites

**IP blocked**: The scrapers have built-in delays. If you get blocked, wait a few hours and try again.

## Next Steps

- Customize `INTEREST_KEYWORDS` to match your tech stack
- Adjust `NOISE_KEYWORDS` if you want to see senior roles
- Run `python3 export_excel.py` anytime to regenerate the Excel file
- Use Option 7 to re-analyze jobs without re-scraping

Happy job hunting! 🎯
