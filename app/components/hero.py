import streamlit as st

from utils.tmdb import get_backdrop, get_movie, get_poster, get_trailer
from utils.youtube_embed import (
    render_youtube_embed,
    youtube_id_from_url,
    youtube_open_button_html,
    youtube_watch_link,
)


def show_hero_section(st, movie_title, api_key):
    movie = get_movie(movie_title, api_key)
    if not movie:
        st.warning("Movie details not available right now.")
        return

    backdrop = get_backdrop(movie) or get_poster(movie)
    trailer = get_trailer(movie.get("id"), api_key)

    st.markdown(
        f"""
        <div style="
            border-radius: 12px;
            min-height: 360px;
            background:
                linear-gradient(90deg, rgba(0,0,0,0.90) 35%, rgba(0,0,0,0.55) 65%, rgba(0,0,0,0.25) 100%),
                url('{backdrop}');
            background-size: cover;
            background-position: center;
            padding: 28px;
            margin-bottom: 14px;
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 20px 45px rgba(0,0,0,0.5);
        ">
            <h1 style="color:#fff;margin-bottom:6px;text-shadow:0 0 18px rgba(229,9,20,0.45);">{movie.get("title", movie_title)}</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if trailer:
        vid = youtube_id_from_url(trailer)
        if vid:
            render_youtube_embed(vid, iframe_height=400, outer_height=418)
            watch = youtube_watch_link(vid)
            st.markdown(youtube_open_button_html(watch), unsafe_allow_html=True)
        else:
            st.caption("Trailer link could not be parsed.")
