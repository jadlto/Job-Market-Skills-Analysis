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
from phrase_labels import categorize_phrase
from skill_analyzer import analyze

PROJECT_ROOT = _SCRIPT.parent.parent
PROCESSED_FILE = PROJECT_ROOT / "data" / "processed_market_data.parquet"
LAST_SEARCH_TITLE_FILE = PROJECT_ROOT / "data" / "last_search_job_title.txt"

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

skill_type = st.radio(
    "Skill type:",
    options=["Hard Skills", "Soft Skills"],
    horizontal=True,
)

st.divider()


def _insights_job_title() -> str:
    q = job_title.strip()
    if q:
        return q
    if LAST_SEARCH_TITLE_FILE.exists():
        return LAST_SEARCH_TITLE_FILE.read_text(encoding="utf-8").strip()
    return ""


_insights_q = _insights_job_title()
st.subheader(
    f"Market Insights: {_insights_q}" if _insights_q else "Market Insights"
)
st.caption(
    "Phrases come from **TF-IDF** (unigrams + bigrams), then a **small classifier** "
    "(hard vs soft vs non-relevant) trained on bundled examples — generic recruiting "
    "language is dropped as **non-relevant**. Lexicon rules apply only if the model fails."
)

col_chart, col_stats = st.columns([1.3, 0.7])

with col_chart:
    want = "soft" if skill_type == "Soft Skills" else "hard"
    all_skills = [
        skill
        for sublist in df["found_skills"]
        for skill in sublist
        if categorize_phrase(skill) == want
    ]

    skill_counts = pd.Series(all_skills).value_counts().reset_index()
    skill_counts.columns = ["Skill", "Count"]

    if skill_counts.empty:
        st.info(
            f"No **{skill_type.lower()}** matched after filtering. "
            "Try the other category, run **Fetch & Analyze** again, or try a different job title."
        )
    else:
        fig = px.bar(
            skill_counts.head(15).sort_values("Count"),
            x="Count",
            y="Skill",
            orientation="h",
            template="plotly_dark",
            color="Count",
            title=f"Top {skill_type} (TF-IDF + classifier)",
        )
        st.plotly_chart(fig, width="stretch")

with col_stats:
    st.metric("Total Listings", len(df))
    st.write("**Top Companies**")
    top_co = df["company"].value_counts().head(10).reset_index()
    st.dataframe(top_co, width="stretch", hide_index=True)
