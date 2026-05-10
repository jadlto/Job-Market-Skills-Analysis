# Targeted Market Skill Discovery

Pull live job postings from the **[Adzuna API](https://developer.adzuna.com)** and surface **tools and software** mentioned in descriptions by matching against **[O*NET Technology Skills](https://www.onetcenter.org/database.html)** for the occupation you pick.

## How it works

### Dashboard

1. **Single dropdown** — Choose one technology-focused **O*NET** occupation:
   - SOC codes **`15-*`** (*Computer and Mathematical Occupations*: developers, data roles, DBAs, analysts, etc.)
   - Plus **`11-3021.00`** (*Computer and Information Systems Managers*)

2. **Fetch & Analyze** — The same title is sent to **Adzuna** and stored for **O*NET** mapping. Descriptions are scanned for phrases that appear in the **Technology Skills** list for the resolved occupation (plus a few supplemental labels such as **SQL** / **Structured Query Language** that postings often use but the database may not list as standalone rows).

3. **Results** — A **Top skills** bar chart counts how often each matched O*NET technology string appears across listings. This is **not** a general “all skills” view; it is **tool- and software-oriented** by design.

On first use, the app downloads the official **O*NET** tab-delimited database from the [O*NET Resource Center](https://www.onetcenter.org/database.html) (~13 MB, [Creative Commons](https://www.onetcenter.org/license_db.html)). The consumer site [O*NET OnLine](https://www.onetonline.org/) uses the same underlying taxonomy.

### Fallback

If the O*NET bundle is missing or unusable, analysis falls back to **TF-IDF** (unigrams + bigrams) and a small bundled **logistic regression** classifier (hard / soft / non-relevant), with lexicon-based boilerplate filtering.

---

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

**CLI pipeline** — wipes cached outputs under `data/`, then fetches using **`config/config.yaml`** (`search.job_title`) and runs analysis:

```bash
python scripts/run_pipeline.py
```

The hosted app does **not** write `config.yaml`; the CLI uses it when no other title is supplied.

### Runtime data (gitignored `data/`)

| Artifact | Role |
|----------|------|
| `market_data.duckdb` | Raw job rows from Adzuna |
| `processed_market_data.parquet` | Per-posting `found_skills` and metadata |
| `last_search_job_title.txt` | Last Adzuna query string |
| `onet_query_title.txt` | Selected O*NET occupation title used for SOC → Technology Skills |
| `onet/db_30_2_text.zip` (and `db_30_2_text/`) | Official O*NET tab files (downloaded once) |
| `onet_label_overrides.json` | Lowercased technology phrases for chart labeling when O*NET mode ran |

---

## Deploy (Streamlit Community Cloud)

1. Push to GitHub.
2. [share.streamlit.io](https://share.streamlit.io) → connect the repository.
3. Main file: `scripts/dashboard.py`.
4. Secrets: same quoted TOML format as above.

Hosted storage is ephemeral; after a restart, run **Fetch & Analyze** again. The first run may take longer while the O*NET zip downloads and extracts.
