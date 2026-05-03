import subprocess
import yaml
import os

def run_step(script_name):
    print(f"--- Running {script_name} ---")
    result = subprocess.run(["python3", f"scripts/{script_name}"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"Error in {script_name}: {result.stderr}")

def main():
    # 1. Ask user for input (updates config.yaml temporarily)
    new_title = input("What job title should we analyze? (e.g., Data Engineer): ")
    
    # Update config.yaml
    with open("config/config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    config['search']['job_title'] = new_title
    with open("config/config.yaml", 'w') as f:
        yaml.dump(config, f)

    # 2. Execute Pipeline
    run_step("api_connector.py")
    run_step("skill_analyzer.py")
    
    print("\n✅ Pipeline Finished! To view results, run:")
    print("streamlit run scripts/dashboard.py")

if __name__ == "__main__":
    main()