import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
from pathlib import Path
import yaml
import os
import subprocess

# --- PATHS ---
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DB_FILE = PROJECT_ROOT / "data" / "market_data.duckdb"
SKILL_FILE = PROJECT_ROOT / "data" / "skill_analysis.parquet"
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"

# --- 1. COMPREHENSIVE JOB MAPPING ---
# Add any title here to make it appear in the dropdown instantly
JOB_MAP = {
    # --- FINANCE & BUSINESS ---
    "Financial Analyst": "Finance",
    "Investment Banker": "Finance",
    "Accountant": "Finance",
    "Portfolio Manager": "Finance",
    "Business Analyst": "Product & Ops",
    "Product Manager": "Product & Ops",
    "Project Manager": "Product & Ops",
    "Operations Manager": "Product & Ops",
    
    # --- DATA & AI ---
    "Data Analyst": "IT & Data",
    "Data Engineer": "IT & Data",
    "Data Scientist": "IT & Data",
    "ML Engineer": "AI & Research",
    "AI Architect": "AI & Research",
    "Database Administrator": "IT & Data",
    "Analytics Manager": "IT & Data",
    
    # --- ENGINEERING & DEV ---
    "Software Engineer": "Engineering",
    "Frontend Developer": "Engineering",
    "Backend Developer": "Engineering",
    "Fullstack Engineer": "Engineering",
    "DevOps Engineer": "Engineering",
    "Cloud Architect": "Engineering",
    "Site Reliability Engineer": "Engineering",
    "Mobile Developer": "Engineering",
    
    # --- SECURITY ---
    "Cybersecurity Analyst": "Security",
    "Security Engineer": "Security",
    "Penetration Tester": "Security",
    "SOC Analyst": "Security",
    
    # --- MARKETING & SALES ---
    "Marketing Analyst": "Marketing",
    "SEO Specialist": "Marketing",
    "Digital Strategist": "Marketing",
    "Sales Operations": "Sales",
    "Account Executive": "Sales"
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
        # Update config.yaml
        with open(CONFIG_FILE, 'r') as f:
            conf = yaml.safe_load(f)
        conf['search']['job_title'] = selected_title
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(conf, f)

        try:
            from api_connector import fetch_market_data
            status.update(label="📡 Fetching live postings...")
            fetch_market_data()
            
            status.update(label="🧠 Analyzing skills...")
            # Trigger the analyzer subprocess
            subprocess.run(["python3", str(CURRENT_DIR / "skill_analyzer.py")], capture_output=True)
            
            st.session_state.has_run = True
            status.update(label="✅ Success!", state="complete")
        except Exception as e:
            st.error(f"Pipeline failed: {e}")
            
    st.rerun()

st.divider()

# --- 3. BLANK STATE ---
if not st.session_state.has_run:
    st.info("👋 Choose a title from the expanded list and hit 'Refresh'.")
    st.stop()

# --- 4. VISUALIZATION ---
if DB_FILE.exists():
    with duckdb.connect(str(DB_FILE), read_only=True) as con:
        try:
            job_count = con.execute("SELECT count(*) FROM jobs").fetchone()[0]
            
            if job_count > 0:
                current_group = JOB_MAP[selected_title]
                st.subheader(f"Demand Analysis: {selected_title} ({current_group})")
                
                c1, c2 = st.columns([1.3, 0.7])
                with c1:
                    if SKILL_FILE.exists():
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
                    st.metric("Jobs Analyzed", job_count)
                    st.write("**Top Companies**")
                    top_df = con.execute("SELECT company, count(*) as Postings FROM jobs GROUP BY company ORDER BY Postings DESC LIMIT 10").df()
                    st.dataframe(top_df, use_container_width=True, hide_index=True)
            else:
                st.warning("No data returned for this search. The API might have zero matches for this specific term right now.")
        except Exception as e:
            st.error(f"Database error: {e}")