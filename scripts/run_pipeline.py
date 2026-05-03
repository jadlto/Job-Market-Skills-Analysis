import subprocess
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
        DATA_DIR / "processed_market_data.parquet"
    ]
    for f in files_to_delete:
        if f.exists():
            f.unlink()
            print(f"🗑️  Deleted {f.name}")
        else:
            print(f"⚠️  {f.name} not found, skipping.")


def run_step(script_name):
    print(f"\n--- Running {script_name} ---")
    script_path = CURRENT_DIR / script_name
    result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"Error in {script_name}:\n{result.stderr}")


def main():
    print("🧹 Cleaning stale data...")
    clean_data()

    print("\n📡 Step 1: Fetching raw data...")
    run_step("api_connector.py")

    print("\n⚙️  Step 2: Transforming data...")
    run_step("skill_analyzer.py")

    print("\n✅ Pipeline Finished! Fresh data ready.")


if __name__ == "__main__":
    main()