#!/usr/bin/env python3
"""
Standalone script to export all jobs from the database to Excel.
Run this anytime to get an updated Excel file with all your jobs.
"""

from database import export_to_excel

if __name__ == "__main__":
    print("Exporting jobs to Excel...")
    filename = export_to_excel()
    if filename:
        print(f"\n✅ Success! Open '{filename}' to view your jobs.")
        print("\n📊 Priority Guide:")
        print("   ⭐ HIGH PRIORITY (8-10): Great matches - apply ASAP!")
        print("   ✅ MEDIUM PRIORITY (5-7): Decent matches - worth applying")
        print("   📋 LOW PRIORITY (1-4): Weak matches - only if desperate")
    else:
        print("❌ No jobs found in database.")
