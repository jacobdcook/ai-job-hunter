import sqlite3
import os
import pandas as pd
import hashlib
from datetime import datetime

DB_NAME = "jobs.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT,
            link TEXT,
            location TEXT,
            date_posted TEXT,
            description TEXT,
            match_score INTEGER,
            missing_skills TEXT,
            analysis TEXT,
            status TEXT DEFAULT 'new',
            last_seen TEXT,
            source TEXT
        )
    ''')
    
    # Check if last_seen column exists (for migration)
    try:
        c.execute("SELECT last_seen FROM jobs LIMIT 1")
    except sqlite3.OperationalError:
        print("Adding 'last_seen' column to database...")
        c.execute("ALTER TABLE jobs ADD COLUMN last_seen TEXT")
    
    # Check if source column exists (for migration)
    try:
        c.execute("SELECT source FROM jobs LIMIT 1")
    except sqlite3.OperationalError:
        print("Adding 'source' column to database...")
        c.execute("ALTER TABLE jobs ADD COLUMN source TEXT")
    
    conn.commit()
    conn.close()


def generate_job_id(link):
    """Generate a unique job ID from the link.
    Uses a hash of the normalized URL to avoid collisions."""
    # Normalize: strip trailing slash, lowercase
    normalized = link.rstrip('/').lower()
    # Create a short hash (first 16 chars of md5)
    return hashlib.md5(normalized.encode()).hexdigest()[:16]

def save_job(job_data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Use hash of link for unique ID (avoids collision from trailing slashes, etc.)
    job_id = generate_job_id(job_data['link'])
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    source = job_data.get('source', 'Unknown')
    
    try:
        c.execute('''
            INSERT INTO jobs (id, title, link, location, date_posted, description, status, last_seen, source)
            VALUES (?, ?, ?, ?, ?, ?, 'new', ?, ?)
        ''', (
            job_id,
            job_data['title'],
            job_data['link'],
            job_data['location'],
            job_data.get('date_posted', 'N/A'),
            job_data.get('description', ''),
            now,
            source
        ))
        conn.commit()
        return True # New job saved
    except sqlite3.IntegrityError:
        # Job already exists, just update the last_seen timestamp
        c.execute("UPDATE jobs SET last_seen = ? WHERE id = ?", (now, job_id))
        conn.commit()
        return False # Job already exists
    finally:
        conn.close()

def update_job_analysis(job_id, score, missing_skills, analysis):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        UPDATE jobs 
        SET match_score = ?, missing_skills = ?, analysis = ?, status = 'analyzed'
        WHERE id = ?
    ''', (score, missing_skills, analysis, job_id))
    conn.commit()
    conn.close()


def update_job_failed_analysis(job_id, error_message, status="rate_limited"):
    """Mark job as failed (e.g. rate limit) so ANALYZE UNANALYZED will retry it."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        UPDATE jobs 
        SET match_score = NULL, analysis = ?, status = ?
        WHERE id = ?
    ''', (error_message[:500] if error_message else "Error during analysis", status, job_id))
    conn.commit()
    conn.close()


def update_job_skip_reason(job_id, reason):
    """Mark job as skipped with a reason (shows in Excel Notes)."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        UPDATE jobs 
        SET status = 'skipped_filter', analysis = ?, match_score = NULL
        WHERE id = ?
    ''', (reason[:500] if reason else "Skipped", job_id))
    conn.commit()
    conn.close()


def update_job_title(job_id, title):
    """Update a job's title (e.g. after parsing from State CA detail page)."""
    if not title or not title.strip():
        return
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE jobs SET title = ? WHERE id = ?", (title.strip()[:500], job_id))
    conn.commit()
    conn.close()

def get_new_jobs():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM jobs WHERE status = 'new'")
    rows = c.fetchall()
    conn.close()
    return rows


def get_new_jobs_as_dicts():
    """Get all 'new' status jobs as dictionaries for re-filtering."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, title, link, location, source FROM jobs WHERE status = 'new'")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def reset_failed_analyses():
    """Reset jobs that got score 0 (failed API calls) so they can be re-analyzed."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE jobs SET status = 'new', match_score = NULL WHERE match_score = 0 OR match_score IS NULL")
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected

def get_jobs_needing_analysis():
    """Get jobs that are new, rate_limited, or failed previous analysis (score 0)."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT * FROM jobs
        WHERE status IN ('new', 'rate_limited') OR match_score = 0 OR match_score IS NULL
    """)
    rows = c.fetchall()
    conn.close()
    return rows

def get_jobs_to_refilter():
    """Get jobs that need to be re-evaluated by the filters (not yet fully analyzed or explicitly skipped)."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Return dict-like rows
    c = conn.cursor()
    c.execute("""
        SELECT id, title, link, location, source FROM jobs
        WHERE status NOT IN ('analyzed', 'skipped_filter')
          AND (match_score IS NULL OR match_score = 0)
    """)
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def export_to_excel(filename=None):
    """Export all jobs to an Excel file with tabs per source.
    Creates: All Jobs, PG&E, SMUD, Kaiser, State CA tabs (tabs only created if jobs exist).
    Always uses jobs_master.xlsx (overwrites existing file)."""
    if filename is None:
        filename = "jobs_master.xlsx"  # Single master file - always overwrites
    
    conn = sqlite3.connect(DB_NAME)
    
    # Get ALL jobs from database with source
    query = """
        SELECT 
            title,
            location,
            match_score,
            missing_skills,
            analysis,
            link,
            date_posted,
            status,
            last_seen,
            source
        FROM jobs
        ORDER BY 
            CASE 
                WHEN match_score IS NULL THEN 0
                ELSE match_score 
            END DESC,
            title ASC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        print("No jobs to export. Run a scrape first (options 1-9).")
        return None
    
    # Add priority column based on score and status
    def get_priority(row):
        score = row['match_score']
        status = row['status']
        if status == 'no_description':
            return "NO DESCRIPTION"
        if status == 'skipped_filter':
            return "SKIPPED (see Notes)"
        if status == 'skipped_ai_title':
            return "SKIPPED BY AI"
        if status == 'rate_limited':
            return "RATE LIMITED (retry later)"
        if pd.isna(score) or score is None:
            return "Not Analyzed"
        elif score >= 8:
            return "HIGH PRIORITY ⭐"
        elif score >= 5:
            return "MEDIUM PRIORITY ✅"
        elif score >= 1:
            return "LOW PRIORITY 📋"
        else:
            return "SKIP"

    df['Priority'] = df.apply(get_priority, axis=1)

    # Add Notes column: why no description / why skipped (so you have context at a glance)
    def get_notes(row):
        status = row['status']
        analysis = row['analysis'] if pd.notna(row['analysis']) and str(row['analysis']).strip() else ""
        if status == 'skipped_filter' and analysis:
            return analysis
        if status == 'skipped_ai_title':
            return "Skipped by AI (title not relevant to your background)"
        if status == 'no_description':
            return "No description (not fetched or job removed from source)"
        if status == 'rate_limited':
            return "Rate limit reached (will retry on next ANALYZE UNANALYZED)"
        if status == 'failed' and analysis:
            return analysis
        return ""

    df['Notes'] = df.apply(get_notes, axis=1)

    # Reorder columns for better readability (include source and Notes)
    column_order = ['Priority', 'Notes', 'match_score', 'title', 'location', 'source', 'link',
                   'missing_skills', 'analysis', 'date_posted', 'last_seen', 'status']
    df = df[column_order]

    # Rename columns for cleaner Excel output
    df.columns = ['Priority', 'Notes', 'Score', 'Job Title', 'Location', 'Source', 'Apply Link',
                  'Missing Skills', 'AI Analysis', 'Date Posted', 'Last Seen (Active)', 'Status']
    
    from openpyxl.styles import Font, PatternFill, Alignment
    
    def format_worksheet(worksheet, link_col_idx=5):
        """Apply formatting to a worksheet."""
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # Make links clickable
        link_font = Font(color="0563C1", underline="single")
        for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row):
            link_cell = row[link_col_idx]
            if link_cell.value and isinstance(link_cell.value, str) and link_cell.value.startswith('http'):
                link_cell.font = link_font
                link_cell.hyperlink = link_cell.value
        
        # Format header row
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
    
    # Get all unique sources (handle None/NaN values)
    unique_sources = df['Source'].dropna().unique()
    
    # Create tab name mapping for cleaner names
    tab_name_map = {
        'PG&E': 'PG&E',
        'SMUD': 'SMUD',
        'Kaiser Permanente': 'Kaiser',
        'State of California': 'State CA',
        'Sutter Health': 'Sutter',
        'UC Davis': 'UC Davis',
    }
    
    # Create Excel writer with multiple sheets
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # Write All Jobs tab
        df.to_excel(writer, sheet_name='All Jobs', index=False)
        format_worksheet(writer.sheets['All Jobs'], link_col_idx=6)

        # Top matches (score >= 7) for quick apply
        df_top = df[df['Score'].notna() & (df['Score'] >= 7)].copy()
        if not df_top.empty:
            df_top.to_excel(writer, sheet_name='Top matches (7+)', index=False)
            format_worksheet(writer.sheets['Top matches (7+)'], link_col_idx=6)
            tabs_created_top = [f"Top matches (7+) ({len(df_top)})"]
        else:
            tabs_created_top = []

        # Create a tab for each unique source
        tabs_created = []
        for source in unique_sources:
            if pd.isna(source) or source == '':
                continue
                
            df_source = df[df['Source'] == source].copy()
            if df_source.empty:
                continue
            
            # Use mapped name or clean up the source name for tab
            tab_name = tab_name_map.get(source, source.replace(' ', '_')[:31])  # Excel tab name limit is 31 chars
            df_source.to_excel(writer, sheet_name=tab_name, index=False)
            format_worksheet(writer.sheets[tab_name], link_col_idx=6)
            tabs_created.append(f"{tab_name} ({len(df_source)})")
    
    print(f"\n✅ Exported {len(df)} jobs to: {filename}")
    tabs_list = [f"All Jobs ({len(df)})"] + tabs_created_top + tabs_created
    print(f"   Tabs: {', '.join(tabs_list)}")
    return filename
