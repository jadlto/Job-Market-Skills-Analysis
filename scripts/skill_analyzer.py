import duckdb
import pandas as pd
import re
from collections import Counter
from pathlib import Path

# --- PATHS ---
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DB_FILE = PROJECT_ROOT / "data" / "market_data.duckdb"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed_market_data.parquet"

# --- CLASSIFICATION RULES ---
# This maps messy titles to clean categories
CATEGORY_MAP = {
    "Accountant": ["ACCOUNTANT", "BOOKKEEPER", "TAX", "AUDIT", "CONTROLLER", "TREASURY"],
    "Data Analyst": ["DATA ANALYST", "ANALYTICS", "INSIGHTS", "BI ANALYST"],
    "Financial Analyst": ["FINANCIAL ANALYST", "FINANCE ANALYST", "FP&A", "COST ANALYST"],
    "Data Engineer": ["DATA ENGINEER", "ETL", "DATA ARCHITECT"],
    "Software Engineer": ["SOFTWARE ENGINEER", "DEVELOPER", "FULLSTACK", "BACKEND", "FRONTEND"]
}

# --- SKILL KEYWORDS ---
CORE_SKILLS = [
    "PYTHON", "SQL", "EXCEL", "CPA", "GAAP", "TAX", "AUDIT", "SAP", "ORACLE", 
    "TABLEAU", "POWER BI", "AWS", "AZURE", "SNOWFLAKE", "BUDGETING", "FORECASTING"
]

def classify_role(title):
    title = str(title).upper()
    for category, keywords in CATEGORY_MAP.items():
        if any(kw in title for kw in keywords):
            return category
    return "Other"

def analyze():
    if not DB_FILE.exists():
        return

    con = duckdb.connect(str(DB_FILE))
    # Grab all raw data
    df = con.execute("SELECT title, description, company FROM jobs").df()
    con.close()

    # 1. CLASSIFICATION TRANSFORMATION
    df['clean_category'] = df['title'].apply(classify_role)

    # 2. SKILL EXTRACTION TRANSFORMATION
    # We'll create a list of skills for every job row
    def extract_skills(desc):
        desc = str(desc).upper()
        return [skill for skill in CORE_SKILLS if re.search(rf'\b{re.escape(skill)}\b', desc)]

    df['found_skills'] = df['description'].apply(extract_skills)

    # 3. SAVE THE FULL TRANSFORMED DATA
    # This now contains the original data PLUS our new classification columns
    df.to_parquet(OUTPUT_FILE, index=False)
    print(f"✅ Transformation complete. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    analyze()