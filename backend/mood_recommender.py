"""
Hybrid mood recommendations:
- Content-based: TF-IDF over stemmed movie tags + cosine similarity vs mood query (same tag corpus as training).
- Content graph: cosine similarity matrix from training (boost titles aligned with selected seed movie).
- Collaborative signal: MovieLens mean ratings per TMDB id (global popularity prior).
- Optional OpenAI: expands mood text into extra keywords (OPENAI_API_KEY).
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import requests
from nltk.stem.porter import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.recommendation_engine import RecommendationEngine

STEMMER = PorterStemmer()

# Mood / genre phrases → extra tokens (matched if substring of user message).
MOOD_LEXICON: Tuple[Tuple[str, str], ...] = (
    ("thriller", "thriller suspense crime mystery noir detective killer tension chase psychological violent dark"),
    ("horror", "horror scary supernatural monster ghost zombie fear blood terrifying nightmare"),
    ("comedy", "comedy funny humor romantic laughter satire parody lighthearted"),
    ("romance", "romance love relationship wedding couple emotional heartfelt"),
    ("action", "action adventure explosion combat hero chase battle fight war soldier"),
    ("sci-fi", "science fiction space robot future technology alien planet dystopian"),
    ("scifi", "science fiction space robot future technology alien planet dystopian"),
    ("fantasy", "fantasy magic dragon wizard kingdom medieval epic quest"),
    ("animation", "animation animated cartoon family colorful pixar disney"),
    ("family", "family children kid friendly uplifting wholesome"),
    ("drama", "drama emotional realistic relationships oscar serious biography"),
    ("musical", "musical music dance singing broadway song"),
    ("war", "war military soldier battle trench historical army"),
    ("western", "western cowboy outlaw frontier desert gunslinger"),
    ("documentary", "documentary real life interview journalism facts"),
    ("dark", "dark bleak gritty noir disturbing psychological tense"),
    ("feel-good", "uplifting heartwarming inspiring positive wholesome comedy"),
    ("suspense", "suspense tension mystery unpredictable twists secrets"),
)


def stem_text(text: str) -> str:
    words = text.lower().split()
    return " ".join(STEMMER.stem(w) for w in words)


def expand_mood_lexicon(user_message: str) -> str:
    """Augment user text using mood/genre dictionary hits."""
    msg = user_message.lower().strip()
    chunks: List[str] = [msg]
    for key, expansion in MOOD_LEXICON:
        if key in msg:
            chunks.append(expansion)
    return " ".join(chunks)


def expand_mood_openai(user_message: str, api_key: str, timeout: float = 18.0) -> str:
    """Optional: ask OpenAI for comma-separated mood/genre keywords."""
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Output only a comma-separated list of at most 20 short "
                            "keywords: genres, moods, settings (no sentences, no punctuation except commas)."
                        ),
                    },
                    {"role": "user", "content": f"Movie mood or vibe: {user_message}"},
                ],
                "max_tokens": 120,
                "temperature": 0.35,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"] or ""
        return text.strip()
    except Exception:
        return ""


@lru_cache(maxsize=1)
def _popularity_by_tmdb(root: str) -> dict:
    """Mean MovieLens rating per TMDB id (weak collaborative / popularity signal)."""
    ratings_path = os.path.join(root, "data", "ratings.csv")
    links_path = os.path.join(root, "data", "links.csv")
    if not os.path.isfile(ratings_path) or not os.path.isfile(links_path):
        return {}
    ratings = pd.read_csv(ratings_path)
    links = pd.read_csv(links_path)
    merged = ratings.merge(links, on="movieId")
    grp = merged.groupby("tmdbId")["rating"].mean()
    return grp.astype(float).to_dict()


def _normalize(arr: np.ndarray) -> np.ndarray:
    a = np.asarray(arr, dtype=float)
    lo, hi = float(np.min(a)), float(np.max(a))
    if hi - lo < 1e-12:
        return np.zeros_like(a)
    return (a - lo) / (hi - lo)


def mood_rank(
    engine: RecommendationEngine,
    user_message: str,
    pool_titles: Sequence[str],
    seed_movie: Optional[str],
    *,
    openai_api_key: Optional[str] = None,
    top_k: int = 8,
    root: Optional[str] = None,
) -> Tuple[List[Tuple[str, float, str]], str]:
    """
    Returns (ranked list of (title, score, reason_snippet), debug_blurb).
    """
    root = root or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    movies_df = engine.movies.reset_index(drop=True)
    if "tags" not in movies_df.columns:
        return [], "Movie tags not loaded — cannot run mood TF-IDF."

    tags_series = movies_df["tags"].astype(str).tolist()
    expanded = expand_mood_lexicon(user_message)
    if openai_api_key:
        extra = expand_mood_openai(user_message, openai_api_key)
        if extra:
            expanded = expanded + " " + extra
    query_stemmed = stem_text(expanded)

    vectorizer = TfidfVectorizer(max_features=5000, stop_words="english")
    tfidf_m = vectorizer.fit_transform(tags_series)
    tfidf_q = vectorizer.transform([query_stemmed])
    mood_sim = cosine_similarity(tfidf_q, tfidf_m).flatten()

    n = len(movies_df)
    pool_set = {t for t in pool_titles if t}
    pop_map = _popularity_by_tmdb(root)
    pop_vals = np.zeros(n, dtype=float)
    for i, mid in enumerate(movies_df["id"].values):
        try:
            pop_vals[i] = pop_map.get(int(mid), 3.0)
        except (TypeError, ValueError):
            pop_vals[i] = 3.0
    pop_n = _normalize(pop_vals)

    seed_n = np.zeros(n, dtype=float)
    if seed_movie and seed_movie in movies_df["title"].values:
        pos = int(movies_df[movies_df["title"] == seed_movie].index[0])
        seed_vec = np.asarray(engine.similarity[pos])
        seed_n = _normalize(seed_vec)

    pool_bin = np.array([1.0 if t in pool_set else 0.0 for t in movies_df["title"].values], dtype=float)

    mood_n = _normalize(mood_sim)
    score = (
        0.48 * mood_n
        + 0.22 * seed_n
        + 0.18 * pop_n
        + 0.12 * pool_bin
    )

    order = np.argsort(score)[::-1][:top_k]
    titles_col = movies_df["title"].values
    out: List[Tuple[str, float, str]] = []
    for pos in order:
        title = titles_col[pos]
        sc = float(score[pos])
        bits = []
        if mood_n[pos] > 0.35:
            bits.append("mood/T")
        if seed_movie and seed_n[pos] > 0.35:
            bits.append("seed")
        if pop_n[pos] > 0.6:
            bits.append("crowd")
        if pool_bin[pos] > 0:
            bits.append("your-list")
        reason = "+".join(bits) if bits else "blend"
        out.append((title, sc, reason))

    debug = (
        "Signals: TF-IDF+cosine on tags (content), seed similarity matrix (content graph), "
        "MovieLens mean rating by TMDB id (popularity / weak collaborative), "
        "boost if title is in your current recommendation strip."
    )
    if openai_api_key:
        debug += " OpenAI keyword expansion enabled when API responds."
    return out, debug

