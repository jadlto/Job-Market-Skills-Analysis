import duckdb
import pandas as pd
import re
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize

# --- PATHS ---
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DB_FILE = PROJECT_ROOT / "data" / "market_data.duckdb"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed_market_data.parquet"

# --- SKILL TAXONOMY ---
SKILLS = [
    # Languages
    "python", "sql", "r", "java", "scala", "javascript", "typescript", "c++", "c#",
    "bash", "shell", "go", "rust", "matlab", "sas", "vba",
    # Data & Analytics
    "excel", "tableau", "power bi", "looker", "qlik", "dax", "pandas", "numpy",
    "scipy", "matplotlib", "seaborn", "plotly", "dbt", "airflow", "spark",
    "hadoop", "kafka", "duckdb", "databricks", "snowflake", "redshift", "bigquery",
    "etl", "elt", "data warehouse", "data lake", "data pipeline", "data modeling",
    # ML / AI
    "machine learning", "deep learning", "nlp", "computer vision", "scikit-learn",
    "tensorflow", "pytorch", "keras", "xgboost", "lightgbm", "mlflow", "hugging face",
    "llm", "generative ai", "reinforcement learning", "a/b testing", "statistics",
    # Cloud & Infra
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "terraform",
    "ci/cd", "git", "github", "gitlab", "linux", "rest api", "graphql",
    # Databases
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "oracle", "sql server",
    "sqlite", "cassandra", "dynamodb",
    # Finance & Accounting
    "gaap", "ifrs", "cpa", "cfa", "financial modeling", "financial reporting",
    "fp&a", "budgeting", "forecasting", "variance analysis", "reconciliation",
    "accounts payable", "accounts receivable", "quickbooks", "sap", "netsuite",
    "vlookup", "pivot tables",
    # Business & PM
    "jira", "confluence", "agile", "scrum", "kanban", "product management",
    "stakeholder management", "requirements gathering", "risk management",
    "six sigma", "lean", "erp",
    # Soft skills
    "communication", "leadership", "problem solving", "critical thinking",
    "project management", "cross functional",
]


def clean_title(title: str) -> str:
    title = re.sub(
        r'\b(I{1,3}|IV|VI{0,3}|IX|sr\.?|jr\.?|lead|principal|staff|senior|junior|associate|mid)\b',
        '', title, flags=re.IGNORECASE
    )
    return re.sub(r'\s+', ' ', title).strip()


def cluster_titles(titles: list[str]) -> dict[str, str]:
    unique_titles = list(set(titles))
    n_unique = len(unique_titles)
    if n_unique == 0:
        return {}
    cleaned = [clean_title(t) for t in unique_titles]

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    X = normalize(vectorizer.fit_transform(cleaned))

    # KMeans requires 1 <= n_clusters <= n_samples
    raw = max(3, min(8, int(n_unique ** 0.45)))
    n_clusters = min(max(1, raw), n_unique)
    print(f"Clustering titles into {n_clusters} groups")

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    km.fit(X)

    terms = vectorizer.get_feature_names_out()
    cluster_names = {}
    for i, centroid in enumerate(km.cluster_centers_):
        top_terms = [terms[j] for j in centroid.argsort()[-5:][::-1]]
        seen_words = set()
        clean_terms = []
        for term in top_terms:
            words = term.split()
            if not all(w in seen_words for w in words):
                clean_terms.append(term.title())
                seen_words.update(words)
            if len(clean_terms) == 3:
                break
        cluster_names[i] = " / ".join(clean_terms)

    return {title: cluster_names[label] for title, label in zip(unique_titles, km.labels_)}


def extract_skills(desc: str) -> list[str]:
    desc_lower = str(desc).lower()
    found = []
    for skill in SKILLS:
        if re.search(rf'\b{re.escape(skill)}\b', desc_lower):
            found.append(skill.title())
    return found


def analyze() -> bool:
    if not DB_FILE.exists():
        print("Database not found. Run api_connector first.")
        return False

    con = duckdb.connect(str(DB_FILE))
    df = con.execute("SELECT title, description, company FROM jobs").df()
    con.close()

    if df.empty:
        print("No rows in jobs table.")
        return False

    title_map = cluster_titles(df["title"].tolist())
    df["clean_category"] = df["title"].map(title_map)

    df["found_skills"] = df["description"].apply(extract_skills)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_FILE, index=False)
    print(f"Wrote {len(df)} rows -> {OUTPUT_FILE}")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if analyze() else 1)