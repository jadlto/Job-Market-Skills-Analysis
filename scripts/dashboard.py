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

import json

import streamlit as st
import pandas as pd
import plotly.express as px

sys.path.insert(0, str(_SCRIPT.parent))

from api_connector import fetch_market_data
from phrase_labels import categorize_phrase, set_onet_session_overrides
from paths import (
    LAST_SEARCH_TITLE_FILE,
    ONET_LABEL_OVERRIDES,
    ONET_QUERY_TITLE_FILE,
    PROCESSED_PARQUET,
)
from skill_analyzer import analyze


def _load_onet_overrides() -> None:
    if not ONET_LABEL_OVERRIDES.exists():
        set_onet_session_overrides(None, None)
        return
    try:
        with open(ONET_LABEL_OVERRIDES, encoding="utf-8") as f:
            data = json.load(f)
        set_onet_session_overrides(
            frozenset(str(x).lower() for x in data.get("hard", [])),
            frozenset(str(x).lower() for x in data.get("soft", [])),
        )
    except Exception:
        set_onet_session_overrides(None, None)


@st.cache_data
def _technology_occupation_titles() -> list[str]:
    """O*NET tech-focused occupations (SOC 15-* + IT managers); empty if DB missing."""
    from onet_skills import ensure_onet_database, list_technology_occupation_titles

    if ensure_onet_database() is None:
        return []
    try:
        return list_technology_occupation_titles()
    except Exception:
        return []


st.set_page_config(page_title="Market Skill Discovery", layout="wide")

_load_onet_overrides()

st.title("🎯 Targeted Market Skill Discovery")

tech_occupations = _technology_occupation_titles()

if not tech_occupations:
    st.warning(
        "The O*NET database is not available yet (it downloads automatically on first run, ~13 MB). "
        "Refresh after a few seconds, or run the app locally with network access."
    )
    selected = None
else:
    st.caption(
        "O*NET **Computer and Mathematical** occupations (SOC 15-*) plus IT systems managers — aligned with technology skill data."
    )
    selected = st.selectbox(
        "Occupation",
        options=tech_occupations,
        index=0,
        label_visibility="visible",
    )

if st.button("🚀 Fetch & Analyze", disabled=not selected):
    q_api = selected.strip()
    try:
        ONET_QUERY_TITLE_FILE.parent.mkdir(parents=True, exist_ok=True)
        ONET_QUERY_TITLE_FILE.write_text(q_api, encoding="utf-8")
    except OSError as e:
        st.error(f"Could not save selection: {e}")
        st.stop()

    with st.status(f"Running pipeline for «{q_api}»...") as status:
        try:
            status.write("Fetching jobs...")
            ok, fetch_err = fetch_market_data(q_api)
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
                        "The API returned no job postings for that occupation title. Try another role from the list."
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
    if not PROCESSED_PARQUET.exists():
        return pd.DataFrame()
    return pd.read_parquet(PROCESSED_PARQUET)


mtime = PROCESSED_PARQUET.stat().st_mtime if PROCESSED_PARQUET.exists() else 0
df = load_processed_data(mtime)

if df.empty:
    st.info(
        "Choose an occupation above and click **Fetch & Analyze**. "
        "Hosted apps lose cached data on restart — run the pipeline again."
    )
    st.stop()


def _insights_job_title() -> str:
    if ONET_QUERY_TITLE_FILE.exists():
        return ONET_QUERY_TITLE_FILE.read_text(encoding="utf-8").strip()
    if LAST_SEARCH_TITLE_FILE.exists():
        return LAST_SEARCH_TITLE_FILE.read_text(encoding="utf-8").strip()
    return ""


_insights_q = _insights_job_title()
st.subheader(
    f"Market Insights: {_insights_q}" if _insights_q else "Market Insights"
)
_onet_mode = ONET_LABEL_OVERRIDES.exists()
st.caption(
    "Tools and software names are matched against **[O*NET Technology Skills](https://www.onetcenter.org/database.html)** "
    "for the selected occupation."
    if _onet_mode
    else "**TF-IDF** phrases plus a small classifier; recruiting boilerplate is filtered first. "
    "(O*NET matching did not run.)"
)

col_chart, col_stats = st.columns([1.3, 0.7])

with col_chart:
    all_skills = [
        skill
        for sublist in df["found_skills"]
        for skill in sublist
        if categorize_phrase(skill) == "hard"
    ]

    skill_counts = pd.Series(all_skills).value_counts().reset_index()
    skill_counts.columns = ["Skill", "Count"]

    if skill_counts.empty:
        st.info(
            "No tool or software phrases from O*NET matched the job text in these listings. "
            "Try another occupation from the list."
        )
    else:
        fig = px.bar(
            skill_counts.head(15).sort_values("Count"),
            x="Count",
            y="Skill",
            orientation="h",
            template="plotly_dark",
            color="Count",
            title="Top skills",
        )
        st.plotly_chart(fig, width="stretch")

with col_stats:
    st.metric("Total Listings", len(df))
    st.write("**Top Companies**")
    top_co = df["company"].value_counts().head(10).reset_index()
    st.dataframe(top_co, width="stretch", hide_index=True)
