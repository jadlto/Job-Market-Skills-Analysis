import sys
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import subprocess
import yaml
from api_connector import fetch_market_data

# --- PATHS ---
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
PROCESSED_FILE = PROJECT_ROOT / "data" / "processed_market_data.parquet"
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"

st.set_page_config(page_title="Market Skill Discovery", layout="wide")

st.title("🎯 Targeted Market Skill Discovery")

# --- JOB TITLE INPUT ---
job_title = st.text_input("Enter a job title to analyze:", placeholder="e.g. Data Analyst, Software Engineer")

if st.button("🚀 Fetch & Analyze"):
    if not job_title.strip():
        st.warning("Please enter a job title first.")
    else:
        # Write job title to config
        with open(CONFIG_FILE, 'r') as f:
            config = yaml.safe_load(f)
        config['search']['job_title'] = job_title.strip()
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(config, f)

        with st.status(f"Running pipeline for '{job_title}'...") as status:
            # ✅ FIX: block until pipeline fully completes before rerunning
            result = subprocess.run(
                [sys.executable, str(CURRENT_DIR / "run_pipeline.py")],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                status.update(label="❌ Pipeline failed!", state="error")
                st.code(result.stderr)
                st.stop()
            else:
                status.update(label="✅ Done!", state="complete")

        st.rerun()

st.divider()

# --- LOAD TRANSFORMED DATA ---
@st.cache_data
def load_processed_data(last_modified: float):
    if not PROCESSED_FILE.exists():
        return pd.DataFrame()
    return pd.read_parquet(PROCESSED_FILE)

mtime = PROCESSED_FILE.stat().st_mtime if PROCESSED_FILE.exists() else 0
df = load_processed_data(mtime)

# --- DYNAMIC DROPDOWN ---
if not df.empty:
    categories = ["-- Select a Role --"] + sorted(df['clean_category'].unique())
    selected_role = st.selectbox("Select Classified Role:", options=categories)
    if selected_role == "-- Select a Role --":
        selected_role = None
else:
    st.info("Enter a job title above and click Fetch & Analyze to get started.")
    selected_role = None

st.divider()

# --- VISUALIZATION ---
if selected_role and not df.empty:
    role_df = df[df['clean_category'] == selected_role]

    st.subheader(f"Market Insights: {selected_role}")

    col_chart, col_stats = st.columns([1.3, 0.7])

    with col_chart:
        all_skills = [skill for sublist in role_df['found_skills'] for skill in sublist]
        skill_counts = pd.Series(all_skills).value_counts().reset_index()
        skill_counts.columns = ['Skill', 'Count']

        if skill_counts.empty:
            st.info("No skills found for this category.")
        else:
            fig = px.bar(
                skill_counts.head(15).sort_values('Count'),
                x='Count', y='Skill', orientation='h',
                template="plotly_dark", color='Count'
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_stats:
        st.metric("Total Listings in Category", len(role_df))
        st.write("**Top Companies**")
        top_co = role_df['company'].value_counts().head(10).reset_index()
        st.dataframe(top_co, use_container_width=True, hide_index=True)