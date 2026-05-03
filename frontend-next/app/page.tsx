"use client";

import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import MovieRail from "@/components/MovieRail";
import { getRecommendations, type Recommendation } from "@/lib/api";

const queryClient = new QueryClient();

function HomeContent() {
  const [movieInput, setMovieInput] = useState("Avatar");
  const [activeMovie, setActiveMovie] = useState("Avatar");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["recommend", activeMovie],
    queryFn: () => getRecommendations(activeMovie),
    staleTime: 1000 * 60 * 10
  });

  const rails = useMemo(() => {
    const list: Recommendation[] = data ?? [];
    return {
      "Top Picks": list.slice(0, 5),
      "Trending Now": list.slice(5, 10),
      "Hidden Gems": list.slice(10, 15),
      "Action Vibes": list.slice(15, 20)
    };
  }, [data]);

  return (
    <main className="mx-auto max-w-[1500px] px-8 py-8">
      <motion.section
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass rounded-2xl p-8 shadow-glow"
      >
        <p className="text-xs uppercase tracking-[0.35em] text-zinc-300">CineVerse Premium</p>
        <h1 className="mt-3 text-5xl font-black leading-tight">Apple TV-grade movie discovery.</h1>
        <p className="mt-3 max-w-2xl text-zinc-300">
          Fluid rails, cinematic posters, instant trailer previews, and AI-powered recommendations.
        </p>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <input
            value={movieInput}
            onChange={(e) => setMovieInput(e.target.value)}
            placeholder="Search a movie..."
            className="w-[360px] rounded-lg border border-white/15 bg-black/40 px-4 py-2 outline-none focus:border-brand-red"
          />
          <button
            onClick={() => setActiveMovie(movieInput || "Avatar")}
            className="rounded-lg bg-brand-red px-4 py-2 font-semibold"
          >
            Generate
          </button>
        </div>
      </motion.section>

      {isLoading && <p className="mt-8 text-zinc-300">Loading recommendations...</p>}
      {isError && <p className="mt-8 text-red-400">Unable to fetch recommendations from API.</p>}

      {!isLoading && !isError && (
        <>
          <MovieRail title="🎯 Top Picks For You" items={rails["Top Picks"]} />
          <MovieRail title="🔥 Trending Now" items={rails["Trending Now"]} />
          <MovieRail title="💎 Hidden Gems" items={rails["Hidden Gems"]} />
          <MovieRail title="🎬 Action Vibes" items={rails["Action Vibes"]} />
        </>
      )}

      <a
        href="#"
        className="fixed bottom-6 right-6 grid h-14 w-14 place-items-center rounded-full bg-brand-red text-2xl shadow-glow"
        aria-label="Assistant"
      >
        💬
      </a>
    </main>
  );
}

export default function Page() {
  return (
    <QueryClientProvider client={queryClient}>
      <HomeContent />
    </QueryClientProvider>
  );
}
