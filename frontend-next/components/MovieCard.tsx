"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import { useState } from "react";
import type { Recommendation } from "@/lib/api";

type Props = {
  movie: Recommendation;
};

export default function MovieCard({ movie }: Props) {
  const [openTrailer, setOpenTrailer] = useState(false);

  return (
    <motion.div
      whileHover={{ scale: 1.05, y: -6 }}
      transition={{ duration: 0.2 }}
      className="w-[220px] shrink-0"
    >
      <div className="glass overflow-hidden rounded-xl">
        {openTrailer && movie.trailer ? (
          <div className="aspect-[16/9] w-full">
            <iframe
              className="h-full w-full"
              src={`https://www.youtube.com/embed/${movie.trailer.split("v=").pop()}`}
              title={movie.title}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>
        ) : (
          <Image
            src={movie.poster || "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='450'%3E%3Crect fill='%231e1e26' width='100%25' height='100%25' rx='12'/%3E%3Ctext x='50%25' y='50%25' fill='%23a8a8b2' font-size='14' text-anchor='middle' font-family='system-ui'%3ENo poster%3C/text%3E%3C/svg%3E"}
            alt={movie.title}
            width={300}
            height={450}
            className="h-[320px] w-full object-cover"
          />
        )}
      </div>

      <h3 className="mt-2 line-clamp-1 text-sm font-semibold">{movie.title}</h3>
      <p className="line-clamp-2 text-xs text-zinc-300">{movie.overview || "No overview available."}</p>
      <button
        onClick={() => setOpenTrailer((v) => !v)}
        className="mt-2 rounded-md bg-brand-red px-3 py-1 text-xs font-semibold"
      >
        {openTrailer ? "Close" : "Play Trailer"}
      </button>
    </motion.div>
  );
}
