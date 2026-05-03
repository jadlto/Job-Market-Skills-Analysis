import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
from pathlib import Path
import yaml
import os
import subprocess # Needed to trigger the analyzer

# --- PATHS ---
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DB_FILE = PROJECT_ROOT / "data" / "market_data.duckdb"
SKILL_FILE = PROJECT_ROOT / "data" / "skill_analysis.parquet"
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"

# --- 1. EXPANDED MASTER LIST ---
JOB_MAP = {
    "Financial Analyst": "Finance",
    "Investment Banker": "Finance",
    "Data Analyst": "IT & Data",
    "Data Engineer": "IT & Data",
    "Data Scientist": "IT & Data",
    "ML Engineer": "AI & Research",
    "Software Engineer": "Engineering",
    "DevOps Engineer": "Engineering",
    "Cybersecurity Analyst": "Security",
    "Marketing Analyst": "Marketing",
    "Business Analyst": "Product",
    "Sales Operations": "Sales"
}

st.set_page_config(page_title="Market Skill Discovery", layout="wide")

if "has_run" not in st.session_state:
    st.session_state.has_run = False

st.title("🎯 Targeted Market Skill Discovery")

# --- 2. THE SINGLE DROPDOWN ---
selected_title = st.selectbox(
    "Select Job Title:", 
    options=sorted(list(JOB_MAP.keys()))
)

if st.button("🚀 Refresh Market Data"):
    with st.status(f"Processing {selected_title}...") as status:
        # 1. Update config.yaml
        with open(CONFIG_FILE, 'r') as f:
            conf = yaml.safe_load(f)
        conf['search']['job_title'] = selected_title
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(conf, f)

        try:
            # 2. Run API Connector (Imported function)
            from api_connector import fetch_market_data
            status.update(label="📡 Fetching live postings...")
            fetch_market_data()
            
            # 3. Run Skill Analyzer (Via Subprocess to ensure fresh state)
            status.update(label="🧠 Analyzing skills...")
            # This is the "secret sauce" - it runs your second script automatically
            subprocess.run(["python3", str(CURRENT_DIR / "skill_analyzer.py")], capture_output=True)
            
            st.session_state.has_run = True
            status.update(label="✅ Success! Dashboard updated.", state="complete")
        except Exception as e:
            st.error(f"Pipeline failed: {e}")
            
    st.rerun()

st.divider()

# --- 3. BLANK STATE ---
if not st.session_state.has_run:
    st.info("👋 Select a title and hit 'Refresh' to begin.")
    st.stop()

# --- 4. VISUALIZATION ---
if DB_FILE.exists():
    with duckdb.connect(str(DB_FILE), read_only=True) as con:
        row_count = con.execute("SELECT count(*) FROM jobs").fetchone()[0]
        
        if row_count > 0:
            st.subheader(f"Analysis for {selected_title}")
            
            c1, c2 = st.columns([1.3, 0.7])
            with c1:
                if SKILL_FILE.exists():
                    # We read the file freshly here
                    df_skills = pd.read_parquet(SKILL_FILE)
                    fig = px.bar(
                        df_skills.sort_values('Count'), 
                        x='Count', y='Skill', 
                        orientation='h', 
                        template="plotly_dark", 
                        color='Count',
                        color_continuous_scale='Viridis'
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            with c2:
                st.metric("Jobs Found", row_count)
                st.write("**Top Companies**")
                top_df = con.execute("SELECT company, count(*) as Postings FROM jobs GROUP BY company ORDER BY Postings DESC LIMIT 10").df()
                st.dataframe(top_df, use_container_width=True, hide_index=True)