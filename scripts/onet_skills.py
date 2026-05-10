"""
Resolve search titles to O*NET-SOC codes and extract skills from job text using the official
O*NET taxonomy (Technology Skills + Skills elements). Data files come from the O*NET
database distribution (Creative Commons) — see https://www.onetcenter.org/database.html
"""

from __future__ import annotations

import re
import socket
import urllib.request
import zipfile
from functools import lru_cache
from pathlib import Path

import pandas as pd

from paths import ONET_DATA_DIR as ONET_DIR

ONET_ZIP_NAME = "db_30_2_text.zip"
ONET_ZIP_URL = f"https://www.onetcenter.org/dl_files/database/{ONET_ZIP_NAME}"
EXTRACT_SUBDIR = "db_30_2_text"


def onet_extract_path() -> Path:
    return ONET_DIR / EXTRACT_SUBDIR


def ensure_onet_database() -> Path | None:
    """
    Ensure tab-delimited O*NET files exist under data/onet/db_30_2_text/.
    Downloads and extracts the official zip on first use (~13 MB).
    """
    root = onet_extract_path()
    occ = root / "Occupation Data.txt"
    if occ.exists():
        return root

    ONET_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = ONET_DIR / ONET_ZIP_NAME
    if not zip_path.exists():
        print(f"Downloading O*NET database from onetcenter.org -> {zip_path.name} ...")
        old_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(180)
            urllib.request.urlretrieve(ONET_ZIP_URL, zip_path)
        finally:
            socket.setdefaulttimeout(old_timeout)

    print(f"Extracting O*NET database to {root} ...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(ONET_DIR)

    if not occ.exists():
        return None

    for loader in (_occupation_data, _alternate_titles, _technology_skills):
        loader.cache_clear()
    return root


@lru_cache(maxsize=1)
def _occupation_data() -> pd.DataFrame:
    p = onet_extract_path() / "Occupation Data.txt"
    return pd.read_csv(p, sep="\t", dtype=str).fillna("")


@lru_cache(maxsize=1)
def _alternate_titles() -> pd.DataFrame:
    p = onet_extract_path() / "Alternate Titles.txt"
    return pd.read_csv(p, sep="\t", dtype=str).fillna("")


@lru_cache(maxsize=1)
def _technology_skills() -> pd.DataFrame:
    p = onet_extract_path() / "Technology Skills.txt"
    return pd.read_csv(p, sep="\t", dtype=str).fillna("")


def list_primary_occupation_titles() -> list[str]:
    """Sorted unique primary occupation titles from ``Occupation Data.txt``."""
    df = _occupation_data()
    titles = df["Title"].dropna().astype(str).str.strip()
    return sorted({t for t in titles if len(t) >= 2}, key=str.casefold)


def list_technology_occupation_titles() -> list[str]:
    """
    Computer / math / data-related O*NET occupations likely to have Technology Skills:
    SOC **15-** (Computer and Mathematical Occupations) plus **11-3021.00** (Computer and
    Information Systems Managers).
    """
    df = _occupation_data()
    soc = df["O*NET-SOC Code"].astype(str).str.strip()
    mask = soc.str.startswith("15-", na=False) | (soc == "11-3021.00")
    titles = df.loc[mask, "Title"].dropna().astype(str).str.strip()
    return sorted({t for t in titles if len(t) >= 2}, key=str.casefold)


def resolve_soc_codes(search_query: str, max_codes: int = 5) -> list[str]:
    """
    Map a free-text job search string (e.g. 'Attorney', 'Data Analyst') to O*NET-SOC codes
    using primary occupation titles and alternate titles.
    """
    q = (search_query or "").strip().lower()
    if not q:
        return []

    occ = _occupation_data()
    alt = _alternate_titles()

    scores: dict[str, float] = {}

    for _, row in occ.iterrows():
        soc = row["O*NET-SOC Code"]
        title = str(row["Title"]).strip().lower()
        if not title:
            continue
        if q == title:
            scores[soc] = scores.get(soc, 0.0) + 12.0
        elif q in title or title in q:
            scores[soc] = scores.get(soc, 0.0) + 6.0

    for _, row in alt.iterrows():
        soc = row["O*NET-SOC Code"]
        at = str(row["Alternate Title"]).strip().lower()
        if not at:
            continue
        if q == at:
            scores[soc] = scores.get(soc, 0.0) + 10.0
        elif q in at or at in q:
            scores[soc] = scores.get(soc, 0.0) + 5.0

    # Tie-breaker: prefer shorter SOC list when scores tie (more specific titles tend to match tighter)
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [soc for soc, _ in ranked[:max_codes]]


# JDs cite these constantly; O*NET Technology Skills often lists only full product names.
_SUPPLEMENTAL_TECH_EXAMPLES = (
    "Structured Query Language",
    "SQL",
)


def _merge_supplemental_technology(examples: list[str]) -> list[str]:
    """Dedupe case-insensitively, keep longest-first order for substring matching."""
    seen: set[str] = {e.strip().lower() for e in examples}
    out = list(examples)
    for e in _SUPPLEMENTAL_TECH_EXAMPLES:
        el = e.strip().lower()
        if el not in seen and len(el) >= 2:
            seen.add(el)
            out.append(e.strip())
    out.sort(key=len, reverse=True)
    return out


def technology_examples_for_socs(soc_codes: list[str]) -> list[str]:
    """Distinct technology product examples for the given occupations, longest names first."""
    if not soc_codes:
        return []
    tech = _technology_skills()
    mask = tech["O*NET-SOC Code"].isin(soc_codes)
    examples = tech.loc[mask, "Example"].astype(str).str.strip()
    examples = [e for e in examples.unique().tolist() if len(e) >= 3]
    examples.sort(key=len, reverse=True)
    return _merge_supplemental_technology(examples)


def _phrase_in_text(haystack_lower: str, phrase_lower: str) -> bool:
    """Whole-phrase substring for multi-word products; word boundaries for single tokens."""
    if " " in phrase_lower:
        return phrase_lower in haystack_lower
    return re.search(rf"\b{re.escape(phrase_lower)}\b", haystack_lower) is not None


def extract_onet_terms(text: str, phrases_sorted: list[str]) -> list[str]:
    """
    Return phrases from phrases_sorted that appear in text (longest phrases checked first).
    Order of output follows phrase list order (longest first); dedupe case-insensitively.
    """
    if not text or not phrases_sorted:
        return []
    hay = text.lower()
    seen: set[str] = set()
    out: list[str] = []
    for phrase in phrases_sorted:
        pl = phrase.strip().lower()
        if len(pl) < 3:
            continue
        if pl in seen:
            continue
        if _phrase_in_text(hay, pl):
            seen.add(pl)
            out.append(phrase.strip())
    return out


def discover_skills_onet(
    descriptions: pd.Series,
    search_query: str,
    *,
    soc_codes: list[str] | None = None,
    max_per_doc: int = 40,
) -> pd.Series:
    """
    Per posting: scan description for O*NET Technology Skills examples for occupations
    inferred from search_query (or reuse soc_codes if provided).
    """
    soc_codes = soc_codes if soc_codes is not None else resolve_soc_codes(search_query)
    if not soc_codes:
        return pd.Series([[] for _ in range(len(descriptions))], index=descriptions.index)

    tech = technology_examples_for_socs(soc_codes)
    combined_sorted = tech

    print(
        f"O*NET: using SOC codes {soc_codes[:5]}{'...' if len(soc_codes) > 5 else ''} "
        f"({len(tech)} technology examples)."
    )

    out_lists = []
    for raw in descriptions.fillna("").astype(str):
        found = extract_onet_terms(raw, combined_sorted)
        out_lists.append(found[:max_per_doc])

    return pd.Series(out_lists, index=descriptions.index)


def session_label_sets_for_query(
    search_query: str,
    *,
    soc_codes: list[str] | None = None,
) -> tuple[frozenset[str], frozenset[str]]:
    """
    Lowercased Technology Skill examples for ``categorize_phrase`` (hard). Soft is empty
    because the app only surfaces technology/tool matches in charts.
    """
    soc_codes = soc_codes if soc_codes is not None else resolve_soc_codes(search_query)
    tech_raw = technology_examples_for_socs(soc_codes)
    hard = frozenset(t.strip().lower() for t in tech_raw if t.strip())
    return hard, frozenset()
