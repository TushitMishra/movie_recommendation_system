import pickle
import os

from pipelines.data_pipeline import load_and_process_data
from pipelines.model_pipeline import train_model
from pipelines.utils import resolve_project_path


class RecommendationEngine:

    def __init__(self):

        # Define artifact paths
        movie_path = resolve_project_path("artifacts/movie_list.pkl")
        similarity_path = resolve_project_path("artifacts/similarity.pkl")

        if not os.path.exists(movie_path) or not os.path.exists(similarity_path):
            final_movies = load_and_process_data()
            train_model(final_movies)

        # Load artifacts
        with open(movie_path, "rb") as f:
            self.movies = pickle.load(f)

        with open(similarity_path, "rb") as f:
            self.similarity = pickle.load(f)


    def recommend(self, movie, top_n=5):

        # Check if movie exists
        if movie not in self.movies['title'].values:
            return ["Movie not found in database"]

        movie_index = self.movies[self.movies['title'] == movie].index[0]

        distances = self.similarity[movie_index]

        movies_list = sorted(
            enumerate(distances),
            key=lambda x: x[1],
            reverse=True
        )[1:top_n+1]

        recommended_movies = [
            self.movies.iloc[i[0]].title
            for i in movies_list
        ]

        return recommended_movies
