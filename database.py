import sqlite3
import os
import pandas as pd
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
            last_seen TEXT
        )
    ''')
    
    # Check if last_seen column exists (for migration)
    try:
        c.execute("SELECT last_seen FROM jobs LIMIT 1")
    except sqlite3.OperationalError:
        print("Adding 'last_seen' column to database...")
        c.execute("ALTER TABLE jobs ADD COLUMN last_seen TEXT")
    
    conn.commit()
    conn.close()

def save_job(job_data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Use job link or title+location as a unique ID if real ID isn't available
    # For PG&E, the link usually contains a numeric ID at the end
    job_id = job_data['link'].split('/')[-1] if '/' in job_data['link'] else job_data['link']
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        c.execute('''
            INSERT INTO jobs (id, title, link, location, date_posted, description, status, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, 'new', ?)
        ''', (
            job_id,
            job_data['title'],
            job_data['link'],
            job_data['location'],
            job_data.get('date_posted', 'N/A'),
            job_data.get('description', ''),
            now
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
    """Export all jobs to an Excel file with clickable links and priority sorting.
    Uses a master file that gets overwritten each time for a single source of truth."""
    if filename is None:
        filename = "pge_jobs_master.xlsx"  # Single master file, overwrites each time
    
    conn = sqlite3.connect(DB_NAME)
    
    # Get ALL jobs from database (deduplicated by link in DB), ordered by score (highest first), then by title
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
            last_seen
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
    
    # Reorder columns for better readability
    column_order = ['Priority', 'match_score', 'title', 'location', 'link', 
                   'missing_skills', 'analysis', 'date_posted', 'last_seen', 'status']
    df = df[column_order]
    
    # Rename columns for cleaner Excel output
    df.columns = ['Priority', 'Score', 'Job Title', 'Location', 'Apply Link', 
                  'Missing Skills', 'AI Analysis', 'Date Posted', 'Last Seen (Active)', 'Status']
    
    # Create Excel writer with formatting
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='All Jobs', index=False)
        
        # Get the workbook and worksheet
        workbook = writer.book
        worksheet = writer.sheets['All Jobs']
        
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
        
        # Make links clickable (Excel will auto-detect URLs)
        from openpyxl.styles import Font
        link_font = Font(color="0563C1", underline="single")
        
        # Find the link column and format it
        for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row):
            link_cell = row[4]  # Column E (Apply Link) - Index 4
            if link_cell.value and isinstance(link_cell.value, str) and link_cell.value.startswith('http'):
                link_cell.font = link_font
                link_cell.hyperlink = link_cell.value
        
        # Format header row
        from openpyxl.styles import Font, PatternFill, Alignment
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        
        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
    
    print(f"\n✅ Exported {len(df)} jobs to: {filename}")
    print(f"   (Master file updated - all jobs sorted by score, deduplicated)")
    return filename
