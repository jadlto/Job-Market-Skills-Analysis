import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
from pathlib import Path
import yaml
import subprocess

# --- PATHS ---
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DB_FILE = PROJECT_ROOT / "data" / "market_data.duckdb"
SKILL_FILE = PROJECT_ROOT / "data" / "skill_analysis.parquet"
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"

st.set_page_config(page_title="Market Skill Discovery", layout="wide")

# --- 1. DYNAMIC TITLE FETCHING ---
def get_available_titles():
    if not DB_FILE.exists():
        return ["Data Analyst", "Accountant", "Financial Analyst"] # Defaults
    
    with duckdb.connect(str(DB_FILE), read_only=True) as con:
        # Get unique titles, cleaning up common noise
        titles = con.execute("""
            SELECT DISTINCT title 
            FROM jobs 
            WHERE title IS NOT NULL 
            LIMIT 50
        """).df()['title'].tolist()
        return sorted(titles)

available_titles = get_available_titles()

if "has_run" not in st.session_state:
    st.session_state.has_run = False

st.title("🎯 Targeted Market Skill Discovery")

# --- 2. THE DYNAMIC DROPDOWN ---
# This now uses the actual list of jobs found in your database
selected_title = st.selectbox("Select Job Title from Results:", options=available_titles)

if st.button("🚀 Refresh & Re-Analyze"):
    with st.status(f"Processing {selected_title}...") as status:
        # Update config.yaml for the next fetch
        with open(CONFIG_FILE, 'r') as f:
            conf = yaml.safe_load(f)
        conf['search']['job_title'] = selected_title
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(conf, f)

        try:
            from api_connector import fetch_market_data
            status.update(label="📡 Fetching live postings...")
            fetch_market_data()
            
            status.update(label="🧠 Re-running Skill Analysis...")
            subprocess.run(["python3", str(CURRENT_DIR / "skill_analyzer.py")], capture_output=True)
            
            st.session_state.has_run = True
            status.update(label="✅ Success!", state="complete")
        except Exception as e:
            st.error(f"Pipeline failed: {e}")
    st.rerun()

st.divider()

# --- 3. DISPLAY RESULTS ---
if DB_FILE.exists():
    with duckdb.connect(str(DB_FILE), read_only=True) as con:
        # Filter stats for the specific selected title
        job_stats = con.execute("SELECT count(*) FROM jobs").fetchone()[0]
        
        if job_stats > 0:
            st.subheader(f"Analysis: {selected_title}")
            
            c1, c2 = st.columns([1.3, 0.7])
            with c1:
                if SKILL_FILE.exists():
                    df_skills = pd.read_parquet(SKILL_FILE)
                    # Show top 15 skills
                    df_plot = df_skills.sort_values('Count', ascending=True).tail(15)
                    fig = px.bar(df_plot, x='Count', y='Skill', orientation='h', 
                                template="plotly_dark", color='Count')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("No skill data. Check your keyword list in skill_analyzer.py!")
            
            with c2:
                st.metric("Total Listings", job_stats)
                st.write("**Hiring Entities**")
                top_df = con.execute("SELECT company, count(*) as Postings FROM jobs GROUP BY company ORDER BY Postings DESC LIMIT 10").df()
                st.dataframe(top_df, use_container_width=True, hide_index=True)