import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Ensure project root is on path so all imports resolve correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.service import get_recommendations

app = FastAPI(title="Cineverse Movie Recommendation API")

# Allow React / Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MovieRequest(BaseModel):
    movie: str
    top_n: int = 5


@app.get("/")
def home():
    return {"message": "Cineverse API running 🚀"}


@app.post("/recommend")
def recommend_movies(req: MovieRequest):
    return {"recommendations": get_recommendations(req.movie, top_n=req.top_n)}