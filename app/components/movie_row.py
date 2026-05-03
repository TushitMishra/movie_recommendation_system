from components.movie_card import show_movie_card


def show_movie_row(st, title, movies, row_key, api_key):
    st.markdown(f"### {title}")
    limited_movies = movies[:10]
    if not limited_movies:
        return

    first_batch = limited_movies[:5]
    second_batch = limited_movies[5:10]

    cols = st.columns(len(first_batch))
    for idx, movie in enumerate(first_batch):
        with cols[idx]:
            show_movie_card(st, movie, card_id=f"{row_key}_a_{idx}", api_key=api_key)

    if second_batch:
        cols = st.columns(len(second_batch))
        for idx, movie in enumerate(second_batch):
            with cols[idx]:
                show_movie_card(st, movie, card_id=f"{row_key}_b_{idx}", api_key=api_key)