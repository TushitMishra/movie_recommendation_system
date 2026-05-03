import os
from concurrent.futures import ThreadPoolExecutor

from backend.intelligent_recommend import intelligent_rank, maybe_clarification
from utils.poster_ui import fixed_poster_html
from utils.tmdb import (
    FALLBACK_POSTER,
    build_movie_card_dict,
    tmdb_search_movie_raw,
)


def _render_mood_poster_grid(streamlit_module, mood_items):
    """Posters + title + rating/year only (same feel as main rows, no scores or jargon)."""
    if not mood_items:
        return
    streamlit_module.markdown("##### 🎬 For your mood")
    n = len(mood_items)
    for row_start in range(0, n, 5):
        chunk = mood_items[row_start : row_start + 5]
        cols = streamlit_module.columns(len(chunk))
        for col, it in zip(cols, chunk):
            with col:
                _, mid, _ = streamlit_module.columns([4, 10, 4])
                with mid:
                    streamlit_module.markdown(
                        fixed_poster_html(it["poster"]), unsafe_allow_html=True
                    )
                    streamlit_module.markdown(
                        f"<p style='color:#fff;font-weight:600;margin:4px 0 2px 0;font-size:0.95rem;text-align:center;'>{it['title']}</p>",
                        unsafe_allow_html=True,
                    )
                    streamlit_module.caption(
                        f"⭐ {it.get('rating', '?')} · 📅 {it.get('year', '?')}"
                    )


def show_chatbot(
    st,
    recommendation_titles,
    engine,
    seed_movie,
    openai_key=None,
    api_key=None,
    enrich_movie_fn=None,
):
    """
    Mood-aware assistant (clean UI — details run in the backend only).
    """
    openai_key = openai_key or os.getenv("OPENAI_API_KEY")

    st.markdown(
        """
        <div id="assistant" style="
            margin-top:24px;
            padding:14px;
            border:1px solid rgba(255,255,255,0.12);
            border-radius:12px;
            background:rgba(255,255,255,0.03);
        ">
            <h4 style="margin:0;color:#fff;">🤖 Movie Assistant</h4>
            <p style="margin:4px 0 0 0;color:#bbb;">
                Type what you want: e.g. <strong>Tom Cruise</strong> or <strong>with Meryl Streep</strong> (cast),
                <strong>horror</strong> or <strong>sci-fi</strong> (genre), <strong>heist at a bank</strong> (plot),
                or <strong>feel-good after a bad day</strong> (mood). The app picks the right kind of match.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "chat_messages" not in st.session_state:
        hint = (
            "Try: **Tom Cruise** · **comedy** · **story about time travel** · **I need something warm and calm**."
        )
        st.session_state["chat_messages"] = [{"role": "assistant", "content": hint}]

    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("mood_items"):
                _render_mood_poster_grid(st, msg["mood_items"])

    st.session_state.setdefault("mood_chat_open", False)

    if st.session_state.get("mood_chat_open", False):
        prompt = st.chat_input("Tell your mood, favourite hero, or any vibe...")
    else:
        prompt = None

    if not prompt:
        return

    st.session_state["chat_messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if engine is None:
        reply = "Recommendation engine not loaded."
        st.session_state["chat_messages"].append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)
        return

    clarify = maybe_clarification(prompt)
    if clarify:
        st.session_state["chat_messages"].append({"role": "assistant", "content": clarify})
        with st.chat_message("assistant"):
            st.markdown(clarify)
        return

    try:
        ranked = intelligent_rank(
            engine,
            prompt,
            list(recommendation_titles or []),
            seed_movie,
            openai_api_key=openai_key,
            tmdb_api_key=api_key,
            top_k=8,
        )
    except Exception as exc:
        reply = f"Recommendation engine error: `{exc}`"
        st.session_state["chat_messages"].append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)
        return

    if not ranked:
        reply = "Could not rank movies — check that tags are present in `movie_list.pkl`."
        st.session_state["chat_messages"].append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)
        return

    mood_items = []
    if api_key:
        titles_only = [r[0] for r in ranked]
        n = len(titles_only)
        workers = min(8, max(1, n))
        with ThreadPoolExecutor(max_workers=workers) as ex:
            raw_movies = list(
                ex.map(lambda t: tmdb_search_movie_raw(t, api_key), titles_only)
            )
        for (title, score, _), movie in zip(ranked, raw_movies):
            info = build_movie_card_dict(title, movie)
            mood_items.append(
                {
                    "title": info["title"],
                    "poster": info["poster"],
                    "rating": info["rating"],
                    "year": info["year"],
                    "mood_score": score,
                }
            )
    else:
        for title, score, _ in ranked:
            mood_items.append(
                {
                    "title": title,
                    "poster": FALLBACK_POSTER,
                    "rating": "—",
                    "year": "—",
                    "mood_score": score,
                }
            )

    response = "Here are some movies that fit what you asked for."

    st.session_state["chat_messages"].append(
        {"role": "assistant", "content": response, "mood_items": mood_items}
    )
    with st.chat_message("assistant"):
        st.markdown(response)
        _render_mood_poster_grid(st, mood_items)