import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import subprocess

# --- PATHS ---
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
PROCESSED_FILE = PROJECT_ROOT / "data" / "processed_market_data.parquet"

st.set_page_config(page_title="Market Skill Discovery", layout="wide")

# Initialize state
if "has_run" not in st.session_state:
    st.session_state.has_run = False

st.title("🎯 Targeted Market Skill Discovery")

# --- LOAD TRANSFORMED DATA ---
@st.cache_data
def load_processed_data():
    if not PROCESSED_FILE.exists():
        return pd.DataFrame()
    return pd.read_parquet(PROCESSED_FILE)

df = load_processed_data()

# --- DYNAMIC DROPDOWN FROM CLASSIFIED DATA ---
if not df.empty:
    # Only show categories that aren't "Other"
    categories = sorted(df[df['clean_category'] != 'Other']['clean_category'].unique())
    selected_role = st.selectbox("Select Classified Role:", options=categories)
else:
    st.warning("No processed data found. Please run a fetch/analyze cycle.")
    selected_role = None

if st.button("🚀 Refresh Pipeline"):
    with st.status("Running Transformation Pipeline...") as status:
        # 1. Fetch raw (unchanged)
        from api_connector import fetch_market_data
        fetch_market_data()
        # 2. Transform (Skill Analyzer)
        subprocess.run(["python3", str(CURRENT_DIR / "skill_analyzer.py")])
        st.cache_data.clear()
        st.session_state.has_run = True
    st.rerun()

st.divider()

# --- VISUALIZATION OF TRANSFORMED DATA ---
if selected_role and not df.empty:
    # Filter data by the classified category
    role_df = df[df['clean_category'] == selected_role]
    
    st.subheader(f"Market Insights: {selected_role}")
    
    col_chart, col_stats = st.columns([1.3, 0.7])
    
    with col_chart:
        # Explode the skills list to count them
        all_skills = [skill for sublist in role_df['found_skills'] for skill in sublist]
        skill_counts = pd.Series(all_skills).value_counts().reset_index()
        skill_counts.columns = ['Skill', 'Count']
        
        fig = px.bar(skill_counts.head(15).sort_values('Count'), 
                     x='Count', y='Skill', orientation='h', 
                     template="plotly_dark", color='Count')
        st.plotly_chart(fig, use_container_width=True)

    with col_stats:
        st.metric("Total Listings in Category", len(role_df))
        st.write("**Top Companies**")
        top_co = role_df['company'].value_counts().head(10).reset_index()
        st.dataframe(top_co, use_container_width=True, hide_index=True)