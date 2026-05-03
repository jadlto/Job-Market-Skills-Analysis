import requests
import pandas as pd
import yaml
import time
import duckdb
from pathlib import Path

# 1. SETUP PATHS
# Resolves the absolute path to ensure the script works regardless of where it's called from
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DB_FILE = PROJECT_ROOT / "data" / "market_data.duckdb"
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"

# Targeted path based on your directory structure (image_ed5163.png)
# This points into the .venv folder to grab the specific text file
KEYS_FILE = PROJECT_ROOT / ".venv" / "api_keys.txt"

def fetch_market_data():
    # 2. LOAD SEARCH CONFIGURATION
    if not CONFIG_FILE.exists():
        print(f"❌ ERROR: Config file missing at {CONFIG_FILE}")
        return
        
    with open(CONFIG_FILE, 'r') as f:
        config = yaml.safe_load(f)
    
    # 3. EXTRACT KEYS FROM api_keys.txt
    app_id, app_key = None, None
    if not KEYS_FILE.exists():
        print(f"❌ ERROR: Key file missing at {KEYS_FILE}")
        print("Ensure 'api_keys.txt' is inside the '.venv' folder.")
        return

    print(f"🔑 Reading keys from {KEYS_FILE}...")
    with open(KEYS_FILE, 'r') as f:
        for line in f:
            clean_line = line.strip()
            if '=' in clean_line:
                key, val = clean_line.split('=', 1)
                # Clean up whitespace and quotes
                val = val.strip().strip('"').strip("'")
                if 'ADZUNA_APP_ID' in key.upper():
                    app_id = val
                elif 'ADZUNA_APP_KEY' in key.upper():
                    app_key = val

    if not app_id or not app_key:
        print(f"❌ ERROR: Could not find ADZUNA_APP_ID or ADZUNA_APP_KEY in {KEYS_FILE}")
        return

    target_job = config['search']['job_title']
    all_jobs = []

    print(f"📡 Fetching live market data for: {target_job}...")

    # 4. API REQUEST LOOP
    for page in range(1, 4):
        api_url = f"https://api.adzuna.com/v1/api/jobs/us/search/{page}"
        params = {
            'app_id': app_id,
            'app_key': app_key,
            'results_per_page': 50,
            'what': target_job,
        }
        
        try:
            r = requests.get(api_url, params=params)
            if r.status_code == 200:
                data = r.json()
                all_jobs.extend(data.get('results', []))
            else:
                print(f"⚠️ API Error {r.status_code}: {r.text}")
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            
        time.sleep(0.5) # Polite rate limiting

    if not all_jobs:
        print("Empty results. Check your API keys or search term in config.yaml.")
        return

    # 5. DATA PROCESSING
    df = pd.DataFrame(all_jobs)
    
    # Flatten nested dictionaries for DuckDB compatibility
    df['company'] = df['company'].apply(lambda x: x.get('display_name') if isinstance(x, dict) else str(x))
    df['location'] = df['location'].apply(lambda x: x.get('display_name') if isinstance(x, dict) else str(x))
    
    # Keep essential columns to keep the database clean
    cols = ['id', 'title', 'company', 'location', 'description', 'created']
    df = df[cols]

    # 6. DATABASE WRITE
    # Ensure data directory exists
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with duckdb.connect(str(DB_FILE)) as con:
        # Atomic replacement of the jobs table
        con.execute("CREATE OR REPLACE TABLE jobs AS SELECT * FROM df")
    
    print(f"✅ Success! Ingested {len(df)} jobs into {DB_FILE.name}")

if __name__ == "__main__":
    fetch_market_data()