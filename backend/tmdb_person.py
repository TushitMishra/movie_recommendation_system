"""
TMDB person search + movie credits — used when tag-based cast matching fails
(e.g. Indian actors not spelled out in older MovieLens tag strings).
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import FrozenSet

import requests

BASE_URL = "https://api.themoviedb.org/3"
TIMEOUT = 15
HEADERS = {"Accept": "application/json"}


def norm_movie_title(title: str) -> str:
    t = (title or "").lower().strip()
    t = re.sub(r"\s+", " ", t)
    return t


@lru_cache(maxsize=128)
def filmography_norm_titles_for_person(person_query: str, api_key: str) -> FrozenSet[str]:
    """
    Normalized movie titles from TMDB acting credits for the best search hit.
    Empty if API fails or no key.
    """
    q = (person_query or "").strip()
    k = (api_key or "").strip()
    if not q or not k:
        return frozenset()

    try:
        r = requests.get(
            f"{BASE_URL}/search/person",
            params={
                "api_key": k,
                "query": q,
                "language": "en-US",
            },
            timeout=TIMEOUT,
            headers=HEADERS,
        )
        if r.status_code != 200:
            return frozenset()
        data = r.json()
        results = data.get("results") or []
        if not results:
            return frozenset()
        pid = results[0].get("id")
        if not pid:
            return frozenset()

        r2 = requests.get(
            f"{BASE_URL}/person/{pid}/movie_credits",
            params={"api_key": k},
            timeout=TIMEOUT,
            headers=HEADERS,
        )
        if r2.status_code != 200:
            return frozenset()
        credits = r2.json()
        out: set[str] = set()
        for section in ("cast",):
            for row in credits.get(section) or []:
                for key in ("title", "original_title"):
                    t = row.get(key)
                    if t and isinstance(t, str):
                        out.add(norm_movie_title(t))
        return frozenset(out)
    except requests.RequestException:
        return frozenset()
