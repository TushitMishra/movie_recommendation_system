"""Stable YouTube embeds inside Streamlit (avoids clipboard / player glitches from st.video)."""

from __future__ import annotations

import html
from typing import Optional

import streamlit.components.v1 as components


def youtube_id_from_url(url: str) -> Optional[str]:
    if not url:
        return None
    u = url.strip()
    if "/embed/" in u:
        return u.split("/embed/")[1].split("?")[0].split("&")[0]
    if "watch?v=" in u:
        return u.split("watch?v=")[1].split("&")[0]
    if "youtu.be/" in u:
        return u.split("youtu.be/")[1].split("?")[0]
    return None


def render_youtube_embed(
    video_id: str, iframe_height: int, outer_height: Optional[int] = None
) -> None:
    """nocookie + full allow list reduces 'Unable to copy link to clipboard' in embedded players."""
    outer_height = outer_height if outer_height is not None else iframe_height + 16
    v = html.escape(video_id, quote=True)
    src = (
        f"https://www.youtube-nocookie.com/embed/{v}"
        f"?rel=0&modestbranding=1&playsinline=1&iv_load_policy=3"
    )
    content = f"""
<div style="width:100%;max-width:100%;overflow:hidden;border-radius:12px;background:#000;">
<iframe
    src="{src}"
    width="100%"
    height="{iframe_height}"
    style="border:0;display:block;"
    allow="accelerometer; autoplay; clipboard-read; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share; fullscreen"
    allowfullscreen
    referrerpolicy="strict-origin-when-cross-origin"
    title="Trailer"
></iframe>
</div>
"""
    components.html(content, height=outer_height, scrolling=False)


def youtube_watch_link(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={html.escape(video_id, quote=True)}"


def youtube_open_button_html(watch_url: str, *, compact: bool = False) -> str:
    """Cinematic pill button opening the trailer on YouTube (new tab)."""
    href = html.escape(watch_url, quote=True)
    if compact:
        pad, fs, mt = "8px 16px", "0.82rem", "8px"
    else:
        pad, fs, mt = "11px 24px", "0.95rem", "14px"
    return f"""
<p style="margin:{mt} 0 0 0;">
<a href="{href}" target="_blank" rel="noopener noreferrer"
style="
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding:{pad};
  background:linear-gradient(180deg,#E50914 0%,#B20710 100%);
  color:#fff;
  font-weight:600;
  font-size:{fs};
  text-decoration:none;
  border-radius:999px;
  box-shadow:0 4px 18px rgba(229,9,20,0.45);
  border:1px solid rgba(255,255,255,0.18);
  letter-spacing:0.02em;
">▶ Open trailer on YouTube</a>
</p>
"""
