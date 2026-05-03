"""
Unified intelligent recommendations from free-text:
- Multi-axis mood / emotion vectors (lexicon → stem overlap, cosine vs movie tags)
- Content: TF–IDF + cosine on training tags (plot, cast, genres in one bag)
- Actor / name: boosted when stemmed cast tokens appear in tags
- Ratings: optional MovieLens min / max filter + confidence-weighted collaborative score
- Seed movie: pre-trained cosine similarity matrix (content-based graph)
- Pool boost: titles already in your on-screen recommendations

Returns human-readable "why" snippets (not internal codes).
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from nltk.stem.porter import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.mood_recommender import MOOD_LEXICON, expand_mood_lexicon, expand_mood_openai
from backend.recommendation_engine import RecommendationEngine
from backend.tmdb_person import filmography_norm_titles_for_person, norm_movie_title

# What the user mainly wants — drives score weights (plain-language behaviour).
QueryIntent = str  # "actor" | "cast" | "genre" | "plot" | "mood" | "balanced"

# Lowercase "two word" lines are often not names (avoid treating as actor).
_NOT_ACTOR_WORD = frozenset(
    {
        "forecast", "tomorrow", "today", "morning", "evening", "night", "year",
        "week", "month", "monday", "tuesday", "wednesday", "thursday", "friday",
        "saturday", "sunday", "good", "best", "worst", "next", "last", "first",
        "long", "short", "high", "low", "new", "old", "big", "little",
    }
)

STEMMER = PorterStemmer()

# Emotional axes → stemmed lexicon phrases (multi-dimensional mood, not one label)
EMOTION_AXES: Dict[str, str] = {
    "melancholy": "sad grief tear lonely loss heartbreak sorrow cry funeral ache emptiness regret",
    "warmth": "hope family love friendship healing uplifting comfort redemption kindness together",
    "tension": "thriller chase fear danger suspense anxiety panic killer hostage escape survival",
    "anger": "revenge rage fight betrayal war battle furious injustice vendetta",
    "nostalgia": "memory childhood past remember years ago flashback hometown letter diary",
    "absurd": "comedy funny absurd satire parody silly joke ridiculous humor",
    "awe": "epic wonder space scale universe majestic visual spectacle adventure discovery",
    "intimacy": "relationship marriage couple conversation quiet dinner romance subtle dialogue",
}

# Intent modifiers (Step 3 style)
DISTRACTION_WORDS = (
    "distract",
    "escape",
    "cheer up",
    "light",
    "funny",
    "laugh",
    "mind off",
    "not think",
)
REFLECTION_WORDS = (
    "reflect",
    "feel",
    "cry",
    "process",
    "heavy",
    "meaning",
    "sit with",
    "think about",
    "emotional",
)


def stem_text(text: str) -> str:
    words = re.sub(r"[^\w\s]", " ", text.lower()).split()
    return " ".join(STEMMER.stem(w) for w in words if w)


def _axis_lexicon_stems() -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for axis, phrase in EMOTION_AXES.items():
        stems = set()
        for w in phrase.split():
            stems.add(STEMMER.stem(w))
        out[axis] = list(stems)
    return out


_AXIS_STEMS = _axis_lexicon_stems()


def _emotion_vector_from_stems(stem_blob: str) -> np.ndarray:
    tokens = set(stem_blob.split())
    vec = np.zeros(len(EMOTION_AXES), dtype=float)
    for i, axis in enumerate(EMOTION_AXES.keys()):
        hits = sum(1 for s in _AXIS_STEMS[axis] if s in tokens)
        vec[i] = float(hits)
    norm = np.linalg.norm(vec)
    if norm > 1e-9:
        vec = vec / norm
    return vec


def _movie_emotion_matrix(tag_stems_list: List[str]) -> np.ndarray:
    mat = np.zeros((len(tag_stems_list), len(EMOTION_AXES)), dtype=float)
    for i, blob in enumerate(tag_stems_list):
        mat[i] = _emotion_vector_from_stems(blob)
    return mat


def _ensure_engine_indices(engine: RecommendationEngine) -> None:
    """
    TF-IDF fit + emotion matrix are expensive; cache once on the engine instance.
    (Previously refit on every chat message → multi-second stalls / white screen.)
    """
    if getattr(engine, "_ir_ready", False):
        return
    movies_df = engine.movies.reset_index(drop=True)
    if "tags" not in movies_df.columns:
        engine._ir_ready = True
        return
    tags_raw = movies_df["tags"].astype(str).tolist()
    vectorizer = TfidfVectorizer(max_features=6000, stop_words="english", min_df=1)
    tfidf_m = vectorizer.fit_transform(tags_raw)
    tag_stems = [stem_text(t) for t in tags_raw]
    M_emo = _movie_emotion_matrix(tag_stems)
    engine._ir_vectorizer = vectorizer
    engine._ir_tfidf_m = tfidf_m
    engine._ir_tag_stems = tag_stems
    engine._ir_M_emo = M_emo
    engine._ir_ready = True


def warm_engine_indices(engine: RecommendationEngine) -> None:
    """Call once after loading RecommendationEngine to avoid lag on first chat."""
    _ensure_engine_indices(engine)


@lru_cache(maxsize=1)
def _rating_stats(root: str) -> Tuple[dict, dict]:
    """tmdbId -> mean rating, tmdbId -> rating count (collaborative + confidence)."""
    ratings_path = os.path.join(root, "data", "ratings.csv")
    links_path = os.path.join(root, "data", "links.csv")
    if not os.path.isfile(ratings_path) or not os.path.isfile(links_path):
        return {}, {}
    ratings = pd.read_csv(ratings_path)
    links = pd.read_csv(links_path)
    merged = ratings.merge(links, on="movieId")
    g = merged.groupby("tmdbId")["rating"].agg(["mean", "count"])
    mean_d = g["mean"].astype(float).to_dict()
    cnt_d = g["count"].astype(int).to_dict()
    # normalize keys to int
    mean_d = {int(k): v for k, v in mean_d.items()}
    cnt_d = {int(k): v for k, v in cnt_d.items()}
    return mean_d, cnt_d


def _parse_rating_bounds(text: str) -> Tuple[Optional[float], Optional[float]]:
    """Extract min/max user rating preferences from text (MovieLens 0.5–5 scale)."""
    t = text.lower()
    lo, hi = None, None
    # "above 4", "at least 3.5", "rating > 4"
    for pat in [
        r"(?:above|at least|more than|>=|>|min(?:imum)?)\s*(\d(?:\.\d)?)",
        r"rating\s*(?:>|>=)\s*(\d(?:\.\d)?)",
    ]:
        m = re.search(pat, t)
        if m:
            try:
                v = float(m.group(1))
                lo = max(0.5, min(5.0, v))
            except ValueError:
                pass
    for pat in [
        r"(?:below|under|less than|<=|<|max(?:imum)?)\s*(\d(?:\.\d)?)",
        r"rating\s*(?:<|<=)\s*(\d(?:\.\d)?)",
    ]:
        m = re.search(pat, t)
        if m:
            try:
                v = float(m.group(1))
                hi = max(0.5, min(5.0, v))
            except ValueError:
                pass
    # "4 stars", "3.5/10" scaled roughly: treat X/10 as X/2 for 5-star scale
    m = re.search(r"(\d(?:\.\d)?)\s*/\s*10", t)
    if m:
        try:
            lo = max(0.5, min(5.0, float(m.group(1)) / 2.0))
        except ValueError:
            pass
    m = re.search(r"(\d(?:\.\d)?)\s*stars?", t)
    if m and lo is None:
        try:
            lo = max(0.5, min(5.0, float(m.group(1))))
        except ValueError:
            pass
    return lo, hi


def _extract_actor_queries(text: str) -> List[str]:
    """Heuristic actor / people phrases (cast is in training tags)."""
    out: List[str] = []
    t = re.sub(r"[*_`#]", "", (text or "").strip())
    patterns = [
        r"(?:with|starring|featuring|actor|actress)\s+([A-Za-z][A-Za-z\s.'-]{1,40}?)(?:\.|,|$)",
        r"^([A-Z][a-z]+\s+[A-Z][a-z]+)\s*$",
        r"^([a-z][a-z.'-]+\s+[a-z][a-z.'-]+)\s*$",
    ]
    for pat in patterns:
        for m in re.finditer(pat, t):
            name = m.group(1).strip()
            if len(name) > 2:
                out.append(name)
    seen: set[str] = set()
    uniq: List[str] = []
    for name in out:
        k = name.lower()
        if k not in seen:
            seen.add(k)
            uniq.append(name)
    return uniq


def detect_query_intent(user_message: str) -> QueryIntent:
    """
    Rough category so recommendations match what the user typed:
    actor / cast / genre / plot / mood — else balanced.
    """
    raw = re.sub(r"[*_`#]", "", (user_message or "").strip())
    if len(raw) < 2:
        return "balanced"
    tl = raw.lower()

    # Bare "Firstname Lastname" (Tom Cruise or tom cruise) → actor search
    m_lower_two = re.match(r"^([a-z][a-z.'-]+)\s+([a-z][a-z.'-]+)$", tl)
    if m_lower_two:
        a, b = m_lower_two.group(1), m_lower_two.group(2)
        if a not in _NOT_ACTOR_WORD and b not in _NOT_ACTOR_WORD:
            return "actor"
    if re.match(r"^[A-Z][a-z.'-]+\s+[A-Z][a-z.'-]+$", raw):
        return "actor"

    # Explicit actor / cast wording
    if re.search(r"\b(actor|actress|starring|featuring)\b", tl):
        return "actor"
    if re.search(r"\b(with|lead\s+role)\s+[a-z]", tl):
        return "actor"
    if re.search(r"\b(cast|ensemble|actors?)\b", tl) and "forecast" not in tl:
        return "cast"

    # Plot / story ask
    if re.search(
        r"\b(plot|story\s+about|film\s+about|movie\s+about|movie\s+where|"
        r"film\s+where|narrative|screenplay)\b",
        tl,
    ):
        return "plot"

    # Genre labels from training lexicon + common asks
    if re.search(r"\b(genre|genres)\b", tl):
        return "genre"
    for key, _ in MOOD_LEXICON:
        if key in tl:
            return "genre"

    # Mood / vibe (feelings, not genre keywords above)
    mood_words = (
        "feel", "feeling", "mood", "vibe", "sad", "happy", "lonely", "cry",
        "heartbreak", "anxious", "stress", "depress", "uplift", "cheer",
        "loneliness", "hurt", "heal",
    )
    if any(w in tl for w in mood_words):
        return "mood"
    if len(tl) > 90:
        return "mood"

    return "balanced"


def _blend_for_intent(
    intent: QueryIntent,
    *,
    has_actors: bool,
    w_dist: float,
    w_refl: float,
) -> Tuple[float, float, float, float, float, float]:
    """
    Returns (tfidf_w, emo_w, actor_w, seed_w, collab_w, pool_w) normalized to sum to 1.
    """
    if intent == "actor":
        base_a = 0.52 if has_actors else 0.15
        base_t = 0.33 if has_actors else 0.55
        w = (base_t, 0.06, base_a, 0.0, 0.04, 0.05)
    elif intent == "cast":
        w = (0.44, 0.10, 0.22 if has_actors else 0.0, 0.06, 0.07, 0.11)
    elif intent == "genre":
        w = (0.46, 0.20, 0.18 if has_actors else 0.0, 0.08, 0.09, 0.07)
    elif intent == "plot":
        w = (0.54, 0.14, 0.18 if has_actors else 0.0, 0.06, 0.07, 0.07)
    elif intent == "mood":
        w = (0.20, 0.48, 0.18 if has_actors else 0.0, 0.04, 0.08, 0.06)
    else:
        tfidf_w = 0.28 + 0.08 * w_dist
        emo_w = 0.22 + 0.10 * w_refl
        actor_w = 0.18 if has_actors else 0.0
        seed_w = 0.18
        collab_w = 0.12
        pool_w = 0.10
        if not has_actors:
            tfidf_w += 0.05
            emo_w += 0.05
            seed_w += 0.04
            collab_w += 0.04
        w = (tfidf_w, emo_w, actor_w, seed_w, collab_w, pool_w)
    s = sum(w)
    return tuple(x / s for x in w) if s > 1e-9 else w


def _normalize(arr: np.ndarray) -> np.ndarray:
    a = np.asarray(arr, dtype=float)
    lo, hi = float(np.min(a)), float(np.max(a))
    if hi - lo < 1e-12:
        return np.zeros_like(a)
    return (a - lo) / (hi - lo)


def _intent_weights(user_lower: str) -> Tuple[float, float]:
    """(distraction_weight, reflection_weight) for genre-style reweighting."""
    d = sum(1 for w in DISTRACTION_WORDS if w in user_lower)
    r = sum(1 for w in REFLECTION_WORDS if w in user_lower)
    if d == 0 and r == 0:
        return 0.5, 0.5
    return float(d) / (d + r + 1e-6), float(r) / (d + r + 1e-6)


def intelligent_rank(
    engine: RecommendationEngine,
    user_message: str,
    pool_titles: Sequence[str],
    seed_movie: Optional[str],
    *,
    openai_api_key: Optional[str] = None,
    tmdb_api_key: Optional[str] = None,
    top_k: int = 8,
    root: Optional[str] = None,
) -> List[Tuple[str, float, str]]:
    """
    Returns list of (title, score, why_human) — no debug blob; third field is user-facing reason.
    """
    root = root or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    movies_df = engine.movies.reset_index(drop=True)
    if "tags" not in movies_df.columns:
        return []

    _ensure_engine_indices(engine)
    if not getattr(engine, "_ir_ready", False):
        return []
    tag_stems = engine._ir_tag_stems
    n_docs = len(tag_stems)

    expanded = expand_mood_lexicon(user_message)
    if openai_api_key:
        extra = expand_mood_openai(user_message, openai_api_key)
        if extra:
            expanded = expanded + " " + extra
    query_stemmed = stem_text(expanded + " " + user_message)

    # --- TF-IDF (reuses corpus matrix built once on engine) ---
    vectorizer = engine._ir_vectorizer
    tfidf_m = engine._ir_tfidf_m
    tfidf_q = vectorizer.transform([query_stemmed])
    tfidf_sim = cosine_similarity(tfidf_q, tfidf_m).flatten()

    # --- Multi-axis emotion cosine ---
    u_emo = _emotion_vector_from_stems(query_stemmed)
    M_emo = engine._ir_M_emo
    if np.linalg.norm(u_emo) < 1e-9:
        emo_sim = np.zeros(n_docs)
    else:
        emo_sim = (M_emo @ u_emo).flatten()
        emo_sim = np.maximum(emo_sim, 0.0)

    # --- Actor overlap (content: cast names stemmed in tags) ---
    actors = _extract_actor_queries(user_message)
    actor_boost = np.zeros(n_docs, dtype=float)
    actor_note = ""
    if actors:
        stems = [stem_text(a) for a in actors]
        actor_note = f"names like “{actors[0]}”" if actors else ""
        for i, blob in enumerate(tag_stems):
            hits = sum(1 for s in stems if s and s in blob)
            actor_boost[i] = float(hits) / max(len(stems), 1)
    actor_n = _normalize(actor_boost) if actors else np.zeros(n_docs)

    # --- Rating bounds + collaborative (MovieLens mean × log count) ---
    mean_d, cnt_d = _rating_stats(root)
    min_r, max_r = _parse_rating_bounds(user_message)
    n = len(movies_df)
    ml_mean = np.zeros(n, dtype=float)
    ml_conf = np.zeros(n, dtype=float)
    for i, mid in enumerate(movies_df["id"].values):
        try:
            tid = int(mid)
        except (TypeError, ValueError):
            tid = -1
        if tid in mean_d:
            ml_mean[i] = mean_d[tid]
            ml_conf[i] = float(np.log1p(cnt_d.get(tid, 0)))
        else:
            ml_mean[i] = 3.0
            ml_conf[i] = 0.0

    rating_ok = np.ones(n, dtype=float)
    if min_r is not None:
        rating_ok = (ml_mean >= min_r - 1e-6).astype(float)
    if max_r is not None:
        rating_ok = rating_ok * (ml_mean <= max_r + 1e-6).astype(float)

    collab = ml_mean * ml_conf
    collab_n = _normalize(collab)

    # --- Seed similarity (pretrained content graph) ---
    seed_n = np.zeros(n, dtype=float)
    if seed_movie and seed_movie in movies_df["title"].values:
        pos = int(movies_df[movies_df["title"] == seed_movie].index[0])
        seed_n = _normalize(np.asarray(engine.similarity[pos]))

    pool_set = {t for t in pool_titles if t}
    pool_bin = np.array([1.0 if t in pool_set else 0.0 for t in movies_df["title"].values], dtype=float)

    # --- Intent: actor vs genre vs plot vs mood → different score mix ---
    user_l = user_message.lower()
    intent = detect_query_intent(user_message)

    # TMDB filmography (fixes actors missing from English tag strings, e.g. Indian cinema)
    tmdb_hit = np.zeros(n, dtype=float)
    tmdb_catalog_overlap = 0
    tmdb_filmography_size = 0
    actor_gap_note = ""
    if intent == "actor" and actors and (tmdb_api_key or "").strip():
        film_titles = filmography_norm_titles_for_person(actors[0], (tmdb_api_key or "").strip())
        tmdb_filmography_size = len(film_titles)
        for i, t in enumerate(movies_df["title"].values):
            if norm_movie_title(str(t)) in film_titles:
                tmdb_hit[i] = 1.0
        tmdb_catalog_overlap = int(tmdb_hit.sum())
        if tmdb_filmography_size > 0 and tmdb_catalog_overlap == 0:
            actor_gap_note = (
                "TMDB has titles for this actor, but none match this app's movie list — "
                "using tag/text matches instead."
            )

    w_dist, w_refl = _intent_weights(user_l)
    tfidf_w, emo_w, actor_w, seed_w, collab_w, pool_w = _blend_for_intent(
        intent,
        has_actors=bool(actors),
        w_dist=w_dist,
        w_refl=w_refl,
    )
    show_seed_in_why = seed_w >= 0.07

    tfidf_nn = _normalize(tfidf_sim)
    emo_nn = _normalize(emo_sim)

    blend_other = (
        tfidf_w * tfidf_nn
        + emo_w * emo_nn
        + actor_w * actor_n
        + seed_w * seed_n
        + collab_w * collab_n
        + pool_w * pool_bin
    )
    if intent == "actor" and float(np.max(tmdb_hit)) > 0:
        tie = _normalize(blend_other)
        score = np.where(tmdb_hit > 0.5, 0.72 + 0.28 * tie, 0.0)
    else:
        score = blend_other
    score = score * rating_ok
    if float(np.max(score)) < 1e-12:
        score = tfidf_nn * 0.5 + emo_nn * 0.3 + collab_n * 0.2

    order = np.argsort(score)[::-1][:top_k]
    titles_col = movies_df["title"].values

    out: List[Tuple[str, float, str]] = []
    top_axes = [ax for ax, v in zip(EMOTION_AXES.keys(), u_emo) if v > 0.15][:2]

    actor_hint_text = (
        actor_gap_note
        if (intent == "actor" and actor_gap_note)
        else "matched mainly on **cast / actor names** in our movie tags"
    )
    intent_hint = {
        "actor": actor_hint_text,
        "cast": "matched **cast & credits** style keywords in tags",
        "genre": "matched **genre & type** tags",
        "plot": "matched **plot / story** text in tags",
        "mood": "matched **mood & vibe** (feelings + tone)",
        "balanced": "",
    }.get(intent, "")

    for pos in order:
        title = titles_col[pos]
        sc = float(score[pos])
        parts: List[str] = []
        if intent_hint:
            parts.append(intent_hint)
        if intent in ("plot", "genre", "mood", "balanced") and tfidf_nn[pos] > 0.25:
            parts.append("story & tags overlap your words")
        if intent in ("mood", "balanced") and emo_nn[pos] > 0.2 and top_axes:
            parts.append(f"vibe overlap: {', '.join(top_axes)}")
        if intent == "actor" and tmdb_hit[pos] > 0.5:
            parts.append("**TMDB filmography** overlap with this catalog")
        if intent == "actor" and actors and actor_boost[pos] > 0:
            parts.append(f"cast mentions ({actor_note})" if actor_note else "cast mentions")
        elif intent not in ("actor",) and actors and actor_boost[pos] > 0:
            parts.append(f"cast overlap ({actor_note})" if actor_note else "cast overlap")
        if show_seed_in_why and seed_movie and seed_n[pos] > 0.25:
            parts.append(f"similar to **{seed_movie}** (film you selected above)")
        if collab_n[pos] > 0.35 and intent not in ("actor",):
            parts.append("often rated well on MovieLens")
        elif collab_n[pos] > 0.35 and intent == "actor":
            parts.append("solid MovieLens ratings where we have data")
        if pool_bin[pos] > 0:
            parts.append("also in your current recommendation strip")
        if min_r is not None:
            parts.append(f"mean rating ≥ {min_r:g} where we have data")
        why = "; ".join(parts) if parts else "blended tags + signals"
        out.append((title, sc, why))

    return out


def maybe_clarification(user_message: str) -> Optional[str]:
    """One smart follow-up for very vague emotional queries."""
    t = user_message.strip()
    if len(t) < 4:
        return None
    tl = t.lower()
    emotional = any(
        w in tl
        for w in (
            "sad",
            "low",
            "depress",
            "anxious",
            "lonely",
            "fight",
            "broke up",
            "stress",
            "hurt",
        )
    )
    if not emotional:
        return None
    has_intent = any(w in tl for w in DISTRACTION_WORDS + REFLECTION_WORDS)
    if has_intent:
        return None
    return (
        "Quick check: do you want something **light to distract you**, "
        "or something **that sits with the feeling**? (You can answer in your next message.)"
    )
