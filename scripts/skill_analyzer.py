import re

import duckdb
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize

from phrase_labels import categorize_phrase

CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DB_FILE = PROJECT_ROOT / "data" / "market_data.duckdb"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed_market_data.parquet"


def clean_title(title: str) -> str:
    title = re.sub(
        r"\b(I{1,3}|IV|VI{0,3}|IX|sr\.?|jr\.?|lead|principal|staff|senior|junior|associate|mid)\b",
        "",
        title,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", title).strip()


def cluster_titles(titles: list[str]) -> dict[str, str]:
    unique_titles = list(set(titles))
    n_unique = len(unique_titles)
    if n_unique == 0:
        return {}
    cleaned = [clean_title(t) for t in unique_titles]

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    X = normalize(vectorizer.fit_transform(cleaned))

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


def _format_phrase(term: str) -> str:
    """Title-case for display; keeps short acronyms readable."""
    t = term.strip()
    if not t:
        return ""
    return t.title()


def discover_skills_tfidf(descriptions: pd.Series, top_per_doc: int = 15) -> pd.Series:
    """
    Per posting: highest TF-IDF unigrams/bigrams, then drop recruiting boilerplate via
    phrase_labels.categorize_phrase. max_df suppresses terms that appear in most postings.
    """
    texts = descriptions.fillna("").astype(str).tolist()
    n_docs = len(texts)
    if n_docs == 0:
        return pd.Series([], dtype=object)

    min_df = max(1, min(5, max(1, n_docs // 25)))
    vectorizer = None
    X = None
    for md in (min_df, max(1, min_df - 1), 1):
        for max_df in (0.52, 0.62, 0.72, 0.85):
            try:
                v = TfidfVectorizer(
                    ngram_range=(1, 2),
                    stop_words="english",
                    min_df=md,
                    max_df=max_df,
                    sublinear_tf=True,
                    max_features=12000,
                )
                xt = v.fit_transform(texts)
            except ValueError:
                continue
            if xt.shape[1] > 0:
                vectorizer, X = v, xt
                break
        if vectorizer is not None:
            break
    if vectorizer is None or X is None or X.shape[1] == 0:
        return pd.Series([[] for _ in range(n_docs)], index=descriptions.index)

    terms = vectorizer.get_feature_names_out()
    out_lists = []

    for i in range(n_docs):
        row = X.getrow(i)
        idx = row.indices
        data = row.data
        if len(idx) == 0:
            out_lists.append([])
            continue
        order = np.argsort(-data)
        picked = []
        seen_lower = set()
        for k in order:
            j = idx[k]
            term = terms[j]
            if len(term.strip()) < 2:
                continue
            disp = _format_phrase(term)
            if categorize_phrase(disp) is None:
                continue
            dl = disp.lower()
            if not dl or dl in seen_lower:
                continue
            seen_lower.add(dl)
            picked.append(disp)
            if len(picked) >= top_per_doc:
                break
        out_lists.append(picked)

    return pd.Series(out_lists, index=descriptions.index)


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

    print("Extracting phrases (TF-IDF per posting)...")
    df["found_skills"] = discover_skills_tfidf(df["description"])

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_FILE, index=False)
    print(f"Wrote {len(df)} rows -> {OUTPUT_FILE}")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if analyze() else 1)
