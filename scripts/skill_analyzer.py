import duckdb
import pandas as pd
import re
from collections import Counter
from pathlib import Path

CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DB_FILE = PROJECT_ROOT / "data" / "market_data.duckdb"
OUTPUT_FILE = PROJECT_ROOT / "data" / "skill_analysis.parquet"

CORE_TECH = ["Python", "SQL", "AWS", "Azure", "GCP", "Snowflake", "dbt", "Airflow", "Spark", "Tableau", "Power BI", "Excel", "R"]

def analyze():
    if not DB_FILE.exists():
        return

    con = duckdb.connect(str(DB_FILE))
    # Read from DuckDB table instead of Parquet
    df = con.execute("SELECT description FROM jobs").df()
    con.close()

    found_skills = []
    descriptions = df['description'].fillna('').astype(str).tolist()

    for desc in descriptions:
        clean_desc = desc.upper()
        for skill in CORE_TECH:
            if re.search(rf'\b{re.escape(skill.upper())}\b', clean_desc):
                found_skills.append(skill)

    counts = Counter(found_skills)
    res_df = pd.DataFrame(counts.most_common(), columns=['Skill', 'Count'])
    res_df.to_parquet(OUTPUT_FILE, index=False)

if __name__ == "__main__":
    analyze()