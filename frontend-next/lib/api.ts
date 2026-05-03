import axios from "axios";

export type Recommendation = {
  title: string;
  poster: string;
  overview: string;
  trailer: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function getRecommendations(movie: string): Promise<Recommendation[]> {
  const { data } = await axios.post<{ recommendations: Recommendation[] }>(
    `${API_BASE}/recommend`,
    { movie },
    { timeout: 8000 }
  );
  return data.recommendations ?? [];
}
