import sys
from pathlib import Path

# --- PATHS ---
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

def clean_data():
    """Wipe stale data files before every run."""
    files_to_delete = [
        DATA_DIR / "market_data.duckdb",
        DATA_DIR / "processed_market_data.parquet",
    ]
    for f in files_to_delete:
        if f.exists():
            f.unlink()
            print(f"🗑️  Deleted {f.name}")
        else:
            print(f"⚠️  {f.name} not found, skipping.")


def main():
    sys.path.insert(0, str(CURRENT_DIR))
    from api_connector import fetch_market_data
    from skill_analyzer import analyze

    print("🧹 Cleaning stale data...")
    clean_data()

    print("\n📡 Step 1: Fetching raw data...")
    if not fetch_market_data():
        raise SystemExit("Fetch failed — check API keys, config, and logs above.")

    print("\n⚙️  Step 2: Transforming data...")
    if not analyze():
        raise SystemExit("Analysis failed — ensure the database has job rows.")

    print("\n✅ Pipeline Finished! Fresh data ready.")


if __name__ == "__main__":
    main()
