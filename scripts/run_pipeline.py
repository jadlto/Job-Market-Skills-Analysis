import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

def clean_data():
    files_to_delete = [
        DATA_DIR / "market_data.duckdb",
        DATA_DIR / "processed_market_data.parquet",
    ]
    for f in files_to_delete:
        if f.exists():
            f.unlink()
            print(f"Deleted {f.name}")
        else:
            print(f"{f.name} not found, skip")


def main():
    sys.path.insert(0, str(CURRENT_DIR))
    from api_connector import fetch_market_data
    from skill_analyzer import analyze

    print("Cleaning cached data...")
    clean_data()

    print("Fetching...")
    if not fetch_market_data():
        raise SystemExit("Fetch failed (keys / config / API).")

    print("Analyzing...")
    if not analyze():
        raise SystemExit("Analyze failed (empty DB?).")

    print("Done.")


if __name__ == "__main__":
    main()
