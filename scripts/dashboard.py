import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
from pathlib import Path
import yaml
import subprocess

CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DB_FILE = PROJECT_ROOT / "data" / "market_data.duckdb"
SKILL_FILE = PROJECT_ROOT / "data" / "skill_analysis.parquet"
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"

def run_step(script_name):
    script_path = str(CURRENT_DIR / script_name)
    return subprocess.run(["python", script_path], capture_output=True, text=True)

st.set_page_config(page_title="Market Skill Discovery", layout="wide")
st.title("🎯 Targeted Market Skill Discovery")

# UI Logic
col_a, col_b = st.columns(2)
with col_a:
    selected_group = st.selectbox("Select Job Group:", ["IT & Data"])
with col_b:
    selected_title = st.selectbox("Select Job Title:", ["Data Analyst", "Data Engineer"])

if st.button(f"🚀 Refresh Market Data"):
    st.cache_data.clear()
    with st.status("DuckDB Refreshing...") as status:
        with open(CONFIG_FILE, 'r') as f:
            conf = yaml.safe_load(f)
        conf['search']['job_title'] = selected_title
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(conf, f)

        run_step("api_connector.py")
        run_step("skill_analyzer.py")
        status.update(label="Database Updated!", state="complete")
    st.rerun()

# Display Logic
if DB_FILE.exists():
    con = duckdb.connect(str(DB_FILE))
    
    col_chart, col_stats = st.columns([1.2, 0.8])
    
    with col_chart:
        st.subheader(f"Skills Found: {selected_title}")
        if SKILL_FILE.exists():
            df_skills = pd.read_parquet(SKILL_FILE)
            plot_df = df_skills[df_skills['Count'] > 0].sort_values('Count', ascending=True)
            fig = px.bar(plot_df, x='Count', y='Skill', orientation='h', color='Count', template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

    with col_stats:
        st.subheader("Market Stats")
        # Direct SQL count
        total = con.execute("SELECT count(*) FROM jobs").fetchone()[0]
        st.metric("Total Rows in DB", total)
        
        st.write("**Top Companies (Cleaned)**")
        # Clean table without JSON strings
        top_co = con.execute("SELECT company, count(*) as Postings FROM jobs GROUP BY company ORDER BY Postings DESC LIMIT 8").df()
        st.table(top_co)
    
    con.close()