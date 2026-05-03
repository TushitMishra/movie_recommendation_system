import pickle
import os


class RecommendationEngine:

    def __init__(self):

        # Define artifact paths
        movie_path = os.path.join("artifacts", "movie_list.pkl")
        similarity_path = os.path.join("artifacts", "similarity.pkl")

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