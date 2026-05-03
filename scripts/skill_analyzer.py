import pandas as pd
import os
import re
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
INPUT_FILE = os.path.join(PROJECT_ROOT, "data", "jobs_data.parquet")
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "data", "skill_analysis.parquet")

# A curated master list for precise extraction from snippets
# This ensures we catch the "Must-Haves" first
CORE_TECH_LIBRARY = [
    "Python", "SQL", "AWS", "Azure", "GCP", "Snowflake", "dbt", "Airflow", 
    "Spark", "Hadoop", "Tableau", "Power BI", "Excel", "Java", "Scala", 
    "Kafka", "Docker", "Kubernetes", "Looker", "SAS", "R", "Redshift"
]

def analyze_robust():
    if not os.path.exists(INPUT_FILE):
        return

    df = pd.read_parquet(INPUT_FILE)
    descriptions = df['description'].fillna('').astype(str).tolist()
    
    found_skills = []

    for desc in descriptions:
        # Normalize text for matching
        clean_desc = desc.upper()
        
        for skill in CORE_TECH_LIBRARY:
            # Regex logic: Match the skill as a whole word (\b)
            # This prevents 'R' from matching 'Requirement' or 'AWS' from matching 'Laws'
            pattern = rf'\b{re.escape(skill.upper())}\b'
            if re.search(pattern, clean_desc):
                found_skills.append(skill)

    # Count frequencies
    skill_counts = Counter(found_skills)
    
    # Convert to DataFrame
    res_df = pd.DataFrame(skill_counts.most_common(), columns=['Skill', 'Count'])
    
    # Ensure all CORE_TECH appear even if 0, for consistent charts
    existing_skills = res_df['Skill'].tolist()
    missing = [{'Skill': s, 'Count': 0} for s in CORE_TECH_LIBRARY if s not in existing_skills]
    if missing:
        res_df = pd.concat([res_df, pd.DataFrame(missing)], ignore_index=True)

    # Final sort
    res_df = res_df.sort_values('Count', ascending=False)
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    res_df.to_parquet(OUTPUT_FILE, index=False)

if __name__ == "__main__":
    analyze_robust()