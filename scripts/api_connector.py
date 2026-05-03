import requests
import pandas as pd
import yaml
import time
import duckdb
from pathlib import Path

# Absolute Path Configuration
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DB_FILE = PROJECT_ROOT / "data" / "market_data.duckdb"
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
KEYS_FILE = PROJECT_ROOT / ".venv" / "api_keys.txt"

def fetch_to_duckdb():
    # Load Config & Keys
    with open(CONFIG_FILE, 'r') as f:
        config = yaml.safe_load(f)
    
    keys = {}
    with open(KEYS_FILE, 'r') as f:
        for line in f:
            if '=' in line:
                k, v = line.strip().split('=', 1)
                keys[k.strip()] = v.strip()

    target = config['search']['job_title']
    all_jobs = []

    # API Request
    for page in range(1, 4):
        params = {
            'app_id': keys.get('ADZUNA_APP_ID'),
            'app_key': keys.get('ADZUNA_APP_KEY'),
            'results_per_page': 50,
            'what': target
        }
        r = requests.get(f"https://api.adzuna.com/v1/api/jobs/us/search/{page}", params=params)
        if r.status_code == 200:
            all_jobs.extend(r.json().get('results', []))
            time.sleep(0.5)

    if all_jobs:
        raw_df = pd.DataFrame(all_jobs)
        
        # Connect to DuckDB (creates file if not exists)
        con = duckdb.connect(str(DB_FILE))
        
        # 1. HARD RESET: Overwrite the table with raw data
        con.execute("CREATE OR REPLACE TABLE raw_jobs AS SELECT * FROM raw_df")
        
        # 2. DATA CLEANING: Extract company name from JSON-like strings
        # This fixes the issue seen in image_edbeba.png
        con.execute("""
            CREATE OR REPLACE TABLE jobs AS 
            SELECT 
                title,
                description,
                CAST(company->>'$.display_name' AS VARCHAR) as company,
                CAST(location->>'$.display_name' AS VARCHAR) as location
            FROM raw_jobs
        """)
        
        print(f"Successfully refreshed DuckDB with {len(all_jobs)} jobs for {target}")
        con.close()

if __name__ == "__main__":
    fetch_to_duckdb()