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
def _onet_occupation_titles() -> list[str]:
    """Primary occupation titles from O*NET (empty if database missing)."""
    from onet_skills import ensure_onet_database, list_primary_occupation_titles

    if ensure_onet_database() is None:
        return []
    try:
        return list_primary_occupation_titles()
    except Exception:
        return []


st.set_page_config(page_title="Market Skill Discovery", layout="wide")

_load_onet_overrides()

st.title("🎯 Targeted Market Skill Discovery")

occupation_titles = _onet_occupation_titles()
use_onet_select = bool(occupation_titles)

if use_onet_select:
    st.caption(
        "Choose the **exact O*NET occupation** for skill matching. "
        "Optional shorter keywords below improve how many jobs Adzuna returns."
    )
    filter_q = st.text_input("Filter occupations (optional)", placeholder="Type to narrow the list")
    needle = (filter_q or "").strip().lower()
    filtered = [t for t in occupation_titles if not needle or needle in t.lower()]
    if not filtered:
        st.warning("No occupations match that filter — clear or change the filter text.")
        selected_occupation = None
    else:
        selected_occupation = st.selectbox(
            "Select occupation",
            options=filtered,
            index=0,
            help="Uses O*NET primary titles (same taxonomy as O*NET OnLine).",
        )
    adzuna_keywords = st.text_input(
        "Job board search (optional)",
        placeholder="e.g. Financial Analyst — leave blank to search using the occupation title",
        help="Adzuna works best with short phrases. If empty, the selected occupation title is used.",
    )
    fetch_enabled = selected_occupation is not None
    manual_query = None
else:
    st.warning(
        "O*NET occupation list is not available yet (database downloads on first analysis, ~13 MB). "
        "Enter a free-text job title for Adzuna until then."
    )
    manual_query = st.text_input(
        "Job title to search",
        placeholder="e.g. Data Analyst, Financial Analyst",
    )
    selected_occupation = None
    adzuna_keywords = ""
    fetch_enabled = bool(manual_query and manual_query.strip())

if st.button("🚀 Fetch & Analyze", disabled=not fetch_enabled):
    q_api = ""
    try:
        ONET_QUERY_TITLE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if use_onet_select and selected_occupation:
            ONET_QUERY_TITLE_FILE.write_text(selected_occupation.strip(), encoding="utf-8")
            q_api = (adzuna_keywords or "").strip() or selected_occupation.strip()
        else:
            try:
                ONET_QUERY_TITLE_FILE.unlink(missing_ok=True)
            except OSError:
                pass
            q_api = (manual_query or "").strip()
    except OSError as e:
        st.error(f"Could not save occupation selection: {e}")
        st.stop()

    if not q_api:
        st.warning("Nothing to search.")
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
                        "The API returned no job postings for that query. "
                        "Try different keywords in **Job board search** or another occupation."
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
        "Select an occupation and click **Fetch & Analyze**. "
        "On hosted deployments, results disappear after a restart — run the pipeline again."
    )
    st.stop()


def _insights_job_title() -> str:
    onet = (
        ONET_QUERY_TITLE_FILE.read_text(encoding="utf-8").strip()
        if ONET_QUERY_TITLE_FILE.exists()
        else ""
    )
    adz = (
        LAST_SEARCH_TITLE_FILE.read_text(encoding="utf-8").strip()
        if LAST_SEARCH_TITLE_FILE.exists()
        else ""
    )
    if onet and adz and onet.casefold() != adz.casefold():
        return f"{onet} · listings «{adz}»"
    return onet or adz or ""


_insights_q = _insights_job_title()
st.subheader(
    f"Market Insights: {_insights_q}" if _insights_q else "Market Insights"
)
_onet_mode = ONET_LABEL_OVERRIDES.exists()
st.caption(
    "Tools and software names are matched against **[O*NET Technology Skills](https://www.onetcenter.org/database.html)** "
    "for occupations aligned with your selection (same taxonomy as [O*NET OnLine](https://www.onetonline.org/))."
    if _onet_mode
    else "**TF-IDF** phrases plus a small classifier; recruiting boilerplate is filtered first. "
    "(O*NET matching did not run — missing database, no occupation match, or offline setup.)"
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
            "No technology or tool phrases matched in these postings. "
            "Try **Job board search** keywords that match how employers write ads, or pick a related occupation."
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
