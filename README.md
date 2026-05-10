# Targeted Market Skill Discovery

Analyzes live job postings (via the [Adzuna](https://developer.adzuna.com) API) and surfaces the most common **hard** and **soft** skills mentioned in descriptions for any job title you choose.

## Live app

Try it in the browser (no local setup required): **[job-market-skills-analysis on Streamlit Cloud](https://job-market-skills-analysis-c6y44ilrnvrhdelml97bms.streamlit.app/)**

Hosted apps use **Streamlit secrets** for API keys. For your own deployment, add `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` in the Streamlit Cloud dashboard under **Settings → Secrets**.

---

## Run locally

### Prerequisites

- Python 3.10+ recommended  
- Free Adzuna API credentials from [developer.adzuna.com](https://developer.adzuna.com)

### 1. Clone and enter the project

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```

### 2. Virtual environment and dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. API keys

**Option A — key file (good for local dev)**  

Create `.venv/api_keys.txt` (do not commit this file):

```text
ADZUNA_APP_ID=your_app_id_here
ADZUNA_APP_KEY=your_app_key_here
```

**Option B — Streamlit secrets (matches Streamlit Cloud)**  

Create `.streamlit/secrets.toml` in the project root:

```toml
ADZUNA_APP_ID = "your_app_id_here"
ADZUNA_APP_KEY = "your_app_key_here"
```

The app tries the key file first, then falls back to Streamlit secrets.

### 4. Start the dashboard

From the project root:

```bash
streamlit run scripts/dashboard.py
```

Your browser should open to the local URL Streamlit prints (by default `http://localhost:8501`).

If your IDE **Run** button executes `python scripts/dashboard.py`, the script detects that and re-invokes `streamlit run` so widgets and session state work correctly.

---

## Usage

1. Enter a job title (for example `Data Analyst` or `Software Engineer`).
2. Click **Fetch & Analyze** to pull listings and run skill extraction.
3. Use the toggle to switch between **Hard Skills** and **Soft Skills** charts.
4. Review **Top Companies** alongside the chart.

`config/config.yaml` stores the last searched title; the pipeline refreshes `data/market_data.duckdb` and `data/processed_market_data.parquet`.

---

## Optional: CLI pipeline

To wipe cached data and run fetch + analysis without the UI:

```bash
python scripts/run_pipeline.py
```

Ensure API keys are configured as above before running.

---

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub.
2. Connect the repo at [share.streamlit.io](https://share.streamlit.io).
3. Set **Main file path** to `scripts/dashboard.py`.
4. Under **Secrets**, add `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` (same as in `.streamlit/secrets.toml`).

Cloud filesystem storage is ephemeral; data files written during a session may not persist across restarts. For a demo or per-session analysis this is usually fine.
