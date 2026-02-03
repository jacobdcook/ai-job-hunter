"""
Interactive setup wizard for AI Job Hunter.
Guides new users through configuring their profile and preferences.

Usage: python3 main.py setup
"""

import os
import json
from config_template import (
    ENTRY_LEVEL_INDICATORS, NOISE_KEYWORDS, IGNORE_FIELDS, 
    INTEREST_KEYWORDS, ENABLED_SITES
)


def clear_screen():
    """Clear terminal screen."""
    os.system('clear' if os.name == 'posix' else 'cls')


def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_section(title):
    """Print a section header."""
    print(f"\n{'─' * 70}")
    print(f"  {title}")
    print(f"{'─' * 70}\n")


def get_multiline_input(prompt, placeholder=""):
    """Get multiline input from user."""
    print(f"\n{prompt}")
    if placeholder:
        print(f"(Example: {placeholder})\n")
    print("(Type 'END' on a new line when done, or 'SKIP' to skip)\n")
    
    lines = []
    while True:
        line = input("> ").strip()
        if line.upper() == 'END':
            break
        elif line.upper() == 'SKIP':
            return None
        elif line:
            lines.append(line)
    
    return "\n".join(lines) if lines else None


def get_yes_no(prompt):
    """Get yes/no response from user."""
    while True:
        response = input(f"\n{prompt} (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        print("Please enter 'y' or 'n'")


def setup_background():
    """Collect user's background and skills."""
    print_section("👤 YOUR BACKGROUND & SKILLS")
    
    print("""This helps the AI understand what jobs are relevant for you.
Include:
  • Your education & certifications
  • Programming languages & tools you know
  • Years of experience in your field
  • Any major projects or achievements""")
    
    background = get_multiline_input(
        "Tell us about yourself:",
        placeholder="5 years Python/Azure, CCNA certified, penetration testing experience, Linux admin"
    )
    
    return background or "Not specified"


def setup_search_keywords():
    """Configure search keywords for job boards."""
    print_section("🔍 SEARCH KEYWORDS")
    
    print("""These keywords will be used to search job boards.
Examples: IT, Security, Analyst, Python, Network, Infrastructure""")
    
    keywords_str = input("\nEnter keywords (comma-separated):\n> ").strip()
    keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
    
    return keywords if keywords else ["IT", "Security", "Analyst"]


def setup_interest_keywords():
    """Configure high-priority interest keywords."""
    print_section("⭐ PRIORITY KEYWORDS (Jobs you want)")
    
    print("""These keywords get PRIORITY - jobs matching these are kept even if Senior/Manager.
Default includes: Cyber, Security, IT, Analyst, Systems, Python, Cloud, etc.

Modify if needed:""")
    
    keywords_str = input("\nEnter priority keywords (comma-separated, or press Enter for defaults):\n> ").strip()
    
    if keywords_str:
        return [k.strip() for k in keywords_str.split(',') if k.strip()]
    else:
        return INTEREST_KEYWORDS


def setup_noise_keywords():
    """Configure noise keywords to filter out."""
    print_section("🚫 FILTER OUT (Senior/Manager/etc)")
    
    print(f"""These keywords filter out jobs you probably don't want.
Current default: {', '.join(NOISE_KEYWORDS)}

Press Enter to keep defaults, or enter your own (comma-separated):""")
    
    keywords_str = input("\n> ").strip()
    
    if keywords_str:
        return [k.strip() for k in keywords_str.split(',') if k.strip()]
    else:
        return NOISE_KEYWORDS


def setup_ignore_fields():
    """Configure fields/roles to completely ignore."""
    print_section("⛔ COMPLETELY IGNORE (Medical, Nursing, etc)")
    
    print(f"""Jobs with these keywords are ALWAYS filtered out.
Currently configured: {len(IGNORE_FIELDS)} medical/clinical/non-tech roles

Want to add more fields to ignore? (e.g., 'Accounting', 'HR', 'Legal')""")
    
    add_more = get_yes_no("Add additional fields to ignore?")
    
    extra = []
    if add_more:
        extra_str = input("\nEnter fields (comma-separated):\n> ").strip()
        extra = [f.strip() for f in extra_str.split(',') if f.strip()]
    
    return IGNORE_FIELDS + extra


def setup_locations():
    """Configure location preferences."""
    print_section("📍 LOCATION PREFERENCES")
    
    print("""Configure where you want to search for jobs.
Leave blank to search everywhere.""")
    
    locations = {}
    
    # State of California
    print("\n📌 State of California (CalCareers):")
    state_location = input("County name (e.g., 'Sacramento County') or press Enter for all CA:\n> ").strip() or None
    locations['STATE_CA_LOCATION'] = state_location
    
    # Kaiser
    print("\n📌 Kaiser Permanente:")
    print("(Keep default for now - edit manually if needed)")
    locations['KAISER_LOCATION_URL'] = None
    
    return locations


def setup_sites():
    """Configure which job sites to use."""
    print_section("🌐 JOB SITES TO SEARCH")
    
    enabled = {}
    sites = [
        ('PG&E', 'pge', 'Pacific Gas & Electric - California'),
        ('SMUD', 'smud', 'Sacramento Municipal Utility District'),
        ('Kaiser', 'kaiser', 'Kaiser Permanente hospitals'),
        ('State CA', 'state_ca', 'California state jobs (CalCareers)'),
        ('CommonSpirit', 'commonspirit', 'CommonSpirit Health (Dignity, CHI)'),
        ('Sutter', 'sutter', 'Sutter Health hospitals'),
        ('UC Davis', 'ucdavis', 'UC Davis Health & administration'),
    ]
    
    print("Which sites do you want to search? (y/n for each)\n")
    
    for display_name, key, description in sites:
        response = input(f"{display_name:15} - {description} (y/n): ").strip().lower()
        enabled[key] = response in ['y', 'yes']
    
    return enabled


def setup_resume():
    """Collect resume/profile information."""
    print_section("📄 RESUME/PROFILE (Optional)")
    
    print("""You can paste your resume or LinkedIn profile text.
This helps the AI understand your background better.
(Optional - you already provided background info above)""")
    
    use_resume = get_yes_no("Include resume/profile text?")
    
    if use_resume:
        resume_text = get_multiline_input(
            "Paste your resume or profile text:",
            placeholder="(Your job history, skills, etc.)"
        )
        return resume_text
    
    return None


def generate_config(user_data):
    """Generate config.py from user input."""
    
    config_content = '''"""
AI Job Hunter Configuration
Auto-generated by setup wizard

Customize these settings as needed!
"""

# =========================================================================
# 1. YOUR BACKGROUND (Most Important!)
# =========================================================================
YOUR_BACKGROUND = """''' + user_data['background'] + '''"""

'''
    
    if user_data.get('resume'):
        config_content += f'''
# Additional resume/profile information
RESUME_TEXT = """''' + user_data['resume'] + '''"""

'''
    
    config_content += f'''
# =========================================================================
# 2. SEARCH & FILTERING KEYWORDS
# =========================================================================
SEARCH_QUERIES = {user_data['search_keywords']}

INTEREST_KEYWORDS = {user_data['interest_keywords']}

NOISE_KEYWORDS = {user_data['noise_keywords']}

IGNORE_FIELDS = {user_data['ignore_fields']}

ENTRY_LEVEL_INDICATORS = {ENTRY_LEVEL_INDICATORS}

# =========================================================================
# 3. LOCATION PREFERENCES
# =========================================================================
STATE_CA_LOCATION = {repr(user_data['locations'].get('STATE_CA_LOCATION'))}
STATE_CA_KEYWORDS = {user_data['search_keywords']}

# =========================================================================
# 4. ENABLED JOB SITES
# =========================================================================
ENABLED_SITES = {{
    "pge": {user_data['sites'].get('pge', True)},
    "smud": {user_data['sites'].get('smud', True)},
    "kaiser": {user_data['sites'].get('kaiser', True)},
    "state_ca": {user_data['sites'].get('state_ca', True)},
    "commonspirit": {user_data['sites'].get('commonspirit', True)},
    "sutter": {user_data['sites'].get('sutter', True)},
    "ucdavis": {user_data['sites'].get('ucdavis', True)},
}}

# Max pages to scrape per site (increase for more jobs, be respectful!)
PG_E_MAX_PAGES = 20
SMUD_MAX_PAGES = 20
KAISER_MAX_PAGES = 20
STATE_CA_MAX_PAGES = 20
COMMONSPIRIT_MAX_PAGES = 20
SUTTER_MAX_PAGES = 20
UCDAVIS_MAX_PAGES = 20
'''
    
    return config_content


def run_setup_wizard():
    """Run the interactive setup wizard."""
    
    clear_screen()
    print_header("🚀 AI JOB HUNTER - SETUP WIZARD")
    
    print("""Welcome! This wizard will help you configure AI Job Hunter.
It should take about 5-10 minutes.

You can change any of these settings later by editing config.py directly.
""")
    
    input("Press Enter to start...")
    
    # Collect all data
    user_data = {}
    
    clear_screen()
    print_header("STEP 1: BACKGROUND")
    user_data['background'] = setup_background()
    
    clear_screen()
    print_header("STEP 2: KEYWORDS")
    user_data['search_keywords'] = setup_search_keywords()
    user_data['interest_keywords'] = setup_interest_keywords()
    user_data['noise_keywords'] = setup_noise_keywords()
    
    clear_screen()
    print_header("STEP 3: FILTERS")
    user_data['ignore_fields'] = setup_ignore_fields()
    
    clear_screen()
    print_header("STEP 4: LOCATIONS")
    user_data['locations'] = setup_locations()
    
    clear_screen()
    print_header("STEP 5: JOB SITES")
    user_data['sites'] = setup_sites()
    
    clear_screen()
    print_header("STEP 6: RESUME (Optional)")
    user_data['resume'] = setup_resume()
    
    # Generate and save config
    clear_screen()
    print_header("✅ GENERATING YOUR CONFIG")
    
    config_content = generate_config(user_data)
    
    # Save config.py
    config_path = "config.py"
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    print(f"✅ Config saved to: {config_path}\n")
    
    # Show summary
    print_section("📋 CONFIGURATION SUMMARY")
    
    print(f"✓ Background: Configured")
    print(f"✓ Search keywords: {len(user_data['search_keywords'])} keywords")
    print(f"✓ Priority keywords: {len(user_data['interest_keywords'])} keywords")
    print(f"✓ Filter keywords: {len(user_data['noise_keywords'])} keywords")
    print(f"✓ Ignore fields: {len(user_data['ignore_fields'])} fields")
    print(f"✓ Sites enabled: {sum(1 for v in user_data['sites'].values() if v)} sites")
    
    if user_data['locations']['STATE_CA_LOCATION']:
        print(f"✓ California location: {user_data['locations']['STATE_CA_LOCATION']}")
    
    print("\n" + "=" * 70)
    print("""
🎉 Setup complete! You're ready to go!

Next steps:
  1. Make sure .env has your GROQ_API_KEY
  2. Run: python3 main.py
  3. Select option to start scraping

Happy job hunting! 🚀
""")
    print("=" * 70)


if __name__ == "__main__":
    run_setup_wizard()
