import os
import time
from pathlib import Path

import duckdb
import pandas as pd
import requests
import yaml

CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DB_FILE = PROJECT_ROOT / "data" / "market_data.duckdb"
LAST_SEARCH_TITLE_FILE = PROJECT_ROOT / "data" / "last_search_job_title.txt"
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
KEYS_FILE = PROJECT_ROOT / ".venv" / "api_keys.txt"


def _load_keys_from_file():
    app_id, app_key = None, None
    if not KEYS_FILE.exists():
        return app_id, app_key
    print(f"Reading keys from {KEYS_FILE}")
    with open(KEYS_FILE, "r") as f:
        for line in f:
            clean_line = line.strip()
            if "=" in clean_line:
                key, val = clean_line.split("=", 1)
                val = val.strip().strip('"').strip("'")
                if "ADZUNA_APP_ID" in key.upper():
                    app_id = val
                elif "ADZUNA_APP_KEY" in key.upper():
                    app_key = val
    return app_id, app_key


def _pick_secret(sec, *names: str) -> str | None:
    """First non-empty secret value for any of the given keys (flat TOML)."""
    for name in names:
        try:
            val = sec[name]
            if val is not None and str(val).strip():
                return str(val).strip()
        except Exception:
            continue
    return None


def _load_keys_from_environ():
    """Some hosts inject API keys as environment variables."""
    aid = (os.environ.get("ADZUNA_APP_ID") or os.environ.get("adzuna_app_id") or "").strip()
    akey = (os.environ.get("ADZUNA_APP_KEY") or os.environ.get("adzuna_app_key") or "").strip()
    return (aid or None), (akey or None)


def _load_keys_from_streamlit():
    """Reads Adzuna keys from st.secrets (Cloud or local .streamlit/secrets.toml)."""
    try:
        import streamlit as st

        sec = st.secrets
    except Exception:
        return None, None

    app_id = _pick_secret(sec, "ADZUNA_APP_ID", "adzuna_app_id")
    app_key = _pick_secret(sec, "ADZUNA_APP_KEY", "adzuna_app_key")

    # Optional TOML section: [adzuna] app_id = "..." app_key = "..."
    if (not app_id or not app_key) and "adzuna" in sec:
        try:
            block = sec["adzuna"]
            if not app_id:
                app_id = _pick_secret(block, "app_id", "APP_ID", "appId")
            if not app_key:
                app_key = _pick_secret(block, "app_key", "APP_KEY", "appKey")
        except Exception:
            pass

    return app_id, app_key


def fetch_market_data(job_title: str | None = None) -> tuple[bool, str]:
    """Fetch from Adzuna. Pass job_title from UI, or omit to use config (CLI).

    Returns (True, "") on success, or (False, reason) with reason one of:
    missing_config, no_job_title, missing_keys, empty_results
    """
    target_job = (job_title or "").strip()
    if not target_job:
        if not CONFIG_FILE.exists():
            print(f"ERROR: Config file missing at {CONFIG_FILE}")
            return False, "missing_config"
        with open(CONFIG_FILE, "r") as f:
            config = yaml.safe_load(f)
        search = config.get("search") or {}
        target_job = str(search.get("job_title", "")).strip()
    if not target_job:
        print("ERROR: No job title (argument or config.yaml search.job_title).")
        return False, "no_job_title"

    app_id, app_key = _load_keys_from_file()
    if not app_id or not app_key:
        sid, skey = _load_keys_from_streamlit()
        if sid and skey:
            app_id, app_key = sid, skey
            print("Using Streamlit secrets for API keys")

    if not app_id or not app_key:
        eid, ekey = _load_keys_from_environ()
        if eid and ekey:
            app_id, app_key = eid, ekey
            print("Using environment variables for API keys")

    if not app_id or not app_key:
        print(f"ERROR: Missing ADZUNA_APP_ID / ADZUNA_APP_KEY ({KEYS_FILE} or Streamlit secrets).")
        return False, "missing_keys"
    all_jobs = []

    print(f"Fetching jobs for: {target_job}")

    for page in range(1, 4):
        api_url = f"https://api.adzuna.com/v1/api/jobs/us/search/{page}"
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": 50,
            "what": target_job,
        }

        try:
            r = requests.get(api_url, params=params)
            if r.status_code == 200:
                data = r.json()
                all_jobs.extend(data.get("results", []))
            else:
                print(f"API error {r.status_code}: {r.text}")
        except Exception as e:
            print(f"Request error: {e}")

        time.sleep(0.5)

    if not all_jobs:
        print("Empty results. Check your API keys or search term in config.yaml.")
        return False, "empty_results"

    df = pd.DataFrame(all_jobs)

    df["company"] = df["company"].apply(
        lambda x: x.get("display_name") if isinstance(x, dict) else str(x)
    )
    df["location"] = df["location"].apply(
        lambda x: x.get("display_name") if isinstance(x, dict) else str(x)
    )

    cols = ["id", "title", "company", "location", "description", "created"]
    cols = [c for c in cols if c in df.columns]
    df = df[cols]

    DB_FILE.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(DB_FILE)) as con:
        con.execute("CREATE OR REPLACE TABLE jobs AS SELECT * FROM df")

    LAST_SEARCH_TITLE_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_SEARCH_TITLE_FILE.write_text(target_job, encoding="utf-8")

    print(f"Ingested {len(df)} jobs -> {DB_FILE.name}")
    return True, ""


if __name__ == "__main__":
    ok, _ = fetch_market_data()
    raise SystemExit(0 if ok else 1)
