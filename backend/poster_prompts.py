# ── Confiscore Poster Prompts ──────────────────────────────────────────────────
# Voice-guided AI poster layouts (architecture by Jay), adapted to PORTRAIT 1080×1350
# for LinkedIn/Facebook (best mobile-feed format) while Instagram keeps native square.
# Edit VOICE_LAYOUT_HINTS to tune how each voice's poster looks per platform.
# Edit SVG_BRAND_BLOCK to change global brand colours and SVG effects.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

# ── Shared brand / colour rules injected into every prompt ────────────────────
SVG_BRAND_BLOCK = """
COMPANY: Confiscore — B2B SaaS that measures human confidence on a 0–1000 scale.
Used by HR teams, recruiters, and business leaders to make better hiring decisions.

BRAND PALETTE (use exactly these — no deviations):
  #070B1B  background base (darkest navy)
  #0D1433  background mid
  #38EF7D  primary accent — electric green (hero numbers, borders, glows)
  #3B5BDB  electric blue (secondary accent, subtle highlights)
  #99ABFF  body / label text
  #8FA8C0  secondary / meta text
  #5A6B82  muted / "before" values
  #FFFFFF  headlines

TYPOGRAPHY: font-family="system-ui,-apple-system,Segoe UI,sans-serif" ONLY.
No @font-face. No Google Fonts. No external references of any kind.

ALWAYS define in <defs>:
  1. A linearGradient id="bg" from #070B1B (0%) to #0D1433 (100%) — fill the whole canvas.
  2. A radialGradient id="glow" — center color #38EF7D at 0%, transparent at 100% — use for
     the soft spotlight behind the hero element (circle r="300", opacity 0.15).
  3. A <filter id="greenGlow"> containing <feGaussianBlur stdDeviation="8" result="blur"/>
     then <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
     — apply filter="url(#greenGlow)" to the hero number and glowing card borders.

GEOMETRY (decorative, keep subtle):
  • One radial spotlight: <circle cx="heroX" cy="heroY" r="300" fill="url(#glow)" opacity="0.15"/>
  • Faint dot grid: small <circle r="1" fill="#38EF7D" opacity="0.06"/> on a ~40px grid — behind all content.
  • Thin concentric arcs (stroke, no fill, opacity 0.08) in a corner for depth — never over text.
  • NO photos. NO human silhouettes. NO clip-art icons.

GOLDEN RULES:
  1. MAXIMUM 3 data points visible on the entire poster — choose the most powerful ones. Omit the rest.
  2. The hero element (number OR headline) must be the LARGEST thing on the canvas — at least 26% of canvas height.
  3. Every number used must come EXACTLY from the post text — never invent data.
  4. Outer margins: 60px all sides. Gutter between any two elements: 28px minimum.
  5. SVG <text> never wraps. Split into stacked <text> elements (y += font_size × 1.18 per line).
     max_chars_per_line ≈ zone_width ÷ (font_size × 0.58). NEVER exceed this.
  6. At 80–120px font: ≤ 13 chars/line. At 52–72px: ≤ 20 chars/line. At 28–40px: ≤ 32 chars/line.
  7. Shorten labels aggressively: "Candidate Confidence Score" → "Conf. Score", "Consecutive Quarters" → "Qtrs".
  8. Every text element must stay ≥ 28px from any card edge and ≥ 60px from the canvas edge.
  9. This is a TALL canvas — compose vertically, top to bottom. Distribute content down the FULL height;
     never leave the bottom third empty and never design it like a wide landscape banner.
"""

# ── Per-platform canvas sizes ─────────────────────────────────────────────────
# Portrait 4:5 (1080×1350) dominates the most vertical space in mobile feeds and is the
# best-performing format for LinkedIn/Facebook; Instagram keeps its native square.
PLATFORM_DIMS: dict[str, tuple[int, int, str]] = {
    "li": (1080, 1350, "LinkedIn portrait 1080×1350"),
    "fb": (1080, 1350, "Facebook portrait 1080×1350"),
    "ig": (1080, 1080, "Instagram square 1080×1080"),
}

# ── Voice × Platform layout directions ───────────────────────────────────────
# li/fb are PORTRAIT 1080×1350 (vertical zones). ig is SQUARE 1080×1080.
# Edit these strings to change what each voice's poster looks like.
VOICE_LAYOUT_HINTS: dict[str, dict[str, str]] = {
    "debasis": {
        "li": (
            "BIG STATEMENT layout (portrait 1080×1350, compose top→bottom):\n"
            "TOP zone (y=60 to y=760, content x=60 to x=1020): eyebrow 'CO-FOUNDER · CONFISCORE' "
            "(14px #38EF7D uppercase letter-spacing=3, y=120); bold headline in 3-4 short lines "
            "(96px white font-weight=800, starting y=240, line spacing 112px, ≤12 chars/line); "
            "one 22px supporting sentence below the headline (fill=#99ABFF); "
            "a thin 2px #38EF7D rule at 30% opacity spanning x=60→1020 under the supporting line. "
            "BOTTOM zone (y=820 to y=1230): ONE large hero stat card (x=60, width=960, height=410, rx=20, "
            "fill=rgba(56,239,125,0.06), stroke=#38EF7D stroke-opacity=0.5 stroke-width=1.5, filter=url(#greenGlow)); "
            "inside, centered: hero number (180px #38EF7D font-weight=800, filter=url(#greenGlow)) "
            "+ a short 2-line label below it (24px #99ABFF, text-anchor=middle). "
            "8px left accent bar (x=0 y=0 width=8 height=1350 fill=#38EF7D). "
            "Scatter subtle ✦ glyphs (20px #38EF7D opacity=0.12) behind the headline. "
            "Radial spotlight centered on the hero card."
        ),
        "fb": (
            "BIG STATEMENT layout (portrait 1080×1350) — identical to the LinkedIn treatment:\n"
            "TOP: eyebrow + 3-4 line bold headline (96px) + supporting sentence + thin accent rule. "
            "BOTTOM: ONE hero stat card with a giant number (180px #38EF7D, greenGlow). "
            "8px left accent bar. Warm and direct — founder voice."
        ),
        "ig": (
            "FOUNDER QUOTE layout (square 1080×1080):\n"
            "Vertically center a bold 3-line quote (72px white font-weight=800, text-anchor=middle, x=540, "
            "lines starting around y=380): pick the most punchy sentence from the post, max 12 chars/line. "
            "Above the quote (y=260): eyebrow 'CONFISCORE · CO-FOUNDER' (13px #38EF7D uppercase letter-spacing=3). "
            "Below the quote (+120px): one accent number (100px #38EF7D font-weight=800, text-anchor=middle) "
            "with a 16px label below it (fill=#99ABFF). "
            "Decorative: two concentric arcs (stroke=#38EF7D opacity=0.08, stroke-width=1) bottom-right corner. "
            "Radial spotlight centered at (540, 540). No left accent bar on square format."
        ),
    },
    "brand": {
        "li": (
            "METRIC DASHBOARD layout (portrait 1080×1350, compose top→bottom):\n"
            "TOP zone (y=60 to y=520, content x=60 to x=1020): eyebrow 'CONFISCORE · B2B SAAS' "
            "(14px #38EF7D uppercase letter-spacing=3, y=120); headline in 2-3 lines "
            "(64px white font-weight=700, y starting 190, line spacing 76px); "
            "2-line supporting sentence (20px #99ABFF) below the headline + 28px gap. "
            "BOTTOM zone (y=560 to y=1230): exactly 2 stat cards STACKED vertically with a 28px gutter "
            "(each card: x=60, width=960, height=320, rx=16, fill=rgba(255,255,255,0.04), "
            "stroke=#38EF7D stroke-opacity=0.4, filter=url(#greenGlow)); "
            "inside each card: big number (104px #38EF7D font-weight=800, text-anchor=middle) "
            "+ a SHORT label under it (20px #99ABFF, text-anchor=middle). "
            "8px left accent bar. Radial spotlight behind the first card."
        ),
        "fb": (
            "METRIC DASHBOARD layout (portrait 1080×1350) — identical to LinkedIn:\n"
            "TOP: eyebrow + 2-3 line headline (64px) + supporting sentence. "
            "BOTTOM: 2 vertically stacked stat cards (104px numbers). 8px left accent bar."
        ),
        "ig": (
            "METRIC SHOWCASE layout (square 1080×1080):\n"
            "Top third: centered eyebrow (13px #38EF7D uppercase, y=120) + headline in 2 lines "
            "(60px white font-weight=700, text-anchor=middle, x=540, y starting 170, line spacing 72px). "
            "Center: 2 side-by-side stat cards (each 460px wide, 220px tall, gap=40px, top y=380, "
            "rx=16, fill=rgba(56,239,125,0.06), stroke=#38EF7D stroke-opacity=0.5, filter=url(#greenGlow)); "
            "each card: big number (96px #38EF7D centered) + 16px label below. "
            "Bottom: 'confiscore.com' centered (14px #38EF7D, y=980). Radial spotlight at (540,400)."
        ),
    },
    "data": {
        "li": (
            "DATA HERO layout (portrait 1080×1350, compose top→bottom):\n"
            "TOP zone (y=60 to y=720): eyebrow stat label (14px #8FA8C0 uppercase, text-anchor=middle, x=540, y=160); "
            "ONE enormous hero number (240px #38EF7D font-weight=800, text-anchor=middle, x=540, y=440, "
            "filter=url(#greenGlow)); a short 2-line context label below it (26px #99ABFF, text-anchor=middle, y≈560). "
            "BOTTOM zone (y=780 to y=1240): TWO horizontal comparison bars STACKED (first top y=840, second y=1020): "
            "each bar — label above it (18px #8FA8C0, x=100); grey track rect (x=100, width=880, height=16, rx=8, fill=#1E2D5A); "
            "green fill rect over the track (same height, width=track×value/max, rx=8, fill=#38EF7D); "
            "value text at track-end+16px on the same baseline (20px #38EF7D font-weight=700). "
            "8px left accent bar. Radial spotlight centered on the hero number."
        ),
        "fb": (
            "DATA HERO layout (portrait 1080×1350) — identical to LinkedIn:\n"
            "TOP: enormous hero number (240px) with context. BOTTOM: 2 stacked comparison bars. 8px left bar."
        ),
        "ig": (
            "STAT IMPACT layout (square 1080×1080):\n"
            "Top half: ONE enormous hero number (280px #38EF7D font-weight=800, text-anchor=middle, "
            "x=540, y=420, filter=url(#greenGlow)); eyebrow label above it (14px #8FA8C0 uppercase, y=240); "
            "short stat label below (24px #99ABFF, y=480). "
            "Lower half: TWO horizontal comparison bars (track width=680px, centered at x=540), "
            "first bar top y=560, second bar top y=660; "
            "grey track (height=12px rx=6 fill=#1E2D5A), green fill (rx=6 fill=#38EF7D), "
            "value label right of track+14px (18px #38EF7D). "
            "Radial spotlight at (540, 400). No left accent bar."
        ),
    },
    "inspiring": {
        "li": (
            "INSIGHT QUOTE layout (portrait 1080×1350, compose top→bottom):\n"
            "TOP zone (y=60 to y=860, content x=60 to x=1020): large decorative opening quote mark "
            "(150px #38EF7D opacity=0.12, x=60, y=200); quote text in 3-4 lines "
            "(64px white font-weight=700, y starting 320, line spacing 80px, max 18 chars/line — "
            "pick the most emotional sentence from the post); closing quote mark "
            "(150px #38EF7D opacity=0.12, right-aligned near x=1000); "
            "attribution line (18px #8FA8C0, below the quote+40px): '— Confiscore Insight'. "
            "BOTTOM zone (y=900 to y=1230): ONE supporting stat card (x=60, width=960, height=300, rx=18, "
            "fill=rgba(56,239,125,0.07), stroke=#38EF7D stroke-opacity=0.45, filter=url(#greenGlow)); "
            "inside, centered: number (108px #38EF7D font-weight=800) + label (20px #99ABFF). "
            "8px left accent bar. Radial spotlight upper-left behind the quote."
        ),
        "fb": (
            "INSIGHT QUOTE layout (portrait 1080×1350) — identical to LinkedIn:\n"
            "TOP: decorative quote marks + 3-4 line quote + attribution. "
            "BOTTOM: ONE supporting stat card. Warm and human. 8px left accent bar."
        ),
        "ig": (
            "QUOTE VISUAL layout (square 1080×1080):\n"
            "Center: giant decorative opening quote (180px #38EF7D opacity=0.10, x=80, y=280); "
            "quote in 2 lines (72px white font-weight=700, text-anchor=middle, x=540, "
            "y=380 and y=468, max 14 chars/line); "
            "giant closing quote (180px #38EF7D opacity=0.10, right-aligned x=960, y=540); "
            "attribution (18px #8FA8C0, text-anchor=middle, x=540, y=560): '— Confiscore'; "
            "ONE small stat card bottom-center (460px wide, 120px tall, y=680, rx=14, "
            "fill=rgba(56,239,125,0.07), stroke=#38EF7D stroke-opacity=0.45): "
            "number (64px #38EF7D centered) + label (15px #99ABFF). "
            "Soft vertical gradient overlay (fill from rgba(7,11,27,0) at top to rgba(7,11,27,0.4) at bottom). "
            "Radial spotlight at (540, 430). No left accent bar."
        ),
    },
}

# ── Carousel voice directions (square 1080×1080 slides) ────────────────────────
CAROUSEL_VOICE_DIRECTIONS: dict[str, str] = {
    "debasis": (
        "COVER: bold 2-line founder statement (96px white, ≤12 chars/line); eyebrow 'CO-FOUNDER · CONFISCORE' above; "
        "'Swipe →' hint below. STAT SLIDES: each stat framed personally ('I saw X → now Y'); "
        "giant number (260px #38EF7D, greenGlow filter) dominates the slide; 1-line context below. "
        "CTA: closing founder line + green pill button."
    ),
    "brand": (
        "COVER: authoritative brand headline (90px, ≤12 chars/line); eyebrow 'CONFISCORE · B2B SAAS'. "
        "STAT SLIDES: ONE metric per slide — giant number (260px #38EF7D) + short bold label + 1-line context. "
        "Premium, clean, precise. CTA: brand tagline + green pill button."
    ),
    "data": (
        "COVER: the single most impactful number from the post as the hero (140px #38EF7D) with a 1-line label. "
        "STAT SLIDES: one enormous number (260–280px #38EF7D, greenGlow filter) per slide; "
        "optional single comparison bar below it. Data dominates — minimal copy. "
        "CTA: final stat insight + green pill button."
    ),
    "inspiring": (
        "COVER: inspiring 2-line human headline (90px white, ≤12 chars/line). "
        "STAT SLIDES: each slide = quote-style insight (2 lines, 60px, centered) + supporting number below (100px #38EF7D). "
        "Narrative arc — feels like a story unfolding. "
        "CTA: emotional closing line + green pill button."
    ),
}

# ── Prompt builders ────────────────────────────────────────────────────────────

def build_single_prompt(req, W: int, H: int, platform_str: str) -> str:
    voice_key = (getattr(req, "voice", None) or "brand").strip()
    platform_key = req.platform
    primary = (req.post_text or req.description or "").strip()
    context = req.description.strip() if (req.post_text and req.description) else ""

    layout = (
        VOICE_LAYOUT_HINTS
        .get(voice_key, VOICE_LAYOUT_HINTS["brand"])
        .get(platform_key, VOICE_LAYOUT_HINTS["brand"]["li"])
    )

    return f"""You are an elite social-media graphic designer. Create a premium {platform_str} poster for Confiscore as a COMPLETE, self-contained SVG — every element rendered, nothing left as a placeholder.

{SVG_BRAND_BLOCK}

POST TEXT (the poster visualises this — use its exact numbers, never invent data):
{primary[:700]}
{f"CONTEXT: {context[:250]}" if context else ""}

CANVAS: {W}×{H} px.
Root element: <svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">

── LAYOUT DIRECTIVE (follow exactly) ──────────────────────────────────────────
{layout}

── FOOTER (always include) ────────────────────────────────────────────────────
"Confiscore" bottom-left (x=60, y={H-30}, fill=white, font-size=22, font-weight=700)
"confiscore.com" bottom-right (x={W-60}, y={H-30}, fill=#38EF7D, font-size=14, text-anchor=end)

── QUALITY CHECK (before closing </svg>) ──────────────────────────────────────
□ <defs> contains linearGradient#bg, radialGradient#glow, filter#greenGlow
□ Background rect fills full canvas with url(#bg)
□ Radial spotlight circle present (fill=url(#glow))
□ Hero element has filter=url(#greenGlow)
□ No more than 3 data points shown
□ Content fills the full height — bottom third is NOT empty
□ Every <text> fits its zone: chars × font_size × 0.58 ≤ zone_width
□ Footer present bottom-left and bottom-right

OUTPUT: Raw SVG only. Start <svg. End </svg>. No markdown. No explanation. No code fences."""


def build_carousel_prompt(req) -> str:
    voice_key = (getattr(req, "voice", None) or "brand").strip()
    primary = (req.post_text or req.description or "").strip()
    context = req.description.strip() if (req.post_text and req.description) else ""

    slide_direction = CAROUSEL_VOICE_DIRECTIONS.get(
        voice_key, CAROUSEL_VOICE_DIRECTIONS["brand"]
    )

    return f"""You are an elite designer. Build a premium LinkedIn carousel for Confiscore as ONE self-contained SVG — all slides stacked vertically, every element fully rendered.

{SVG_BRAND_BLOCK}

POST THIS CAROUSEL IS BASED ON (use exact numbers — never invent data):
{primary[:700]}
{f"CONTEXT: {context[:250]}" if context else ""}

── VOICE / SLIDE DIRECTION ─────────────────────────────────────────────────────
{slide_direction}

── STRUCTURE ───────────────────────────────────────────────────────────────────
• Each slide: exactly 1080×1080 px
• Count slides: 1 cover + 1 per key stat (max 4 stat slides) + 1 CTA = 3–6 slides total
• Stack: <g transform="translate(0, N×1080)"> for slide index N (starting at 0)
• Root: <svg width="1080" height="TOTAL" viewBox="0 0 1080 TOTAL"> — replace TOTAL with slideCount×1080

── EVERY SLIDE MUST HAVE ────────────────────────────────────────────────────────
• Full-canvas background rect fill=url(#bg)
• Radial spotlight circle fill=url(#glow) behind the hero element
• 8px left accent bar (x=0, width=8, height=1080, fill=#38EF7D)
• 72px left margin for all content
• Footer: "confiscore.com" bottom-right (x=1008, y=1056, fill=#38EF7D, font-size=13, text-anchor=end)

── COVER SLIDE (slide 0) ────────────────────────────────────────────────────────
Eyebrow label top-left (13px #38EF7D uppercase letter-spacing=3, y=100)
Bold headline 2–3 lines (96px white font-weight=800, y starting 180, ≤12 chars/line)
Subtext 1 line (20px #99ABFF, after headline+40px)
"Swipe → see the numbers" (14px #8FA8C0, after subtext+24px)
Decorative concentric arcs bottom-right corner (stroke=#38EF7D opacity=0.08 stroke-width=1)

── STAT SLIDES ──────────────────────────────────────────────────────────────────
Eyebrow "0N / SHORT LABEL" top-left (13px #38EF7D uppercase, y=100)
Giant hero number centered (260px #38EF7D font-weight=800, text-anchor=middle, x=540, filter=url(#greenGlow))
Bold stat label below number (36px white font-weight=700, text-anchor=middle)
1-line context (18px #8FA8C0, text-anchor=middle)

── CTA SLIDE (last) ─────────────────────────────────────────────────────────────
Closing headline 2 lines (80px white font-weight=700, ≤14 chars/line, text-anchor=middle, x=540)
Green pill button centered below: <rect rx="28" fill="#38EF7D" width="280" height="60"/>
Button label: "Try Confiscore →" (18px fill=#070B1B font-weight=700, text-anchor=middle, centered on button)

── QUALITY CHECK ────────────────────────────────────────────────────────────────
□ <defs> has linearGradient#bg, radialGradient#glow, filter#greenGlow
□ Root <svg> height = slideCount × 1080 (exact integer, no placeholder)
□ Each slide has its own <g transform="translate(0, N×1080)">
□ Hero numbers have filter=url(#greenGlow)
□ No text overflows its zone

OUTPUT: Raw SVG only. Start <svg. End </svg>. No markdown. No explanation. No code fences."""
