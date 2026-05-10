import re
import subprocess
import sys
from pathlib import Path

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

import streamlit as st
import pandas as pd
import plotly.express as px

sys.path.insert(0, str(_SCRIPT.parent))

from api_connector import fetch_market_data
from skill_analyzer import analyze

PROJECT_ROOT = _SCRIPT.parent.parent
PROCESSED_FILE = PROJECT_ROOT / "data" / "processed_market_data.parquet"

# Optional filter: phrases whose tokens overlap this set (not a full taxonomy).
_SOFT_LEXICON = frozenset(
    """
    communication leadership negotiation collaboration teamwork presentation
    interpersonal mentoring coaching empathy listening writing speaking stakeholder
    relationship persuasion influence facilitation adaptability diplomacy consensus
    collaborative organizational verbal oral written multicultural diversity inclusion
    """.split()
)


def _phrase_soft_leaning(phrase: str) -> bool:
    tokens = set(re.findall(r"[a-z]+", phrase.lower()))
    return bool(tokens & _SOFT_LEXICON)


st.set_page_config(page_title="Market Skill Discovery", layout="wide")
st.title("🎯 Targeted Market Skill Discovery")

job_title = st.text_input("Enter a job title to analyze:", placeholder="e.g. Data Analyst, Software Engineer")

if st.button("🚀 Fetch & Analyze"):
    if not job_title.strip():
        st.warning("Please enter a job title first.")
    else:
        with st.status(f"Running pipeline for '{job_title}'...") as status:
            try:
                status.write("Fetching jobs...")
                ok, fetch_err = fetch_market_data(job_title.strip())
                if not ok:
                    status.update(label="Pipeline failed", state="error")
                    if fetch_err == "missing_keys":
                        st.error(
                            "**The app cannot read your Adzuna keys.** "
                            "Streamlit Cloud Secrets must be **valid TOML** — not `.env` style. "
                            "Lines like `ADZUNA_APP_ID=abc123` **fail parsing**, so keys never reach the app.\n\n"
                            "Use **spaces around `=`** and **double quotes** around each value:\n\n"
                            "```toml\n"
                            "ADZUNA_APP_ID = \"paste_your_app_id_here\"\n"
                            "ADZUNA_APP_KEY = \"paste_your_app_key_here\"\n"
                            "```\n\n"
                            "In [Streamlit Cloud](https://share.streamlit.io): **Manage app** → **Settings** → "
                            "**Secrets** → **Save** → **Reboot**. Keys: [developer.adzuna.com](https://developer.adzuna.com)."
                        )
                    elif fetch_err == "empty_results":
                        st.warning(
                            "The API returned no job postings for that title. "
                            "Try another keyword or confirm your Adzuna keys are valid."
                        )
                    else:
                        st.error(f"Fetch failed ({fetch_err}). Check logs.")
                    st.stop()

                status.write("Analyzing skills...")
                if not analyze():
                    raise RuntimeError(
                        "Could not analyze jobs. Ensure listings were downloaded."
                    )

                status.update(label="Done", state="complete")
            except Exception as e:
                status.update(label="Pipeline failed", state="error")
                st.exception(e)
                st.stop()

        st.rerun()

st.divider()


@st.cache_data
def load_processed_data(last_modified: float):
    if not PROCESSED_FILE.exists():
        return pd.DataFrame()
    return pd.read_parquet(PROCESSED_FILE)


mtime = PROCESSED_FILE.stat().st_mtime if PROCESSED_FILE.exists() else 0
df = load_processed_data(mtime)

if df.empty:
    st.info(
        "Enter a job title and click **Fetch & Analyze**. "
        "On hosted deployments, results disappear after a restart—run the pipeline again."
    )
    st.stop()

view = st.radio(
    "Phrase view:",
    options=["All phrases (TF-IDF)", "Soft-skill leaning (keyword filter)"],
    horizontal=True,
)

st.divider()

st.subheader(f"Market Insights: {job_title}")
st.caption(
    "Phrases come from **TF-IDF** on job descriptions in this batch (unigrams + bigrams). "
    "They are not a fixed dictionary — they reflect what text is most distinctive in these postings."
)

col_chart, col_stats = st.columns([1.3, 0.7])

with col_chart:
    all_skills = [
        skill
        for sublist in df["found_skills"]
        for skill in sublist
        if view == "All phrases (TF-IDF)" or _phrase_soft_leaning(skill)
    ]

    skill_counts = pd.Series(all_skills).value_counts().reset_index()
    skill_counts.columns = ["Skill", "Count"]

    if skill_counts.empty:
        st.info(
            "No phrases matched this view. Try **All phrases**, or run fetch again with more listings."
        )
    else:
        chart_title = (
            "Top phrases (TF-IDF)"
            if view == "All phrases (TF-IDF)"
            else "Soft-skill leaning phrases"
        )
        fig = px.bar(
            skill_counts.head(15).sort_values("Count"),
            x="Count",
            y="Skill",
            orientation="h",
            template="plotly_dark",
            color="Count",
            title=chart_title,
        )
        st.plotly_chart(fig, width="stretch")

with col_stats:
    st.metric("Total Listings", len(df))
    st.write("**Top Companies**")
    top_co = df["company"].value_counts().head(10).reset_index()
    st.dataframe(top_co, width="stretch", hide_index=True)
