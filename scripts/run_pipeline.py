import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).parent.resolve()

def clean_data():
    from paths import DB_FILE, ONET_LABEL_OVERRIDES, ONET_QUERY_TITLE_FILE, PROCESSED_PARQUET

    files_to_delete = [
        DB_FILE,
        PROCESSED_PARQUET,
        ONET_LABEL_OVERRIDES,
        ONET_QUERY_TITLE_FILE,
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

    print("Cleaning cached pipeline outputs...")
    clean_data()

    print("Fetching...")
    ok, err = fetch_market_data()
    if not ok:
        raise SystemExit(f"Fetch failed: {err}")

    print("Analyzing...")
    if not analyze():
        raise SystemExit("Analyze failed (empty DB?).")

    print("Done.")


if __name__ == "__main__":
    main()
