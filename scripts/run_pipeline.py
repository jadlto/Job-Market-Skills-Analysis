import subprocess
import sys  # ✅ FIX: needed for sys.executable
from pathlib import Path

def run_step(script_name):
    print(f"--- Running {script_name} ---")
    # ✅ FIX: anchor path to this file's directory, not the working directory
    script_path = Path(__file__).parent / script_name
    result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"Error in {script_name}: {result.stderr}")

def main():
    run_step("api_connector.py")
    run_step("skill_analyzer.py")
    print("\n✅ Pipeline Finished! Raw data ingested and transformation applied.")

if __name__ == "__main__":
    main()