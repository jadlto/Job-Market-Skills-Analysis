# Targeted Market Skill Discovery

Live job postings ([Adzuna API](https://developer.adzuna.com)) → **TF-IDF phrases** from each batch of descriptions (no fixed skill dictionary). An optional view filters phrases with a small soft-skill keyword list.

## Live app

**[Open on Streamlit Cloud](https://job-market-skills-analysis-c6y44ilrnvrhdelml97bms.streamlit.app/)**

On Streamlit Cloud: **Settings → Secrets** — use **TOML with quoted values** (not shell `KEY=value`):

```toml
ADZUNA_APP_ID = "your_id"
ADZUNA_APP_KEY = "your_key"
```

Unquoted or `.env`-style lines are **invalid TOML** and secrets will not load.

---

## Local setup

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**API keys** — either:

- `.venv/api_keys.txt`:

  ```text
  ADZUNA_APP_ID=...
  ADZUNA_APP_KEY=...
  ```

- or `.streamlit/secrets.toml`:

  ```toml
  ADZUNA_APP_ID = "..."
  ADZUNA_APP_KEY = "..."
  ```

Keys file is tried first, then Streamlit secrets.

**Run the dashboard** (from repo root):

```bash
streamlit run scripts/dashboard.py
```

`python scripts/dashboard.py` re-invokes Streamlit automatically when needed.

**CLI pipeline** (optional — wipes `data/` cache, uses `config/config.yaml` for `search.job_title`):

```bash
python scripts/run_pipeline.py
```

The hosted dashboard passes the text box value into the API and does **not** write `config.yaml` (read-only deploys). CLI still uses `config.yaml`.

---

## Deploy (Streamlit Community Cloud)

1. Push to GitHub.
2. [share.streamlit.io](https://share.streamlit.io) → connect repo.
3. Main file: `scripts/dashboard.py`.
4. Secrets (same TOML format as above — quoted strings).

Hosted storage is ephemeral; re-run **Fetch & Analyze** after restarts.
