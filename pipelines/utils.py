import os

import yaml
import requests


# -----------------------------------
# Load Config File
# -----------------------------------
def load_config():
    try:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        config_path = os.path.join(project_root, "config", "config.yaml")
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)
        return config
    except Exception as e:
        raise Exception(f"Error loading config file: {e}")


# -----------------------------------
# Fetch Movie Poster from TMDB
# -----------------------------------
def fetch_poster(movie_title, api_key):
    try:
        url = (
            f"https://api.themoviedb.org/3/search/movie"
            f"?api_key={api_key}&query={movie_title}"
        )

        response = requests.get(url)
        data = response.json()

        # Check if results exist
        if data.get("results") and len(data["results"]) > 0:
            poster_path = data["results"][0].get("poster_path")

            if poster_path:
                return f"https://image.tmdb.org/t/p/w500{poster_path}"

    except Exception as e:
        print(f"Error fetching poster: {e}")

    # Fallback image
    return "https://via.placeholder.com/300x450?text=No+Image"
