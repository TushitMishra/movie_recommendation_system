import pandas as pd
import ast
import sys

from pipelines.logger import logging
from pipelines.utils import load_config
from pipelines.exception import CustomException


def load_and_process_data():

    logging.info("Data pipeline started")

    try:
        config = load_config()

        # -----------------------------
        # Load datasets
        # -----------------------------
        movies = pd.read_csv(config['data']['movies_path'], low_memory=False)
        credits = pd.read_csv(config['data']['credits_path'])
        keywords = pd.read_csv(config['data']['keywords_path'])

        logging.info("Datasets loaded successfully")

        movies = movies[['id', 'title', 'overview', 'genres']]

        if 'movie_id' in credits.columns:
            credits.rename(columns={'movie_id': 'id'}, inplace=True)

        # -----------------------------
        # Convert IDs
        # -----------------------------
        movies['id'] = pd.to_numeric(movies['id'], errors='coerce')
        movies = movies.dropna(subset=['id'])

        movies['id'] = movies['id'].astype(int)
        credits['id'] = credits['id'].astype(int)
        keywords['id'] = keywords['id'].astype(int)

        # -----------------------------
        # Merge
        # -----------------------------
        movies = movies.merge(credits, on='id')
        movies = movies.merge(keywords, on='id')

        logging.info("Datasets merged successfully")

        # -----------------------------
        # Clean
        # -----------------------------
        movies.dropna(inplace=True)
        movies.reset_index(drop=True, inplace=True)

        logging.info("Missing values removed")

        # -----------------------------
        # Feature Extraction
        # -----------------------------
        def extract_names(obj):
            try:
                return [i['name'] for i in ast.literal_eval(obj)]
            except Exception as e:
                logging.warning(f"extract_names error: {e}")
                return []

        def extract_cast(obj):
            try:
                return [i['name'] for i in ast.literal_eval(obj)[:3]]
            except Exception as e:
                logging.warning(f"extract_cast error: {e}")
                return []

        def extract_director(obj):
            try:
                for i in ast.literal_eval(obj):
                    if i['job'] == 'Director':
                        return [i['name']]
                return []
            except Exception as e:
                logging.warning(f"extract_director error: {e}")
                return []

        movies['genres'] = movies['genres'].apply(extract_names)
        movies['keywords'] = movies['keywords'].apply(extract_names)
        movies['cast'] = movies['cast'].apply(extract_cast)
        movies['crew'] = movies['crew'].apply(extract_director)

        movies['overview'] = movies['overview'].apply(lambda x: x.split())

        def remove_spaces(L):
            return [i.replace(" ", "") for i in L]

        movies['genres'] = movies['genres'].apply(remove_spaces)
        movies['keywords'] = movies['keywords'].apply(remove_spaces)
        movies['cast'] = movies['cast'].apply(remove_spaces)
        movies['crew'] = movies['crew'].apply(remove_spaces)

        # -----------------------------
        # Create Tags
        # -----------------------------
        movies['tags'] = (
            movies['overview']
            + movies['genres']
            + movies['keywords']
            + movies['cast']
            + movies['crew']
        )

        if 'title_x' in movies.columns:
            movies.rename(columns={'title_x': 'title'}, inplace=True)

        final_movies = movies[['id', 'title', 'tags']].copy()

        final_movies['tags'] = final_movies['tags'].apply(lambda x: " ".join(x).lower())

        logging.info("Data pipeline completed successfully")

        return final_movies

    except Exception as e:
        logging.error(f"Error in data pipeline: {e}")
        raise CustomException(e, sys)