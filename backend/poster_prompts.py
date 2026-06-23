# ── Confiscore Poster Prompts ──────────────────────────────────────────────────
# Controls the visual style of every AI-generated poster.
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
     the soft spotlight behind the hero element (circle r="280", opacity 0.15).
  3. A <filter id="greenGlow"> containing <feGaussianBlur stdDeviation="8" result="blur"/>
     then <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
     — apply filter="url(#greenGlow)" to the hero number and glowing card borders.

GEOMETRY (decorative, keep subtle):
  • One radial spotlight: <circle cx="heroX" cy="heroY" r="280" fill="url(#glow)" opacity="0.15"/>
  • Faint dot grid: small <circle r="1" fill="#38EF7D" opacity="0.06"/> on a ~40px grid — behind all content.
  • Thin concentric arcs (stroke, no fill, opacity 0.08) in a corner for depth — never over text.
  • NO photos. NO human silhouettes. NO clip-art icons.

GOLDEN RULES:
  1. MAXIMUM 3 data points visible on the entire poster — choose the most powerful ones. Omit the rest.
  2. The hero element (number OR headline) must be the LARGEST thing on the canvas — at least 28% of canvas height.
  3. Every number used must come EXACTLY from the post text — never invent data.
  4. Outer margins: 52px all sides. Gutter between any two elements: 28px minimum.
  5. SVG <text> never wraps. Split into stacked <text> elements (y += font_size × 1.18 per line).
     max_chars_per_line ≈ zone_width ÷ (font_size × 0.58). NEVER exceed this.
  6. At 80–120px font: ≤ 13 chars/line. At 52–72px: ≤ 20 chars/line. At 28–40px: ≤ 32 chars/line.
  7. Shorten labels aggressively: "Candidate Confidence Score" → "Conf. Score", "Consecutive Quarters" → "Qtrs".
  8. Every text element must stay ≥ 28px from any card edge and ≥ 52px from the canvas edge.
"""

# ── Per-platform canvas sizes ─────────────────────────────────────────────────
PLATFORM_DIMS: dict[str, tuple[int, int, str]] = {
    "li": (1200, 627, "LinkedIn landscape 1200×627"),
    "fb": (1200, 630, "Facebook landscape 1200×630"),
    "ig": (1080, 1080, "Instagram square 1080×1080"),
}

# ── Voice × Platform layout directions ───────────────────────────────────────
# Edit these strings to change what each voice's poster looks like.
# Keep descriptions short — they are inserted verbatim into the Claude prompt.
VOICE_LAYOUT_HINTS: dict[str, dict[str, str]] = {
    "debasis": {
        "li": (
            "BIG STATEMENT layout:\n"
            "Left zone (x=60 to x=620): eyebrow label 'CO-FOUNDER · CONFISCORE' (13px #38EF7D uppercase, y=80); "
            "bold headline in 3 short lines (88px white font-weight=800, starting y=160, line spacing 104px); "
            "one 18px supporting sentence below (fill=#99ABFF, y after headline + 40px); "
            "a thin 2px horizontal rule in #38EF7D at 30% opacity spanning the left zone. "
            "Right zone (x=680 to x=1148): ONE large stat card (rx=18, full zone height minus 2×52px margins, "
            "fill=rgba(56,239,125,0.06), stroke=#38EF7D stroke-opacity=0.5 stroke-width=1.5, "
            "filter=url(#greenGlow)); inside: hero number (160px #38EF7D font-weight=800, centered, "
            "filter=url(#greenGlow)) + short 2-line label below (22px #99ABFF). "
            "8px left accent bar (x=0 y=0 width=8 height=full, fill=#38EF7D). "
            "Add subtle ✦ glyphs (20px #38EF7D opacity=0.12) scattered behind the left headline zone."
        ),
        "fb": (
            "BIG STATEMENT layout (same energy as LinkedIn):\n"
            "Left zone (x=60 to x=620): eyebrow + 3-line bold headline (88px) + supporting sentence. "
            "Right zone (x=680 to x=1148): ONE hero stat card with large number (160px #38EF7D, greenGlow filter). "
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
            "SPLIT DASHBOARD layout:\n"
            "Left zone (x=60 to x=560): eyebrow 'CONFISCORE · B2B SAAS' (13px #38EF7D uppercase, y=72); "
            "headline in 3 lines (64px white font-weight=700, y starting 120, line spacing 76px); "
            "2-line supporting sentence (20px #99ABFF) below headline + 28px gap; "
            "ONE hero stat inline: large number (96px #38EF7D font-weight=800) + short label beside it (18px #8FA8C0). "
            "Right zone (x=600 to x=1148): exactly 2 stat cards stacked vertically with 24px gutter "
            "(each card: rx=14, height=(canvas_h - 2×52px - 24px)/2, full zone width, "
            "fill=rgba(255,255,255,0.04), stroke=#38EF7D stroke-opacity=0.4, filter=url(#greenGlow)); "
            "inside each card: big number (100px #38EF7D centered) + SHORT label (18px #99ABFF). "
            "8px left accent bar."
        ),
        "fb": (
            "SPLIT DASHBOARD layout (same as LinkedIn):\n"
            "Left: eyebrow + 3-line headline (64px) + supporting sentence + 1 inline stat. "
            "Right: 2 stacked stat cards (100px numbers). 8px left accent bar."
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
            "DATA HERO layout:\n"
            "Center-left hero zone (x=60 to x=680, vertically centered): "
            "eyebrow stat label (14px #8FA8C0 uppercase, y=100); "
            "ONE enormous hero number (200px #38EF7D font-weight=800, filter=url(#greenGlow), y=320); "
            "short 2-line context label below it (22px #99ABFF). "
            "Right zone (x=720 to x=1148): TWO horizontal comparison bars stacked (gap=80px), "
            "each bar: label above (16px #8FA8C0), grey track rect (height=14px, width=360px, fill=#1E2D5A, rx=7), "
            "green fill rect (same height, width=track×(value/max), fill=#38EF7D, rx=7), "
            "value text at track-end+16px same baseline (18px #38EF7D font-weight=700). "
            "8px left accent bar. Radial spotlight at hero number center."
        ),
        "fb": (
            "DATA HERO layout (same as LinkedIn):\n"
            "Left: enormous hero number (200px) with context. Right: 2 comparison bars. 8px left bar."
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
            "INSIGHT QUOTE layout:\n"
            "Left zone (x=60 to x=680): radial spotlight at (340, 314); "
            "large decorative opening quote mark (120px #38EF7D opacity=0.12, y=120); "
            "quote text in 3 lines (60px white font-weight=700, y starting 180, line spacing 72px, "
            "max 20 chars/line — pick the most emotional sentence from the post); "
            "closing quote mark (120px #38EF7D opacity=0.12, right-aligned in zone); "
            "attribution line (18px #8FA8C0, y after quote+36px): '— Confiscore Insight'. "
            "Right zone (x=720 to x=1148): ONE supporting stat card (full zone width, 200px tall, "
            "centered vertically, rx=16, fill=rgba(56,239,125,0.07), stroke=#38EF7D stroke-opacity=0.45, "
            "filter=url(#greenGlow)); inside: number (100px #38EF7D centered) + label (18px #99ABFF). "
            "8px left accent bar."
        ),
        "fb": (
            "INSIGHT QUOTE layout (same as LinkedIn):\n"
            "Left: decorative quote marks + 3-line quote text + attribution. "
            "Right: ONE supporting stat card. Warm and human."
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

# ── Carousel voice directions ──────────────────────────────────────────────────
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
"Confiscore" bottom-left (x=60, y={H-24}, fill=white, font-size=20, font-weight=700)
"confiscore.com" bottom-right (x={W-60}, y={H-24}, fill=#38EF7D, font-size=13, text-anchor=end)

── QUALITY CHECK (before closing </svg>) ──────────────────────────────────────
□ <defs> contains linearGradient#bg, radialGradient#glow, filter#greenGlow
□ Background rect fills full canvas with url(#bg)
□ Radial spotlight circle present (fill=url(#glow))
□ Hero element has filter=url(#greenGlow)
□ No more than 3 data points shown
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
