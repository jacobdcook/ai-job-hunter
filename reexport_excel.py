#!/usr/bin/env python3
"""Re-export the Excel file from the existing database.
Run this after changing config settings (PREFERRED_CITIES, etc.) to update Excel
without re-scraping or re-analyzing jobs. Takes ~2 seconds."""

from database import export_to_excel

if __name__ == "__main__":
    export_to_excel()
