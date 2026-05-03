import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
from pathlib import Path
import yaml
from api_connector import fetch_market_data

# --- PATHS ---
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DB_FILE = PROJECT_ROOT / "data" / "market_data.duckdb"
SKILL_FILE = PROJECT_ROOT / "data" / "skill_analysis.parquet"
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"

# --- 1. MASTER LIST (One source for everything) ---
JOB_MAP = {
    "Data Analyst": "IT & Data",
    "Data Engineer": "IT & Data",
    "Data Scientist": "IT & Data",
    "ML Engineer": "AI & Research",
    "Software Engineer": "Engineering",
    "DevOps Engineer": "Engineering",
    "Cybersecurity Analyst": "Security",
    "Marketing Analyst": "Marketing",
    "Product Manager": "Product",
    "Business Analyst": "Product",
    "Financial Analyst": "Finance"
}

st.set_page_config(page_title="Market Skill Discovery", layout="wide")

# Handle the "Blank Start" logic
if "has_run" not in st.session_state:
    st.session_state.has_run = False

st.title("🎯 Targeted Market Skill Discovery")

# --- 2. THE ONLY DROPDOWN ---
# This replaces the two-dropdown system entirely.
selected_title = st.selectbox(
    "Select Job Title:", 
    options=sorted(list(JOB_MAP.keys())),
    help="Choose a title to fetch live market data."
)

if st.button("🚀 Refresh Market Data"):
    with st.status(f"Fetching {selected_title} jobs...") as status:
        # Update config.yaml
        with open(CONFIG_FILE, 'r') as f:
            conf = yaml.safe_load(f)
        conf['search']['job_title'] = selected_title
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(conf, f)

        try:
            fetch_market_data()
            # run_skill_analysis() # Call your analyzer here
            st.session_state.has_run = True
            status.update(label="Sync Complete!", state="complete")
        except Exception as e:
            st.error(f"Sync failed: {e}")
    st.rerun()

st.divider()

# --- 3. BLANK STATE LOGIC ---
if not st.session_state.has_run:
    st.info("👋 Select a title and hit 'Refresh' to see the analysis.")
    st.stop()

# --- 4. DATA VISUALIZATION ---
if DB_FILE.exists():
    with duckdb.connect(str(DB_FILE), read_only=True) as con:
        row_count = con.execute("SELECT count(*) FROM jobs").fetchone()[0]
        
        if row_count > 0:
            current_group = JOB_MAP[selected_title]
            st.subheader(f"Results for {selected_title} in {current_group}")
            
            c1, c2 = st.columns([1.3, 0.7])
            with c1:
                if SKILL_FILE.exists():
                    df_skills = pd.read_parquet(SKILL_FILE)
                    fig = px.bar(df_skills.sort_values('Count'), x='Count', y='Skill', 
                                orientation='h', template="plotly_dark", color='Count')
                    st.plotly_chart(fig, use_container_width=True)
            with c2:
                st.metric("Total Jobs Found", row_count)
                st.write("**Top Companies**")
                top_df = con.execute("SELECT company, count(*) as Postings FROM jobs GROUP BY company ORDER BY Postings DESC LIMIT 10").df()
                st.dataframe(top_df, use_container_width=True, hide_index=True)