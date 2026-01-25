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

def get_new_jobs():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM jobs WHERE status = 'new'")
    rows = c.fetchall()
    conn.close()
    return rows

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
    """Get jobs that are new OR failed previous analysis (score 0)."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM jobs WHERE status = 'new' OR match_score = 0 OR match_score IS NULL")
    rows = c.fetchall()
    conn.close()
    return rows

def export_to_excel(filename=None):
    """Export all jobs to an Excel file with tabs per source.
    Creates: All Jobs, PG&E, SMUD, Kaiser tabs (tabs only created if jobs exist).
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
        print("No jobs to export.")
        return None
    
    # Add priority column based on score
    def get_priority(score):
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
    
    df['Priority'] = df['match_score'].apply(get_priority)
    
    # Reorder columns for better readability (include source)
    column_order = ['Priority', 'match_score', 'title', 'location', 'source', 'link', 
                   'missing_skills', 'analysis', 'date_posted', 'last_seen', 'status']
    df = df[column_order]
    
    # Rename columns for cleaner Excel output
    df.columns = ['Priority', 'Score', 'Job Title', 'Location', 'Source', 'Apply Link', 
                  'Missing Skills', 'AI Analysis', 'Date Posted', 'Last Seen (Active)', 'Status']
    
    # Create separate dataframes per source
    df_pge = df[df['Source'] == 'PG&E'].copy()
    df_smud = df[df['Source'] == 'SMUD'].copy()
    df_kaiser = df[df['Source'] == 'Kaiser Permanente'].copy()
    df_all = df.copy()
    
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
    
    # Create Excel writer with multiple sheets
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # Write All Jobs tab
        df_all.to_excel(writer, sheet_name='All Jobs', index=False)
        format_worksheet(writer.sheets['All Jobs'], link_col_idx=5)
        
        # Write PG&E tab (if any jobs exist)
        if not df_pge.empty:
            df_pge.to_excel(writer, sheet_name='PG&E', index=False)
            format_worksheet(writer.sheets['PG&E'], link_col_idx=5)
        
        # Write SMUD tab (if any jobs exist)
        if not df_smud.empty:
            df_smud.to_excel(writer, sheet_name='SMUD', index=False)
            format_worksheet(writer.sheets['SMUD'], link_col_idx=5)
        
        # Write Kaiser tab (if any jobs exist)
        if not df_kaiser.empty:
            df_kaiser.to_excel(writer, sheet_name='Kaiser', index=False)
            format_worksheet(writer.sheets['Kaiser'], link_col_idx=5)
    
    print(f"\n✅ Exported {len(df_all)} jobs to: {filename}")
    tabs_list = [f"All Jobs ({len(df_all)})"]
    if not df_pge.empty:
        tabs_list.append(f"PG&E ({len(df_pge)})")
    if not df_smud.empty:
        tabs_list.append(f"SMUD ({len(df_smud)})")
    if not df_kaiser.empty:
        tabs_list.append(f"Kaiser ({len(df_kaiser)})")
    print(f"   Tabs: {', '.join(tabs_list)}")
    return filename
