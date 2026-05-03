# 🎯 Targeted Market Skill Discovery

Analyzes live job postings and surfaces the most in-demand skills for any job title.

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```

### 2. Create a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_lg
```

### 3. Add your API keys
Create a file at `.venv/api_keys.txt`:

ADZUNA_APP_ID=your_id_here
ADZUNA_APP_KEY=your_key_here


Get free API keys at https://developer.adzuna.com

### 4. Run the dashboard
```bash
streamlit run scripts/dashboard.py
```

## Usage
1. Enter a job title (e.g. `Data Analyst`)
2. Click **Fetch & Analyze**
3. Toggle between **Hard Skills** and **Soft Skills**