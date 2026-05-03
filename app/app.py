import os
import sys
from dotenv import load_dotenv
load_dotenv()
from concurrent.futures import ThreadPoolExecutor

import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.recommendation_engine import RecommendationEngine
from backend.intelligent_recommend import warm_engine_indices
from components.chatbot import show_chatbot
from components.hero import show_hero_section
from components.landing import show_landing
from components.movie_row import show_movie_row
from components.search import show_search_bar
from pipelines.utils import load_config
from utils.tmdb import (
    build_movie_card_dict,
    get_movie,
    resolve_tmdb_api_key,
    tmdb_search_movie_raw,
    validate_tmdb_key,
)

st.set_page_config(page_title="Cineverse Movie Discovery", page_icon="🎬", layout="wide")


@st.cache_resource(show_spinner="🎬 Loading Cineverse engine...")
def load_engine():
    eng = RecommendationEngine()
    warm_engine_indices(eng)
    return eng


@st.cache_data(show_spinner=False)
def enrich_movie(title, api_key, _cache_v=4):
    """One TMDB search per movie (poster + meta). Trailers load only when user taps ▶ (faster page load)."""
    movie = get_movie(title, api_key)
    return build_movie_card_dict(title, movie)


@st.cache_data(show_spinner=False)
def enrich_movies(titles, api_key):
    """Parallel TMDB search (HTTP in threads); poster URLs built on main thread."""
    titles = tuple(str(t) for t in titles)
    if not titles:
        return []
    n = len(titles)
    workers = min(8, max(1, n))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        movies = list(ex.map(lambda t: tmdb_search_movie_raw(t, api_key), titles))
    return [build_movie_card_dict(t, m) for t, m in zip(titles, movies)]


def inject_styles():
    st.markdown(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
        <style>
            /* ═══════════════════════════════════════════
               CINEVERSE — PREMIUM DESIGN SYSTEM
               ═══════════════════════════════════════════ */

            .stApp {
                font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
                background:
                    radial-gradient(ellipse 80% 50% at 50% 0%, rgba(229, 9, 20, 0.12), transparent 50%),
                    radial-gradient(ellipse 60% 50% at 0% 50%, rgba(124, 58, 237, 0.08), transparent 50%),
                    radial-gradient(ellipse 60% 50% at 100% 30%, rgba(6, 182, 212, 0.06), transparent 50%),
                    linear-gradient(180deg, #030304 0%, #07070a 45%, #010102 100%);
                color: #ffffff;
            }

            /* ── Scrollbar ── */
            ::-webkit-scrollbar { width: 6px; height: 6px; }
            ::-webkit-scrollbar-track { background: transparent; }
            ::-webkit-scrollbar-thumb { background: rgba(229,9,20,0.35); border-radius: 3px; }
            ::-webkit-scrollbar-thumb:hover { background: rgba(229,9,20,0.6); }

            .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1450px; }
            h1, h2, h3, h4, p, label, span, div { color: #ffffff; font-family: 'Inter', system-ui, sans-serif; }

            /* ── Poster hover ── */
            img {
                border-radius: 14px !important;
                transition: transform 0.35s cubic-bezier(0.4,0,0.2,1), box-shadow 0.35s ease, filter 0.35s ease;
            }
            img:hover {
                transform: scale(1.07) translateY(-4px);
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6), 0 0 20px rgba(229,9,20,0.15);
                filter: saturate(1.2) brightness(1.05);
            }

            .cine-poster-wrap {
                width: 100%;
                max-width: 100%;
                margin: 0 auto 10px auto;
            }
            .cine-poster {
                width: 100%;
                aspect-ratio: 2 / 3.38;
                border-radius: 14px;
                overflow: hidden;
                background: linear-gradient(135deg, #1a1a22, #111118);
                border: 1px solid rgba(255,255,255,0.05);
            }
            .cine-poster img {
                width: 100%;
                height: 100%;
                object-fit: cover;
                object-position: center center;
                display: block;
                border-radius: 0 !important;
            }

            /* ── Buttons ── */
            div[data-testid="stButton"] button {
                background: linear-gradient(135deg, #E50914, #ff3d4a) !important;
                color: #fff !important;
                border: 0 !important;
                border-radius: 12px !important;
                font-weight: 700 !important;
                font-family: 'Inter', sans-serif !important;
                transition: all 0.3s cubic-bezier(0.4,0,0.2,1) !important;
                box-shadow: 0 4px 15px rgba(229,9,20,0.25) !important;
            }
            div[data-testid="stButton"] button:hover {
                background: linear-gradient(135deg, #c90712, #e8303d) !important;
                transform: translateY(-2px) !important;
                box-shadow: 0 8px 25px rgba(229,9,20,0.4) !important;
            }

            .section-gap { margin-top: 16px; margin-bottom: 8px; }

            /* ── Cinema shell (sweeping light) ── */
            .cinema-shell {
                position: relative;
                border: none;
                border-radius: 18px;
                padding: 24px;
                background: rgba(255,255,255,0.03);
                overflow: hidden;
                box-shadow: none;
                border: 1px solid rgba(255,255,255,0.05);
            }
            .cinema-shell::before {
                content: "";
                position: absolute;
                inset: -130% -20% auto -20%;
                height: 260%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent);
                transform: rotate(16deg);
                animation: sweep 9s linear infinite;
                pointer-events: none;
            }
            @keyframes sweep {
                from { transform: translateX(-35%) rotate(16deg); }
                to { transform: translateX(35%) rotate(16deg); }
            }

            .imax-title {
                font-size: 2.85rem;
                margin: 0;
                letter-spacing: -0.02em;
                font-weight: 900;
                background: linear-gradient(135deg, #fff 30%, rgba(229,9,20,0.8) 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }

            .landing-headline {
                font-size: 3.15rem;
                margin: 0;
                letter-spacing: -0.02em;
                font-weight: 900;
                line-height: 1.15;
            }

            /* ── Movie row strip ── */
            .row-strip {
                display: flex;
                gap: 8px;
                overflow-x: auto;
                padding: 8px 0 2px 0;
                scrollbar-width: thin;
            }
            .row-strip img {
                width: 72px;
                height: 108px;
                object-fit: cover;
                border-radius: 10px;
                border: 1px solid rgba(255,255,255,0.1);
                transition: all 0.3s ease;
            }
            .row-strip img:hover {
                border-color: rgba(229,9,20,0.4);
            }

            /* ── Ambient orbs ── */
            .ambient-orb {
                position: fixed;
                width: 260px;
                height: 260px;
                border-radius: 999px;
                filter: blur(80px);
                opacity: 0.18;
                z-index: 0;
                pointer-events: none;
                animation: drift 18s ease-in-out infinite alternate;
            }
            .orb-a { top: 12%; right: 8%; background: #E50914; }
            .orb-b { bottom: 8%; left: 6%; background: #4361ff; animation-delay: 1s; }
            @keyframes drift {
                from { transform: translateY(0px) translateX(0px) scale(1); }
                to { transform: translateY(30px) translateX(-20px) scale(1.1); }
            }

            /* ── Landing page wrappers ── */
            .landing-wrap {
                min-height: calc(100vh - 10rem);
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 1.5rem 0.5rem 2rem 0.5rem;
            }
            .landing-inner {
                width: 100%;
                max-width: 760px;
            }
            .landing-desc {
                color: #e8e8ee;
                font-size: 1.22rem;
                line-height: 1.75;
                margin: 18px 0 10px 0;
                max-width: 720px;
            }

            /* ── Section headings ── */
            h3 {
                font-weight: 800 !important;
                letter-spacing: -0.01em;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _openai_key():
    """Only read from environment — never touch `st.secrets` (avoids missing-secrets.toml UI warning)."""
    return os.getenv("OPENAI_API_KEY")


ROW_LABELS = [
    "🎯 Top Picks For You",
    "🔥 Trending Now",
    "💎 Hidden Gems",
    "🎬 Action Vibes",
    "⭐ More To Watch",
]


def split_rows(movies):
    """Up to 4 rows, 10 cards each — works for any count (e.g. 7 → one row of 7)."""
    if not movies:
        return {}
    out = {}
    for start in range(0, len(movies), 10):
        chunk = movies[start : start + 10]
        label_i = start // 10
        if label_i < len(ROW_LABELS):
            out[ROW_LABELS[label_i]] = chunk
    return out


def main():
    inject_styles()
    if "app_entered" not in st.session_state:
        st.session_state["app_entered"] = False

    if not st.session_state["app_entered"]:
        if show_landing(st):
            st.session_state["app_entered"] = True
            st.rerun()
        return

    config = load_config()
    api_key = resolve_tmdb_api_key(config)

    if st.session_state.get("_tmdb_key_used") != api_key:
        st.session_state["_tmdb_health"] = validate_tmdb_key(api_key)
        st.session_state["_tmdb_key_used"] = api_key
    ok_tmdb, tmdb_msg = st.session_state["_tmdb_health"]
    if not ok_tmdb:
        st.error(tmdb_msg)

    engine = load_engine()

    with st.sidebar:
        st.markdown("**Cineverse**")
        if st.button("← Welcome", key="sidebar_welcome"):
            st.session_state["app_entered"] = False
            st.rerun()

    # ── Mood chat toggle state (default hidden) ──
    st.session_state.setdefault("mood_chat_open", False)

    # ── Styled CSS for header area ──
    st.markdown(
        """
        <style>
            /* Mood toggle button styling */
            .mood-toggle-col [data-testid="stButton"] button {
                background: linear-gradient(135deg, #E50914, #ff4450) !important;
                border: none !important;
                border-radius: 999px !important;
                padding: 8px 22px !important;
                font-weight: 600 !important;
                font-size: 0.88rem !important;
                color: #fff !important;
                box-shadow: 0 2px 14px rgba(229,9,20,0.35);
                transition: transform 0.25s ease, box-shadow 0.3s ease;
                animation: mood-pulse 2.5s ease-in-out infinite;
            }
            .mood-toggle-col [data-testid="stButton"] button:hover {
                transform: scale(1.07) !important;
                box-shadow: 0 4px 22px rgba(229,9,20,0.55) !important;
            }
            @keyframes mood-pulse {
                0%, 100% { box-shadow: 0 2px 14px rgba(229,9,20,0.35); }
                50% { box-shadow: 0 4px 24px rgba(229,9,20,0.6); }
            }
            /* Remove extra padding from header columns */
            .header-row [data-testid="stVerticalBlockBorderWrapper"] {
                padding: 0 !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── Header row: title on left, mood button on right ──
    st.markdown('<div class="header-row">', unsafe_allow_html=True)
    hdr_left, hdr_right = st.columns([0.84, 0.16])
    with hdr_left:
        st.markdown(
            """
            <div style="
                padding: 10px 14px;
                border-radius: 12px;
                background: rgba(0,0,0,0.58);
                backdrop-filter: blur(8px);
            ">
                <span style="font-weight:700; font-size:1rem;">🎬 Cineverse Movie Discovery</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with hdr_right:
        st.markdown('<div class="mood-toggle-col">', unsafe_allow_html=True)
        mood_label = "❌ Close Chat" if st.session_state["mood_chat_open"] else "💬 Mood"
        if st.button(
            mood_label,
            key="mood_toggle_btn",
            type="primary",
            help="Want to share your mood or your favourite hero?",
        ):
            st.session_state["mood_chat_open"] = not st.session_state["mood_chat_open"]
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Ambient orbs + hero title ──
    st.markdown(
        """
        <div class="ambient-orb orb-a"></div>
        <div class="ambient-orb orb-b"></div>
        <div class="cinema-shell">
            <h1 class="imax-title">Cineverse Movie Discovery</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    movie_titles = list(engine.movies["title"].values)
    c1, c2, c3 = st.columns([2.2, 1.3, 1.2])
    with c1:
        selected_movie = show_search_bar(st, movie_titles)
    with c2:
        top_n = st.slider(
            "How many recommendations?",
            min_value=1,
            max_value=50,
            value=12,
            step=1,
            help="Exact count (1–50). Fewer = faster TMDB poster load.",
        )
    with c3:
        try:
            run_btn = st.button("Launch", use_container_width=True)
        except TypeError:
            run_btn = st.button("Launch")

    show_hero_section(st, selected_movie, api_key)

    if "last_selected_movie" not in st.session_state:
        st.session_state["last_selected_movie"] = None

    should_refresh = run_btn or st.session_state["last_selected_movie"] != selected_movie

    if should_refresh:
        with st.spinner("Finding the best movies for you..."):
            try:
                recommendations = engine.recommend(selected_movie, top_n=top_n)
                if not recommendations or recommendations == ["Movie not found in database"]:
                    st.warning("No recommendations found for this movie.")
                    st.session_state["recommendations"] = []
                else:
                    st.session_state["recommendations"] = recommendations
            except Exception as exc:
                st.error("Recommendation system error.")
                st.exception(exc)
                st.session_state["recommendations"] = []
            finally:
                st.session_state["last_selected_movie"] = selected_movie

    recommendations = st.session_state.get("recommendations", [])
    if not recommendations:
        st.info("Choose a movie and click **Launch** to load recommendation rows.")
        show_chatbot(
            st,
            [],
            engine,
            selected_movie,
            _openai_key(),
            api_key,
            enrich_movie,
        )
        return

    with st.spinner(f"Loading posters for {len(recommendations)} movies (TMDB)…"):
        detailed = enrich_movies(recommendations, api_key)
    rows = split_rows(detailed)

    for idx, (row_title, row_movies) in enumerate(rows.items()):
        if row_movies:
            st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)
            strip_html = "<div class='row-strip'>" + "".join(
                f"<img src='{m['poster']}' alt='poster' />" for m in row_movies[:10]
            ) + "</div>"
            st.markdown(strip_html, unsafe_allow_html=True)
            show_movie_row(st, row_title, row_movies, row_key=f"row_{idx}", api_key=api_key)

    show_chatbot(
        st,
        recommendations,
        engine,
        selected_movie,
        _openai_key(),
        api_key,
        enrich_movie,
    )


if __name__ == "__main__":
    main()