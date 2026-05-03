import sys
import yaml
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import subprocess

# --- PATHS ---
CURRENT_DIR = Path(__file__).parent.resolve()
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

# ✅ Track whether the user has fetched data in this session
if "data_ready" not in st.session_state:
    st.session_state.data_ready = False

# --- JOB TITLE INPUT ---
job_title = st.text_input("Enter a job title to analyze:", placeholder="e.g. Data Analyst, Software Engineer")

if st.button("🚀 Fetch & Analyze"):
    if not job_title.strip():
        st.warning("Please enter a job title first.")
    else:
        with open(CONFIG_FILE, 'r') as f:
            config = yaml.safe_load(f)
        config['search']['job_title'] = job_title.strip()
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(config, f)

        with st.status(f"Running pipeline for '{job_title}'...") as status:
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
                st.session_state.data_ready = True  # ✅ only set after successful run
                status.update(label="✅ Done!", state="complete")
        st.rerun()

st.divider()

# ✅ Only load and show data if the user has fetched in this session
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
skill_type = st.radio(
    "Skill type:",
    options=["Hard Skills", "Soft Skills"],
    horizontal=True
)

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
            st.plotly_chart(fig, use_container_width=True)

    with col_stats:
        st.metric("Total Listings", len(df))
        st.write("**Top Companies**")
        top_co = df['company'].value_counts().head(10).reset_index()
        st.dataframe(top_co, use_container_width=True, hide_index=True)