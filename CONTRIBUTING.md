# Contributing to AI Job Hunter 🚀

First off, thank you for considering contributing to AI Job Hunter! It's people like you who make this tool better for everyone.

## How Can I Contribute?

### Adding New Job Sites
We are always looking to expand our coverage! If you want to add a new company or job board:
1.  Check the `scrapers/` directory for existing examples (like `pge.py` or `kaiser.py`).
2.  Create a new Python file for the site.
3.  Ensure your scraper returns a list of dictionaries with `title`, `link`, `location`, and `source`.
4.  Add the new site to `ENABLED_SITES` in `config_template.py`.

### Improving Filtering Logic
Our goal is to reduce noise. If you have better keywords for `IGNORE_FIELDS` or `INTEREST_KEYWORDS`, please share them!

### Bug Reports & Feature Requests
Feel free to open an issue if you find a bug or have a great idea for a new feature.

## Development Setup
1.  Fork the repo.
2.  Install dependencies: `pip install -r requirements.txt`.
3.  Install Playwright browsers: `playwright install chromium`.
4.  Run tests or the main script.

Happy Hunting!
