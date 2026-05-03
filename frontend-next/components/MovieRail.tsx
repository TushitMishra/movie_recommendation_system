"use client";

import type { Recommendation } from "@/lib/api";
import MovieCard from "./MovieCard";

type Props = {
  title: string;
  items: Recommendation[];
};

export default function MovieRail({ title, items }: Props) {
  if (!items.length) return null;

  return (
    <section className="mt-8">
      <h2 className="mb-3 text-xl font-bold">{title}</h2>
      <div className="flex gap-4 overflow-x-auto pb-2">
        {items.map((movie, idx) => (
          <MovieCard key={`${title}-${movie.title}-${idx}`} movie={movie} />
        ))}
      </div>
    </section>
  );
}
