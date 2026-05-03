import duckdb
import pandas as pd
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
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


def cluster_titles(titles: list[str]) -> dict[str, str]:
    """
    Clusters job titles using TF-IDF + KMeans.
    Deduplicates cluster name terms so labels are clean.
    """
    unique_titles = list(set(titles))

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    X = normalize(vectorizer.fit_transform(unique_titles))

    n_clusters = max(5, min(15, int(len(unique_titles) ** 0.5)))
    print(f"🔢 Clustering into {n_clusters} categories...")

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    km.fit(X)

    terms = vectorizer.get_feature_names_out()
    cluster_names = {}
    for i, centroid in enumerate(km.cluster_centers_):
        # Get top terms, deduplicate words across terms
        top_terms = [terms[j] for j in centroid.argsort()[-5:][::-1]]
        seen_words = set()
        clean_terms = []
        for term in top_terms:
            words = term.split()
            # Only add term if it introduces a new word
            if not all(w in seen_words for w in words):
                clean_terms.append(term.title())
                seen_words.update(words)
            if len(clean_terms) == 3:
                break
        cluster_names[i] = " / ".join(clean_terms)

    return {title: cluster_names[label] for title, label in zip(unique_titles, km.labels_)}


def build_skill_vocabulary(descriptions: list[str], min_doc_freq: int = 3) -> set[str]:
    """
    Builds a skill vocabulary purely from the data.
    Only keeps phrases that appear in at least min_doc_freq postings,
    filtering out one-off noise automatically.
    Uses spaCy to keep only noun phrases (real skills, not sentence fragments).
    """
    # Extract noun chunks from all descriptions via spaCy
    all_chunks = []
    for desc in descriptions:
        doc = nlp(desc[:5000])  # cap length for performance
        chunks = [
            chunk.text.strip().lower()
            for chunk in doc.noun_chunks
            if 2 < len(chunk.text.strip()) < 40  # ignore single chars and long fragments
            and not chunk.text.strip()[0].isdigit()
        ]
        all_chunks.append(" | ".join(chunks))  # join for CountVectorizer

    # Use CountVectorizer to find phrases appearing across min_doc_freq docs
    cv = CountVectorizer(
        tokenizer=lambda x: x.split(" | "),
        preprocessor=lambda x: x,
        min_df=min_doc_freq,
        binary=True
    )
    cv.fit(all_chunks)
    vocabulary = set(cv.get_feature_names_out())

    # Filter out generic non-skill phrases
    noise = {
        "job description", "job", "description", "responsibilities", "requirements",
        "qualifications", "experience", "education", "bachelor", "master", "degree",
        "years", "ability", "knowledge", "understanding", "skills", "skill",
        "work", "working", "team", "environment", "communication", "opportunity",
        "position", "role", "candidate", "salary", "benefits", "location",
        "the fp& a", "fp& a", "work type", "the fp", "overview", "reports",
        "monday", "tuesday", "wednesday", "thursday", "friday", "hybrid", "remote"
    }
    return vocabulary - noise


def extract_skills(desc: str, vocabulary: set[str]) -> list[str]:
    """
    Extracts skills from a description by matching against
    the statistically-derived vocabulary (appears in 3+ postings).
    """
    doc = nlp(str(desc)[:5000])
    found = []
    for chunk in doc.noun_chunks:
        text = chunk.text.strip()
        if text.lower() in vocabulary:
            found.append(text)
    return list(set(found))


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

    # --- TRANSFORM: Build skill vocabulary from data ---
    print(f"\n📚 Building skill vocabulary from {len(df)} descriptions...")
    vocabulary = build_skill_vocabulary(df['description'].tolist(), min_doc_freq=3)
    print(f"✅ Vocabulary: {len(vocabulary)} unique skill phrases")

    # --- TRANSFORM: Extract skills ---
    print(f"🔍 Extracting skills...")
    df['found_skills'] = df['description'].apply(lambda d: extract_skills(d, vocabulary))

    # --- WRITE to parquet ---
    df.to_parquet(OUTPUT_FILE, index=False)
    print(f"\n✅ Done. Processed {len(df)} jobs → {OUTPUT_FILE}")


if __name__ == "__main__":
    analyze()