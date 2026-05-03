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

# --- SMART CLASSIFICATION RULES ---
CATEGORY_MAP = {
    "Accountant": ["ACCOUNTANT", "BOOKKEEPER", "TAX", "AUDIT", "CONTROLLER", "TREASURY"],
    "Financial Analyst": ["FINANCIAL ANALYST", "FINANCE ANALYST", "FP&A", "COST ANALYST", "INVESTMENT"],
    "Data Analyst": ["DATA ANALYST", "ANALYTICS", "INSIGHTS", "BI ANALYST", "REPORTING ANALYST"],
    "Data Engineer": ["DATA ENGINEER", "ETL", "DATA ARCHITECT", "PIPELINE"],
    # ✅ FIX: Added "FULL STACK" and "FULL-STACK" — "FULLSTACK" never matches real job titles
    "Software Engineer": ["SOFTWARE ENGINEER", "DEVELOPER", "FULL STACK", "FULL-STACK", "BACKEND", "FRONTEND", "PYTHON DEVELOPER"],
    "Project Manager": ["PROJECT MANAGER", "PMP", "PROGRAM MANAGER"],
    "Business Analyst": ["BUSINESS ANALYST", "SYSTEMS ANALYST", "OPERATIONS ANALYST"]
}

# --- SKILL KEYWORDS ---
CORE_SKILLS = [
    "PYTHON", "SQL", "EXCEL", "CPA", "GAAP", "TAX", "AUDIT", "SAP", "ORACLE", 
    "TABLEAU", "POWER BI", "AWS", "AZURE", "SNOWFLAKE", "BUDGETING", "FORECASTING",
    "RECONCILIATION", "FINANCIAL REPORTING", "QUICKBOOKS", "VLOOKUP"
]

def classify_role(title):
    title = str(title).upper()
    for category, keywords in CATEGORY_MAP.items():
        if any(kw in title for kw in keywords):
            return category
    return "Other"

def analyze():
    if not DB_FILE.exists():
        print("❌ Database not found.")
        return

    con = duckdb.connect(str(DB_FILE))
    df = con.execute("SELECT title, description, company FROM jobs").df()
    con.close()

    # 1. Apply Classification
    df['clean_category'] = df['title'].apply(classify_role)

    # 2. Extract Skills
    def extract_skills(desc):
        desc = str(desc).upper()
        return [skill for skill in CORE_SKILLS if re.search(rf'\b{re.escape(skill)}\b', desc)]

    df['found_skills'] = df['description'].apply(extract_skills)

    # 3. Save Transformed Data
    df.to_parquet(OUTPUT_FILE, index=False)
    print(f"✅ Transformation complete. Processed {len(df)} jobs. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    analyze()