import streamlit as st
import pandas as pd
import os
import yaml
import subprocess
import plotly.express as px
from pathlib import Path

# FORCE ABSOLUTE PATH LOCK
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DATA_FILE = PROJECT_ROOT / "data" / "jobs_data.parquet"
SKILL_FILE = PROJECT_ROOT / "data" / "skill_analysis.parquet"
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"

JOB_GROUPS = {
    "IT & Data": ["Data Analyst", "Data Engineer", "Machine Learning Engineer", "Software Engineer"],
    "Finance": ["Accountant", "Financial Analyst", "Auditor"],
    "Marketing": ["SEO Specialist", "Content Strategist"]
}

def run_step(script_name):
    script_path = str(CURRENT_DIR / script_name)
    # Using 'python' instead of 'python3' to match standard venv environments
    return subprocess.run(["python", script_path], capture_output=True, text=True)

st.set_page_config(page_title="Market Skill Discovery", layout="wide")
st.title("🎯 Targeted Market Skill Discovery")

col_a, col_b = st.columns(2)
with col_a:
    selected_group = st.selectbox("Select Job Group:", options=list(JOB_GROUPS.keys()))
with col_b:
    selected_title = st.selectbox("Select Job Title:", options=JOB_GROUPS[selected_group])

if st.button(f"🚀 Refresh Market Data for {selected_title}"):
    st.cache_data.clear()
    with st.status(f"Running Absolute Path Sync...") as status:
        # Update Config
        with open(CONFIG_FILE, 'r') as f:
            conf = yaml.safe_load(f)
        conf['search']['job_title'] = selected_title
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(conf, f)

        st.write("Step 1: Extracting...")
        run_step("api_connector.py")
        
        st.write("Step 2: Analyzing...")
        run_step("skill_analyzer.py")
        
        status.update(label="Complete!", state="complete")
    st.rerun()

# --- VALIDATION VIEW ---
if DATA_FILE.exists():
    df_jobs = pd.read_parquet(DATA_FILE)
    df_skills = pd.read_parquet(SKILL_FILE)
    
    col_chart, col_stats = st.columns([1.2, 0.8])
    with col_chart:
        st.subheader(f"Results for: {selected_title}")
        # Filter out 0s to see if the analyzer is working
        plot_df = df_skills[df_skills['Count'] > 0].sort_values('Count', ascending=True)
        if not plot_df.empty:
            fig = px.bar(plot_df, x='Count', y='Skill', orientation='h', color='Count', template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Analyzer found 0 matches. Check description quality.")

    with col_stats:
        st.subheader("Market Stats")
        st.metric("Rows in Parquet", f"{len(df_jobs)}")
        st.write("**Top Companies (Current File)**")
        st.table(df_jobs['company'].value_counts().head(5))