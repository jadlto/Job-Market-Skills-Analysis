import subprocess
import sys
from pathlib import Path

# IDE "Run" often executes `python dashboard.py`; interactive widgets need Streamlit's server.
_SCRIPT = Path(__file__).resolve()

if __name__ == "__main__":
    import streamlit as st
    from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx

    if get_script_run_ctx() is None:
        raise SystemExit(
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    str(_SCRIPT),
                    *sys.argv[1:],
                ],
                cwd=str(_SCRIPT.parent),
            ).returncode
        )

import yaml
import streamlit as st
import pandas as pd
import plotly.express as px

# Make sure scripts/ is on path so imports work on cloud and when cwd differs
sys.path.insert(0, str(_SCRIPT.parent))

from api_connector import fetch_market_data
from skill_analyzer import analyze

# --- PATHS ---
CURRENT_DIR = _SCRIPT.parent
PROJECT_ROOT = CURRENT_DIR.parent
PROCESSED_FILE = PROJECT_ROOT / "data" / "processed_market_data.parquet"
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"

# --- SKILL CLASSIFICATION ---
HARD_SKILLS = {
    "Python", "Sql", "R", "Java", "Scala", "Javascript", "Typescript", "C++", "C#",
    "Bash", "Shell", "Go", "Rust", "Matlab", "Sas", "Vba",
    "Excel", "Tableau", "Power Bi", "Looker", "Qlik", "Dax", "Pandas", "Numpy",
    "Scipy", "Matplotlib", "Seaborn", "Plotly", "Dbt", "Airflow", "Spark",
    "Hadoop", "Kafka", "Duckdb", "Databricks", "Snowflake", "Redshift", "Bigquery",
    "Etl", "Elt", "Data Warehouse", "Data Lake", "Data Pipeline", "Data Modeling",
    "Machine Learning", "Deep Learning", "Nlp", "Computer Vision", "Scikit-Learn",
    "Tensorflow", "Pytorch", "Keras", "Xgboost", "Lightgbm", "Mlflow", "Hugging Face",
    "Llm", "Generative Ai", "Reinforcement Learning", "A/B Testing", "Statistics",
    "Aws", "Azure", "Gcp", "Google Cloud", "Docker", "Kubernetes", "Terraform",
    "Ci/Cd", "Git", "Github", "Gitlab", "Linux", "Rest Api", "Graphql",
    "Postgresql", "Mysql", "Mongodb", "Redis", "Elasticsearch", "Oracle", "Sql Server",
    "Sqlite", "Cassandra", "Dynamodb",
    "Gaap", "Ifrs", "Cpa", "Cfa", "Financial Modeling", "Financial Reporting",
    "Fp&A", "Budgeting", "Forecasting", "Variance Analysis", "Reconciliation",
    "Accounts Payable", "Accounts Receivable", "Quickbooks", "Sap", "Netsuite",
    "Vlookup", "Pivot Tables",
    "Jira", "Confluence", "Agile", "Scrum", "Kanban", "Erp", "Six Sigma", "Lean",
}

SOFT_SKILLS = {
    "Communication", "Leadership", "Problem Solving", "Critical Thinking",
    "Project Management", "Cross Functional", "Stakeholder Management",
    "Requirements Gathering", "Risk Management",
}

st.set_page_config(page_title="Market Skill Discovery", layout="wide")
st.title("🎯 Targeted Market Skill Discovery")

if "data_ready" not in st.session_state:
    st.session_state.data_ready = False

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
            try:
                # ✅ Call functions directly — no subprocess
                status.write("📡 Fetching jobs...")
                if not fetch_market_data():
                    raise RuntimeError(
                        "Could not fetch job listings. Check API keys and config."
                    )

                status.write("⚙️ Analyzing skills...")
                if not analyze():
                    raise RuntimeError(
                        "Could not analyze jobs. Ensure listings were downloaded."
                    )

                st.session_state.data_ready = True
                status.update(label="✅ Done!", state="complete")
            except Exception as e:
                status.update(label="❌ Pipeline failed!", state="error")
                st.exception(e)
                st.stop()

        st.rerun()

st.divider()

if not st.session_state.data_ready:
    st.info("Enter a job title above and click **Fetch & Analyze** to get started.")
    st.stop()

# --- LOAD DATA ---
@st.cache_data
def load_processed_data(last_modified: float):
    if not PROCESSED_FILE.exists():
        return pd.DataFrame()
    return pd.read_parquet(PROCESSED_FILE)

mtime = PROCESSED_FILE.stat().st_mtime if PROCESSED_FILE.exists() else 0
df = load_processed_data(mtime)

# --- SKILL TYPE TOGGLE ---
skill_type = st.radio("Skill type:", options=["Hard Skills", "Soft Skills"], horizontal=True)

st.divider()

# --- VISUALIZATION ---
if not df.empty:
    st.subheader(f"Market Insights: {job_title}")

    col_chart, col_stats = st.columns([1.3, 0.7])

    with col_chart:
        skill_set = HARD_SKILLS if skill_type == "Hard Skills" else SOFT_SKILLS
        all_skills = [
            skill for sublist in df['found_skills']
            for skill in sublist
            if skill in skill_set
        ]

        skill_counts = pd.Series(all_skills).value_counts().reset_index()
        skill_counts.columns = ['Skill', 'Count']

        if skill_counts.empty:
            st.info(f"No {skill_type.lower()} found for this search.")
        else:
            fig = px.bar(
                skill_counts.head(15).sort_values('Count'),
                x='Count', y='Skill', orientation='h',
                template="plotly_dark", color='Count',
                title=f"Top {skill_type}"
            )
            st.plotly_chart(fig, width="stretch")

    with col_stats:
        st.metric("Total Listings", len(df))
        st.write("**Top Companies**")
        top_co = df['company'].value_counts().head(10).reset_index()
        st.dataframe(top_co, width="stretch", hide_index=True)