import pickle
import sys
import os

from nltk.stem.porter import PorterStemmer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from pipelines.utils import load_config, resolve_project_path
from pipelines.logger import logging
from pipelines.exception import CustomException


def train_model(final_movies):

    logging.info("Model training started")

    try:
        config = load_config()

        # -----------------------------
        # Stemming
        # -----------------------------
        ps = PorterStemmer()

        final_movies['tags'] = final_movies['tags'].apply(
            lambda text: " ".join([ps.stem(word) for word in text.split()])
        )

        logging.info("Stemming completed")

        # -----------------------------
        # Vectorization
        # -----------------------------
        cv = CountVectorizer(
            max_features=config['model']['max_features'],
            stop_words=config['model']['stop_words']
        )

        vectors = cv.fit_transform(final_movies['tags']).toarray()

        logging.info("Vectorization completed")

        # -----------------------------
        # Similarity
        # -----------------------------
        similarity = cosine_similarity(vectors)

        logging.info("Similarity matrix created")

        # -----------------------------
        # Save artifacts
        # -----------------------------
        movie_path = resolve_project_path(config['artifacts']['movie_list'])
        similarity_path = resolve_project_path(config['artifacts']['similarity'])
        os.makedirs(os.path.dirname(movie_path), exist_ok=True)
        os.makedirs(os.path.dirname(similarity_path), exist_ok=True)

        pickle.dump(final_movies, open(movie_path, 'wb'))
        pickle.dump(similarity, open(similarity_path, 'wb'))

        logging.info("Model saved successfully")

        return final_movies, similarity

    except Exception as e:
        logging.error(f"Error in model pipeline: {e}")
        raise CustomException(e, sys)
