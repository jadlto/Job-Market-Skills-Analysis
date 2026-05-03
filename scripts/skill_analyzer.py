import duckdb
import pandas as pd
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize
import spacy

# --- PATHS ---
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DB_FILE = PROJECT_ROOT / "data" / "market_data.duckdb"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed_market_data.parquet"

# --- LOAD MODEL ONCE ---
print("⏳ Loading NLP model...")
nlp = spacy.load("en_core_web_lg")

# --- NOISE FILTER ---
SKILL_STOPWORDS = {
    "job description", "job", "description", "responsibilities", "requirements",
    "qualifications", "experience", "education", "bachelor", "master", "degree",
    "years", "ability", "knowledge", "understanding", "skills", "skill",
    "work", "working", "team", "environment", "strong", "excellent",
    "communication", "written", "verbal", "preferred", "required", "plus",
    "opportunity", "position", "role", "candidate", "employer", "employee",
    "salary", "benefits", "location", "remote", "hybrid", "onsite", "office",
    "san", "authorization", "monday", "tuesday", "wednesday", "thursday", "friday"
}


def cluster_titles(titles: list[str]) -> dict[str, str]:
    """
    Clusters job titles using TF-IDF + KMeans.
    Automatically names each cluster from its most representative terms.
    Zero manual input.
    """
    unique_titles = list(set(titles))

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    X = normalize(vectorizer.fit_transform(unique_titles))

    # Auto-pick number of clusters (square root heuristic, min 5 max 15)
    n_clusters = max(5, min(15, int(len(unique_titles) ** 0.5)))
    print(f"🔢 Clustering into {n_clusters} categories...")

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    km.fit(X)

    terms = vectorizer.get_feature_names_out()
    cluster_names = {}
    for i, centroid in enumerate(km.cluster_centers_):
        top_terms = [terms[j] for j in centroid.argsort()[-3:][::-1]]
        cluster_names[i] = " / ".join(t.title() for t in top_terms)

    return {title: cluster_names[label] for title, label in zip(unique_titles, km.labels_)}


def extract_skills(desc: str) -> list[str]:
    """
    Extracts skills using spaCy NER.
    Filters out generic job description noise.
    """
    doc = nlp(str(desc))
    skills = []
    for ent in doc.ents:
        if ent.label_ in ("ORG", "PRODUCT", "WORK_OF_ART", "GPE", "LAW"):
            text = ent.text.strip()
            # Filter noise, short tokens, pure numbers, and stopwords
            if (
                text.lower() not in SKILL_STOPWORDS
                and len(text) > 2
                and not text.isnumeric()
            ):
                skills.append(text)
    return list(set(skills))


def analyze():
    if not DB_FILE.exists():
        print("❌ Database not found. Run api_connector.py first.")
        return

    con = duckdb.connect(str(DB_FILE))
    df = con.execute("SELECT title, description, company FROM jobs").df()
    con.close()

    # --- TRANSFORM: Cluster titles ---
    print(f"🏷️  Clustering {df['title'].nunique()} unique titles...")
    title_map = cluster_titles(df['title'].tolist())
    df['clean_category'] = df['title'].map(title_map)

    print("\n📊 Category breakdown:")
    print(df['clean_category'].value_counts().to_string())

    # --- TRANSFORM: Extract skills ---
    print(f"\n🔍 Extracting skills from {len(df)} descriptions...")
    df['found_skills'] = df['description'].apply(extract_skills)

    # --- WRITE to parquet ---
    df.to_parquet(OUTPUT_FILE, index=False)
    print(f"\n✅ Done. Processed {len(df)} jobs → {OUTPUT_FILE}")


if __name__ == "__main__":
    analyze()