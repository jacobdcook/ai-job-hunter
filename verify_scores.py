#!/usr/bin/env python3
"""
Score verification tool - manually review and adjust AI scores for top GovernmentJobs matches.
Useful for validating that high-scoring jobs are actually good fits for your profile.
"""

import sqlite3
import sys
from database import DB_NAME, export_to_excel, generate_job_id

def verify_scores_by_batch(source="GovernmentJobs.com", min_score=8, max_score=10):
    """
    Interactively review and adjust scores for jobs in a score range.

    Args:
        source: Job source to filter by (e.g., "GovernmentJobs.com")
        min_score: Minimum score to show
        max_score: Maximum score to show
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get jobs in this score range
    cursor.execute("""
        SELECT id, title, location, match_score, description FROM jobs
        WHERE source = ? AND match_score >= ? AND match_score <= ?
        ORDER BY match_score DESC, title ASC
    """, (source, min_score, max_score))

    jobs = cursor.fetchall()

    if not jobs:
        print(f"\nNo {source} jobs with scores {min_score}-{max_score} found.\n")
        conn.close()
        return

    print(f"\n{'='*80}")
    print(f"Score Verification: {source} ({len(jobs)} jobs with scores {min_score}-{max_score})")
    print(f"{'='*80}\n")

    updates = 0

    for idx, job in enumerate(jobs, 1):
        print(f"\n[{idx}/{len(jobs)}] Current Score: {job['match_score']}/10")
        print(f"Title: {job['title']}")
        print(f"Location: {job['location']}")

        if job['description']:
            desc_preview = job['description'][:300].replace('\n', ' ')
            print(f"Description: {desc_preview}...")

        # Get user input
        while True:
            new_score_str = input("\nNew score (1-10) or press Enter to keep current: ").strip()

            if new_score_str == "":
                print("→ Keeping current score")
                break

            try:
                new_score = int(new_score_str)
                if 1 <= new_score <= 10:
                    if new_score != job['match_score']:
                        # Update database
                        cursor.execute(
                            "UPDATE jobs SET match_score = ? WHERE id = ?",
                            (new_score, job['id'])
                        )
                        conn.commit()
                        print(f"✓ Updated: {job['match_score']} → {new_score}")
                        updates += 1
                    else:
                        print("→ Score unchanged")
                    break
                else:
                    print("Please enter a score between 1 and 10")
            except ValueError:
                print("Please enter a valid number")

        # Show progress
        if idx % 5 == 0:
            print(f"\n--- Progress: {idx}/{len(jobs)} reviewed ---")

    conn.close()

    if updates > 0:
        print(f"\n{'='*80}")
        print(f"✓ Updated {updates} score(s)")
        print(f"{'='*80}\n")

        # Ask if user wants to export
        export_now = input("Update Excel file with new scores? (y/n): ").strip().lower()
        if export_now == 'y':
            print("\nExporting to Excel...")
            export_to_excel()
            print("✓ Excel file updated!")
    else:
        print(f"\n{'='*80}")
        print("No score changes made.")
        print(f"{'='*80}\n")


def main():
    """Main verification workflow."""
    print("\n" + "="*80)
    print("  Score Verification Tool")
    print("="*80)

    # Step 1: Review 8-10 scores
    print("\nStep 1: Reviewing HIGH PRIORITY (8-10/10) GovernmentJobs matches")
    print("These are jobs the AI thinks are great fits for your profile.")
    print("Review each title and adjust the score if needed.\n")

    input("Press Enter to start reviewing 8-10/10 scores...")
    verify_scores_by_batch(source="GovernmentJobs.com", min_score=8, max_score=10)

    # Step 2: Review 6-7 scores
    print("\n" + "="*80)
    print("Step 2: Reviewing MEDIUM PRIORITY (6-7/10) GovernmentJobs matches")
    print("These are decent matches but not top tier.\n")

    continue_medium = input("Review 6-7/10 scores? (y/n): ").strip().lower()
    if continue_medium == 'y':
        input("Press Enter to start...")
        verify_scores_by_batch(source="GovernmentJobs.com", min_score=6, max_score=7)

    print("\n✓ Score verification complete!")
    print("Your updated scores have been saved to the database and Excel file.\n")


if __name__ == "__main__":
    main()
