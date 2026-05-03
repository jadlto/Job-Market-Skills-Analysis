import requests
import pandas as pd
import yaml
import time
import duckdb
import os
from pathlib import Path

CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DB_FILE = PROJECT_ROOT / "data" / "market_data.duckdb"
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"

def fetch_market_data():
    # 1. LOAD CONFIG
    with open(CONFIG_FILE, 'r') as f:
        config = yaml.safe_load(f)
    
    # 2. THE KEY LOOKUP (Explicitly check files)
    # We'll check the .env or a text file since the shell variables are empty
    app_id, app_key = None, None
    
    # Look for .env first
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if 'ADZUNA_APP_ID' in line: app_id = line.split('=')[1].strip().strip('"')
                if 'ADZUNA_APP_KEY' in line: app_key = line.split('=')[1].strip().strip('"')

    if not app_id or not app_key:
        print(f"❌ CRITICAL: Keys not found at {env_path}")
        return

    target_job = config['search']['job_title']
    all_jobs = []

    # 3. API CALL
    for page in range(1, 4):
        params = {
            'app_id': app_id,
            'app_key': app_key,
            'results_per_page': 50,
            'what': target_job
        }
        r = requests.get(f"https://api.adzuna.com/v1/api/jobs/us/search/{page}", params=params)
        
        if r.status_code == 200:
            all_jobs.extend(r.json().get('results', []))
        else:
            print(f"⚠️ API Rejected Request: {r.status_code} - {r.text}")
        time.sleep(0.5)

    if all_jobs:
        df = pd.DataFrame(all_jobs)
        # Flattening
        df['company'] = df['company'].apply(lambda x: x.get('display_name') if isinstance(x, dict) else str(x))
        df['location'] = df['location'].apply(lambda x: x.get('display_name') if isinstance(x, dict) else str(x))
        
        # 4. WRITE TO DUCKDB
        with duckdb.connect(str(DB_FILE)) as con:
            con.execute("CREATE OR REPLACE TABLE jobs AS SELECT * FROM df")
        print(f"✅ Success: {len(all_jobs)} jobs added.")
    else:
        print("❌ No jobs found. Table was not updated.")

if __name__ == "__main__":
    fetch_market_data()