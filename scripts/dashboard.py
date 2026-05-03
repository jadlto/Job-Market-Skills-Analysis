import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
from pathlib import Path
import yaml

# Import your script functions directly
from api_connector import fetch_market_data
# from skill_analyzer import run_analysis # Uncomment when ready

CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DB_FILE = PROJECT_ROOT / "data" / "market_data.duckdb"
SKILL_FILE = PROJECT_ROOT / "data" / "skill_analysis.parquet"
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"

st.set_page_config(page_title="Market Skill Discovery", layout="wide")
st.title("🎯 Targeted Market Skill Discovery")

# --- DYNAMIC DROPDOWN LOGIC ---
# 1. Load available titles from your config as defaults
with open(CONFIG_FILE, 'r') as f:
    conf = yaml.safe_load(f)
    
# 2. Get unique titles already in your DB to populate the list
db_titles = []
if DB_FILE.exists():
    with duckdb.connect(str(DB_FILE), read_only=True) as con:
        try:
            titles_df = con.execute("SELECT DISTINCT title FROM jobs LIMIT 100").df()
            db_titles = titles_df['title'].tolist()
        except:
            db_titles = ["Data Analyst", "Data Engineer", "Software Engineer"]

# Combine and clean list for the dropdown
available_titles = sorted(list(set(db_titles + ["Data Analyst", "Data Engineer"])))

col_a, col_b = st.columns(2)
with col_a:
    # You can expand groups here or pull from config
    selected_group = st.selectbox("Select Job Group:", ["IT & Data", "Engineering", "Marketing"])
with col_b:
    # This now uses the dynamic list from the DB
    selected_title = st.selectbox("Select Job Title:", available_titles)

if st.button(f"🚀 Refresh Market Data"):
    with st.status(f"Updating market data for {selected_title}...") as status:
        # Update config with the UI selection
        conf['search']['job_title'] = selected_title
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(conf, f)

        try:
            fetch_market_data()
            # run_analysis() 
            status.update(label="Sync Complete!", state="complete")
        except Exception as e:
            st.error(f"Execution failed: {e}")
            status.update(label="Failed", state="error")
    st.rerun()

# --- DATABASE VIEW ---
if DB_FILE.exists():
    with duckdb.connect(str(DB_FILE), read_only=True) as con:
        try:
            res = con.execute("SELECT count(*) FROM jobs").fetchone()
            row_count = res[0] if res else 0
            
            if row_count > 0:
                col_chart, col_stats = st.columns([1.2, 0.8])
                with col_chart:
                    st.subheader(f"Analysis: {selected_title}")
                    if SKILL_FILE.exists():
                        df_skills = pd.read_parquet(SKILL_FILE)
                        fig = px.bar(df_skills.sort_values('Count'), x='Count', y='Skill', 
                                    orientation='h', template="plotly_dark", color='Count')
                        st.plotly_chart(fig, width='stretch')
                
                with col_stats:
                    st.metric("Jobs Scanned", row_count)
                    st.write("**Top Hiring Companies**")
                    top_co = con.execute("SELECT company, count(*) as Postings FROM jobs GROUP BY company ORDER BY Postings DESC LIMIT 10").df()
                    st.dataframe(top_co, width='stretch', hide_index=True)
            else:
                st.warning("No data found for this specific title. Try hitting 'Refresh'.")
        except Exception as e:
            st.error(f"Table error: {e}")
else:
    st.info("👋 No database found. Hit Refresh to start.")