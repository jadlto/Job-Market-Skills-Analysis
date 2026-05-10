# Targeted Market Skill Discovery

Pull live job postings from the **[Adzuna API](https://developer.adzuna.com)**, then infer skills per listing:

1. **Preferred path — [O*NET](https://www.onetonline.org/) taxonomy** — Your search string is mapped to O*NET-SOC occupations (titles + alternate titles). Job descriptions are scanned for phrases drawn from official **[Technology Skills](https://www.onetcenter.org/database.html)** examples and **Skills** elements for those occupations. Hard vs soft labels follow O*NET session metadata (technology examples → hard; skill elements → soft). On first use, the app downloads the tab-delimited **O*NET 30.2** database from the [O*NET Resource Center](https://www.onetcenter.org/database.html) (~13 MB, Creative Commons).

2. **Fallback — TF-IDF + classifier** — If the O*NET bundle is unavailable, no occupation matches your query, or mapping fails, the pipeline uses per-document TF-IDF (unigrams + bigrams) and a small bundled **logistic regression** model (hard / soft / non-relevant), with lexicon-based boilerplate filtering.

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

The connector tries the keys file first, then Streamlit secrets, then environment variables.

**Run the dashboard** (from repo root):

```bash
streamlit run scripts/dashboard.py
```

Running `python scripts/dashboard.py` re-invokes Streamlit when no GUI context is detected.

**CLI pipeline** — deletes cached `data` artifacts (DuckDB, Parquet, O*NET label overrides), then fetches using **`config/config.yaml`** (`search.job_title`) and runs analysis:

```bash
python scripts/run_pipeline.py
```

The hosted UI passes the search box into the API and does **not** write `config.yaml`. The CLI still reads `config.yaml` when no title is passed on the command line.

### Runtime data (gitignored `data/`)

| Artifact | Role |
|----------|------|
| `market_data.duckdb` | Raw job rows from Adzuna |
| `processed_market_data.parquet` | Per-posting `found_skills` and metadata |
| `last_search_job_title.txt` | Query string used to resolve O*NET occupations |
| `onet/db_30_2_text.zip` (and extracted folder) | Official O*NET tab files (downloaded once) |
| `onet_label_overrides.json` | Lowercased hard/soft phrase sets for the dashboard when O*NET mode ran |

---

## Deploy (Streamlit Community Cloud)

1. Push to GitHub.
2. [share.streamlit.io](https://share.streamlit.io) → connect the repository.
3. Main file: `scripts/dashboard.py`.
4. Secrets: same quoted TOML format as above.

Hosted filesystems are ephemeral; after a restart, run **Fetch & Analyze** again. The first O*NET-backed run may take longer while the database zip downloads and extracts.
