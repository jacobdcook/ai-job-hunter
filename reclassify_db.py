#!/usr/bin/env python3
"""Reclassify all analyzed jobs in the database using updated taxonomy + seniority filter.
Does NOT re-run Groq AI — uses existing match_score values.
Safe to run multiple times (idempotent)."""

import sqlite3
import re
from database import DB_NAME, export_to_excel, update_job_feeder_classification, update_job_skip_reason
from job_classifier import classify_and_score_job
from config import SENIORITY_EXCLUDE


def word_match(keyword, text):
    pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
    return bool(re.search(pattern, text.lower()))


def main():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT id, title, description, match_score, status, source, feeder_category
        FROM jobs
        WHERE match_score IS NOT NULL AND match_score > 0
    """)
    rows = c.fetchall()
    conn.close()

    print(f"Found {len(rows)} analyzed jobs to reclassify")

    reclassified = 0
    seniority_filtered = 0
    category_changes = {}

    for row in rows:
        job_id = row['id']
        title = row['title'] or ""
        desc = row['description'] or ""
        groq_score = row['match_score']
        old_category = row['feeder_category']

        title_lower = title.lower()
        matched_seniority = None
        for kw in SENIORITY_EXCLUDE:
            if word_match(kw, title) or kw.lower() in title_lower:
                matched_seniority = kw
                break

        if matched_seniority:
            update_job_skip_reason(job_id, f"Seniority: '{matched_seniority}' too high for entry-level")
            seniority_filtered += 1
            continue

        classification = classify_and_score_job(title, desc, groq_score)
        new_category = classification['category']

        if old_category and old_category != new_category:
            key = f"{old_category}->{new_category}"
            category_changes[key] = category_changes.get(key, 0) + 1

        update_job_feeder_classification(
            job_id,
            new_category,
            classification['feeder_score'],
            " | ".join(classification['reasons']),
            classification['priority_score']
        )
        reclassified += 1

    print(f"\nReclassified: {reclassified}")
    print(f"Seniority filtered: {seniority_filtered}")
    if category_changes:
        print("\nCategory changes:")
        for change, count in sorted(category_changes.items()):
            print(f"  {change}: {count}")

    print("\nRe-exporting to Excel...")
    export_to_excel()


if __name__ == "__main__":
    main()
