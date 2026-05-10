"""Shared filesystem paths for pipeline scripts and the dashboard."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_FILE = DATA_DIR / "market_data.duckdb"
PROCESSED_PARQUET = DATA_DIR / "processed_market_data.parquet"
LAST_SEARCH_TITLE_FILE = DATA_DIR / "last_search_job_title.txt"
ONET_LABEL_OVERRIDES = DATA_DIR / "onet_label_overrides.json"
ONET_DATA_DIR = DATA_DIR / "onet"
