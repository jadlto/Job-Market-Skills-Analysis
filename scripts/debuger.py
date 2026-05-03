import os
import sys

# LEVEL 1: IMMEDIATE FEEDBACK
print("--- SCRIPT START ---")

try:
    import pandas as pd
    import yaml
    import spacy
    print("--- LIBRARIES LOADED ---")
except ImportError as e:
    print(f"--- IMPORT ERROR: {e} ---")
    sys.exit()

# LEVEL 2: PATH CHECKING
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CONFIG_FILE = os.path.join(PROJECT_ROOT, "config", "config.yaml")
INPUT_FILE = os.path.join(PROJECT_ROOT, "data", "jobs_raw.csv")

print(f"Looking for config at: {CONFIG_FILE}")
print(f"Looking for data at: {INPUT_FILE}")

def run_test():
    print("--- ENTERING FUNCTION ---")
    
    if not os.path.exists(CONFIG_FILE):
        print("FAIL: Config file missing!")
        return
    
    with open(CONFIG_FILE, 'r') as f:
        config = yaml.safe_load(f)
        print(f"SUCCESS: Loaded YAML. Skills: {config.get('target_skills')}")

    if not os.path.exists(INPUT_FILE):
        print("FAIL: CSV file missing!")
        return

    df = pd.read_csv(INPUT_FILE)
    print(f"SUCCESS: Loaded CSV with {len(df)} rows.")

# LEVEL 3: EXECUTION
if __name__ == "__main__":
    print("--- MAIN BLOCK TRIGGERED ---")
    run_test()
    print("--- SCRIPT FINISHED ---")