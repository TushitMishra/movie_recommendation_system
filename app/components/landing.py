import streamlit as st


def _wide_button(streamlit_module, label, **kwargs):
    try:
        return streamlit_module.button(label, use_container_width=True, **kwargs)
    except TypeError:
        return streamlit_module.button(label, **kwargs)


_LANDING_CSS = """
<style>
    /* ── Hide default header on landing ── */
    header[data-testid="stHeader"] { background: transparent !important; }

    /* ── Orb keyframes ── */
    @keyframes od1 { 0% { transform: translate(0,0) scale(1); } 100% { transform: translate(50px,35px) scale(1.12); } }
    @keyframes od2 { 0% { transform: translate(0,0) scale(1); } 100% { transform: translate(-35px,45px) scale(1.08); } }

    /* ── Orbs via pseudo-elements (pure CSS, no DOM) ── */
    .stApp::before {
        content: '';
        position: fixed;
        width: 520px; height: 520px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(229,9,20,0.25), transparent 70%);
        top: -10%; left: -6%;
        filter: blur(80px);
        pointer-events: none;
        z-index: 0;
        animation: od1 18s ease-in-out infinite alternate;
    }
    .stApp::after {
        content: '';
        position: fixed;
        width: 400px; height: 400px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(124,58,237,0.18), transparent 70%);
        top: 12%; right: -5%;
        filter: blur(80px);
        pointer-events: none;
        z-index: 0;
        animation: od2 22s ease-in-out infinite alternate;
    }

    /* ── Fade-up animation ── */
    @keyframes fup { from { opacity: 0; transform: translateY(28px); } to { opacity: 1; transform: translateY(0); } }

    /* ── Badge ── */
    .hbadge {
        display: inline-flex; align-items: center; gap: 8px; padding: 8px 22px;
        border-radius: 100px; background: rgba(229,9,20,0.12); border: 1px solid rgba(229,9,20,0.3);
        font-size: 0.78rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
        color: #ff7878 !important; margin: 0 auto 24px auto;
        animation: bp 3s ease-in-out infinite, fup 0.8s ease-out both;
    }
    @keyframes bp { 0%, 100% { box-shadow: 0 0 0 0 rgba(229,9,20,0.15); } 50% { box-shadow: 0 0 20px 4px rgba(229,9,20,0.15); } }

    /* ── Hero Title ── */
    .htitle {
        font-size: 3.6rem; font-weight: 900; line-height: 1.08; margin: 0 0 6px 0;
        letter-spacing: -0.025em; color: #fff !important;
        animation: fup 0.9s ease-out 0.3s both;
    }
    .gw {
        background: linear-gradient(135deg, #fff 0%, #E50914 50%, #F59E0B 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    }

    /* ── Subtitle ── */
    .hsub {
        color: #9ca3af !important; font-size: 1.1rem; line-height: 1.85;
        max-width: 580px; margin: 14px auto 0 auto;
        animation: fup 0.9s ease-out 0.6s both;
    }
    .hsub b { color: #e5e7eb !important; font-weight: 600; }

    /* ── Typewriter ── */
    .tw {
        display: inline-block; overflow: hidden; white-space: nowrap;
        border-right: 3px solid #E50914; font-style: italic; color: #a1a1aa !important;
        font-size: 1rem; margin: 14px auto 0 auto;
        animation: twt 3.2s steps(42) 1s both, bk 0.7s step-end infinite;
    }
    @keyframes twt { from { width: 0; } to { width: 100%; } }
    @keyframes bk { 50% { border-color: transparent; } }

    /* ── Feature card styling ── */
    .fc-icon {
        width: 50px; height: 50px; border-radius: 14px; display: grid; place-items: center;
        font-size: 1.5rem; margin-bottom: 12px;
    }
    .fc-wrap {
        background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
        border-radius: 18px; padding: 24px 20px; height: 100%;
        transition: all 0.3s ease;
    }
    .fc-wrap:hover {
        border-color: rgba(229,9,20,0.25); transform: translateY(-3px);
        box-shadow: 0 14px 40px rgba(0,0,0,0.35);
    }

    /* ── Stats styling ── */
    .sv {
        font-size: 1.65rem; font-weight: 900;
        background: linear-gradient(135deg, #fff, #E50914);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    }
    .sl {
        font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.1em;
        color: #71717a !important; font-weight: 600; margin-top: 2px;
    }

    /* ── CTA button overrides ── */
    div.cta-section [data-testid="stButton"] button {
        background: linear-gradient(135deg, #E50914, #ff3d4a) !important;
        border: none !important; border-radius: 16px !important;
        padding: 16px 52px !important; font-weight: 800 !important;
        font-size: 1.1rem !important;
        box-shadow: 0 6px 30px rgba(229,9,20,0.35) !important;
        transition: all 0.3s ease !important;
    }
    div.cta-section [data-testid="stButton"] button:hover {
        transform: translateY(-3px) scale(1.03) !important;
        box-shadow: 0 12px 45px rgba(229,9,20,0.5) !important;
    }

    /* ── Scroll indicator ── */
    .sd {
        width: 4px; height: 8px; border-radius: 4px; background: #71717a;
        animation: sb 1.5s ease-in-out infinite;
    }
    @keyframes sb { 0%, 100% { transform: translateY(0); opacity: 1; } 50% { transform: translateY(10px); opacity: 0.3; } }

    @media (max-width: 768px) {
        .htitle { font-size: 2.2rem !important; }
    }
</style>
"""


def show_landing(streamlit_module) -> bool:
    """Immersive cinematic welcome screen. Returns True if user clicked Get Started."""

    # ─── Inject CSS ───
    streamlit_module.markdown(_LANDING_CSS, unsafe_allow_html=True)

    # ─── Spacer for vertical centering ───
    streamlit_module.markdown("<div style='height:6vh;'></div>", unsafe_allow_html=True)

    # ─── Badge ───
    streamlit_module.markdown(
        '<div style="text-align:center;">'
        '<span class="hbadge">&#127916; AI-Powered Movie Discovery</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ─── Hero Title ───
    streamlit_module.markdown(
        '<div style="text-align:center;">'
        '<div class="htitle">Discover Movies That<br/><span class="gw">Match Your Mood</span></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ─── Subtitle ───
    streamlit_module.markdown(
        '<div style="text-align:center;">'
        '<div class="hsub">'
        "Tell us what you feel like watching, and our AI finds films that "
        "fit &mdash; whether it&rsquo;s a specific <b>actor</b>, <b>vibe</b>, or <b>story</b>.<br/>"
        "No complicated filters, just <b>meaningful recommendations</b> with reasons you&rsquo;ll understand."
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ─── Typewriter quote ───
    streamlit_module.markdown(
        '<div style="text-align:center;">'
        '<span class="tw">&ldquo;Every great movie starts with the right mood.&rdquo;</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    streamlit_module.markdown("<div style='height:2rem;'></div>", unsafe_allow_html=True)

    # ─── Feature Cards (using Streamlit columns) ───
    features = [
        ("🧠", "AI-Powered Engine",
         "Advanced NLP understands natural language to recommend movies you'll actually love.",
         "#E5091433", "#E5091444"),
        ("🎭", "Mood-Based Discovery",
         "Feeling adventurous? Nostalgic? Just say it — we'll match your emotion to the perfect film.",
         "#7C3AED33", "#7C3AED44"),
        ("⚡", "Lightning Fast",
         "Get 20+ curated recommendations in under 2 seconds with optimized ML pipelines.",
         "#F59E0B33", "#F59E0B44"),
    ]

    cols = streamlit_module.columns(3, gap="medium")
    for col, (icon, title, desc, bg, border) in zip(cols, features):
        with col:
            streamlit_module.markdown(
                f'<div class="fc-wrap">'
                f'<div class="fc-icon" style="background:linear-gradient(135deg,{bg},{bg[:-2]}11);border:1px solid {border};">{icon}</div>'
                f'<div style="font-size:1rem;font-weight:700;color:#fff !important;margin-bottom:6px;">{title}</div>'
                f'<div style="font-size:0.82rem;color:#a1a1aa !important;line-height:1.6;">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    streamlit_module.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)

    # ─── Stats Bar (using Streamlit columns) ───
    stats = [
        ("🎬", "50K+", "Movies Indexed"),
        ("🧠", "3", "ML Models"),
        ("⚡", "<2s", "Avg Response"),
        ("🎯", "94%", "Accuracy"),
    ]
    stat_cols = streamlit_module.columns(4, gap="small")
    for col, (icon, value, label) in zip(stat_cols, stats):
        with col:
            streamlit_module.markdown(
                f'<div style="text-align:center;padding:16px 8px;background:rgba(255,255,255,0.03);border-radius:16px;border:1px solid rgba(255,255,255,0.06);">'
                f'<div style="font-size:1.3rem;margin-bottom:4px;">{icon}</div>'
                f'<div class="sv">{value}</div>'
                f'<div class="sl">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    streamlit_module.markdown("<div style='height:2rem;'></div>", unsafe_allow_html=True)

    # ─── CTA Button ───
    streamlit_module.markdown('<div class="cta-section">', unsafe_allow_html=True)
    _, c2, _ = streamlit_module.columns([1.2, 1, 1.2])
    with c2:
        clicked = _wide_button(streamlit_module, "🚀  Start Discovering", key="landing_get_started")
    streamlit_module.markdown("</div>", unsafe_allow_html=True)

    # ─── Scroll indicator ───
    streamlit_module.markdown(
        '<div style="text-align:center;margin-top:32px;">'
        '<div style="font-size:0.62rem;text-transform:uppercase;letter-spacing:0.2em;color:#52525b !important;margin-bottom:6px;">Scroll</div>'
        '<div style="width:20px;height:34px;border-radius:12px;border:2px solid #3f3f46;display:inline-flex;align-items:flex-start;justify-content:center;padding-top:5px;">'
        '<div class="sd"></div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ─── Footer ───
    streamlit_module.markdown(
        '<div style="text-align:center;padding:20px 0 8px 0;color:#3f3f46 !important;font-size:0.75rem;">'
        "Built with 🧠 Machine Learning, NLP &amp; ❤️ &middot; CineVerse &copy; 2026"
        '</div>',
        unsafe_allow_html=True,
    )

    return clicked
