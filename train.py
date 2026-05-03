import sys

from pipelines.data_pipeline import load_and_process_data
from pipelines.model_pipeline import train_model
from pipelines.logger import logging
from pipelines.exception import CustomException


if __name__ == "__main__":

    logging.info("Training pipeline started")

    try:
        # Run Data Pipeline
        final_movies = load_and_process_data()

        # Run Model Pipeline
        train_model(final_movies)

        logging.info("Training completed successfully")

    except Exception as e:
        logging.error(f"Error in training pipeline: {e}")
        raise CustomException(e, sys)