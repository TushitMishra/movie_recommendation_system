"""Poster frame: full width of stack (matches Trailer button), equal cards, slightly tall portrait."""

from __future__ import annotations

import html as html_module


def fixed_poster_html(image_url: str) -> str:
    """Width = parent column (same as ▶ Trailer); height from aspect-ratio (slightly taller than 2:3)."""
    u = html_module.escape(image_url, quote=True)
    return (
        '<div class="cine-poster-wrap">'
        f'<div class="cine-poster"><img src="{u}" alt="" loading="lazy" /></div>'
        "</div>"
    )
