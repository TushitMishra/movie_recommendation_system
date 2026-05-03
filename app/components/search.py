def show_search_bar(st, movie_titles):
    st.markdown("### Search")
    return st.selectbox(
        "Choose a movie",
        options=movie_titles,
        index=0,
        label_visibility="collapsed",
        help="Select a movie to get recommendations.",
    )