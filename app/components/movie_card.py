from typing import Optional

import streamlit as st

from utils.poster_ui import fixed_poster_html
from utils.tmdb import get_movie, get_trailer
from utils.youtube_embed import (
    render_youtube_embed,
    youtube_id_from_url,
    youtube_open_button_html,
    youtube_watch_link,
)


def _full_width_button(streamlit_module, label, **kwargs):
    try:
        return streamlit_module.button(label, use_container_width=True, **kwargs)
    except TypeError:
        return streamlit_module.button(label, **kwargs)


def show_movie_card(st, movie_data, card_id, api_key):
    session_key = f"trailer_open_{card_id}"
    open_key = f"open_btn_{card_id}"
    close_key = f"close_btn_{card_id}"
    resolved_key = f"trailer_youtube_{card_id}"

    if session_key not in st.session_state:
        st.session_state[session_key] = False

    st.markdown("<div style='margin-bottom:8px;'>", unsafe_allow_html=True)

    tmdb_id = movie_data.get("tmdb_id")

    if st.session_state[session_key]:
        tid = tmdb_id
        if not tid:
            found = get_movie(movie_data.get("title") or "", api_key)
            if found and found.get("id") is not None:
                try:
                    tid = int(found["id"])
                except (TypeError, ValueError):
                    tid = None
        if resolved_key not in st.session_state and tid:
            st.session_state[resolved_key] = get_trailer(tid, api_key)
        trailer_url = st.session_state.get(resolved_key)

        if trailer_url:
            vid: Optional[str] = youtube_id_from_url(trailer_url)
            if vid:
                render_youtube_embed(vid, iframe_height=220, outer_height=236)
                watch = youtube_watch_link(vid)
                st.markdown(youtube_open_button_html(watch, compact=True), unsafe_allow_html=True)
            else:
                st.caption("Invalid trailer link")
        else:
            st.caption("Trailer not available")

        if _full_width_button(st, "✖ Close", key=close_key):
            st.session_state[session_key] = False
            if resolved_key in st.session_state:
                del st.session_state[resolved_key]
            st.rerun()
    else:
        # Narrow centered stack: equal poster box + button width matches stack
        _, stack_col, _ = st.columns([4, 10, 4])
        with stack_col:
            st.markdown(fixed_poster_html(movie_data["poster"]), unsafe_allow_html=True)
            can_trailer = bool(tmdb_id) or bool(movie_data.get("title"))
            if can_trailer:
                if _full_width_button(st, "▶ Trailer", key=open_key):
                    st.session_state[session_key] = True
                    st.rerun()
            else:
                _full_width_button(st, "Trailer N/A", key=open_key, disabled=True)

    st.markdown(
        f"<p style='color:#fff;font-weight:600;margin:6px 0 2px 0;text-align:center;'>{movie_data['title']}</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='color:#bbb;font-size:0.82rem;margin:0;text-align:center;'>⭐ {movie_data['rating']} | 📅 {movie_data['year']}</p>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
