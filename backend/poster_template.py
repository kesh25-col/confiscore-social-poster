"""Deterministic Confiscore poster/carousel renderer (Pillow).

Renders the approved neon-glow template — deep navy + glowing green hero, refined
soft borders with generous padding, progress bars, insight cards, two-tone
headlines — from a structured content spec. Claude fills in the words; this file
owns the layout, so every generation looks the same polished way.

Fully server-side (no browser rasterization), so it works identically on AWS.
Requires a TrueType sans font; tries Windows Arial (local dev) then DejaVu Sans
(common on Linux — `dnf install dejavu-sans-fonts` / `apt install fonts-dejavu`).
"""
from __future__ import annotations
import secrets
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── palette ──
NAVY_TOP = (15, 27, 50); NAVY_BOT = (8, 15, 31)
GREEN = (62, 224, 126); WHITE = (238, 244, 255); MUTED = (150, 166, 198)
BLUE = (122, 152, 210); TRACK = (28, 44, 74)
CARD_FILL = (18, 34, 62); CARD_LINE = (52, 88, 80); MINI_LINE = (42, 66, 104)
DIV = (40, 58, 92); PILL = (28, 48, 84)
COLORS = {"white": WHITE, "green": GREEN}

_BOLD = ["C:/Windows/Fonts/arialbd.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf"]
_REG = ["C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf"]

def _font(bold: bool, size: int):
    for p in (_BOLD if bold else _REG):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size)   # Pillow >= 10.1 scalable fallback
    except Exception:
        return ImageFont.load_default()

def _wrap(d, text, f, mw):
    out, cur = [], ""
    for w in str(text).split():
        s = (cur + " " + w).strip()
        if d.textlength(s, font=f) <= mw:
            cur = s
        else:
            out.append(cur); cur = w
    if cur:
        out.append(cur)
    return out

def _vgrad(w, h):
    g = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / (h - 1)
        g.putpixel((0, y), tuple(int(NAVY_TOP[i] + (NAVY_BOT[i]-NAVY_TOP[i])*t) for i in range(3)))
    return g.resize((w, h)).convert("RGBA")

def _radial(img, box, blur, alpha):
    g = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse(box, fill=GREEN + (alpha,))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(blur)))

def _glow(img, xy, text, f, anchor, color=GREEN, blur=20):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text(xy, text, font=f, fill=color + (255,), anchor=anchor)
    b = layer.filter(ImageFilter.GaussianBlur(blur))
    img.alpha_composite(b); img.alpha_composite(b)
    ImageDraw.Draw(img).text(xy, text, font=f, fill=color + (255,), anchor=anchor)

def _softcard(img, box, radius, border):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(box, radius=radius, fill=CARD_FILL, outline=border, width=2)
    x0, y0, x1, _ = box
    d.line([x0 + radius, y0 + 2, x1 - radius, y0 + 2], fill=(60, 84, 120), width=1)  # bevel

def _fit(d, lines, mw, start, lo=60):
    s = start
    while s > lo:
        f = _font(True, s)
        if all(d.textlength(t, font=f) <= mw for t, _ in lines):
            return f
        s -= 4
    return _font(True, lo)

def _save(img, upload_dir: Path) -> str:
    fn = secrets.token_hex(16) + ".png"
    Path(upload_dir).mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(Path(upload_dir) / fn)
    return fn

# ── SINGLE POSTER (1080×1350, ratio 1.25 → single image) ──────────────────────
def render_single(spec: dict, upload_dir: Path) -> str:
    W, H, M = 1080, 1350, 88
    img = _vgrad(W, H)
    _radial(img, [W*0.5, -H*0.08, W*1.12, H*0.30], 140, 46)
    d = ImageDraw.Draw(img)
    head = [(t, COLORS.get(c, WHITE)) for t, c in spec["headline"]]

    d.text((M, 90), spec["label"], font=_font(True, 26), fill=GREEN)
    hf = _fit(d, head, W-2*M, start=102)
    lh = int(hf.size * 1.05); y = 158
    for text, col in head:
        if col == GREEN: _glow(img, (M, y), text, hf, "la")
        else: ImageDraw.Draw(img).text((M, y), text, font=hf, fill=col, anchor="la")
        y += lh
    d = ImageDraw.Draw(img); y += 16
    for ln in _wrap(d, spec["sub"], _font(False, 34), W-2*M):
        d.text((M, y), ln, font=_font(False, 34), fill=BLUE); y += 46

    d.line([M, 620, W-M, 620], fill=DIV, width=2)
    gap = 26; cw = (W-2*M-gap)//2
    for i, (label, val) in enumerate(spec["cards"][:2]):
        x = M + i*(cw+gap)
        _softcard(img, [x, 648, x+cw, 648+118], 18, MINI_LINE)
        dd = ImageDraw.Draw(img)
        dd.text((x+40, 682), str(label).upper(), font=_font(False, 20), fill=MUTED)
        dd.text((x+40, 718), str(val), font=_font(True, 32), fill=WHITE)

    # hero card (fixed 800..1248), content vertically centered
    top, bottom = 800, 1248
    _softcard(img, [M, top, W-M, bottom], 28, CARD_LINE)
    cap = spec.get("cap", [])
    num_h, g1, cap_h, g2, g3, take_h, g4, pill_h = 104, 30, len(cap)*38, 26, 26, 40, 30, 46
    total = num_h+g1+cap_h+g2+2+g3+take_h+g4+pill_h
    sy = top + max(34, ((bottom-top)-total)//2)
    _glow(img, (W//2, sy+num_h//2), spec["hero"], _font(True, 108), "mm")
    d = ImageDraw.Draw(img)
    yy = sy + num_h + g1
    for ln in cap:
        d.text((W//2, yy+19), ln, font=_font(False, 30), fill=MUTED, anchor="mm"); yy += 38
    yy += g2
    d.line([M+80, yy, W-M-80, yy], fill=DIV, width=2); yy += 2 + g3
    d.text((W//2, yy+take_h//2), spec["take"], font=_font(True, 34), fill=WHITE, anchor="mm")
    yy += take_h + g4
    _pills(img, W, yy, spec.get("tags", []))

    d.text((M, H-54), "Confiscore", font=_font(True, 30), fill=WHITE)
    d.text((W-M, H-52), spec.get("url", "confiscore.com"), font=_font(False, 26), fill=MUTED, anchor="ra")
    return _save(img, upload_dir)

def _pills(img, W, cy, tags):
    if not tags: return
    d = ImageDraw.Draw(img); f = _font(False, 24); ph = 48
    ws = [d.textlength(t, font=f)+46 for t in tags]
    total = sum(ws) + 18*(len(tags)-1); x = (W-total)//2
    for t, w in zip(tags, ws):
        d.rounded_rectangle([x, cy, x+w, cy+ph], radius=ph//2, fill=PILL)
        d.text((x+w/2, cy+ph/2), t, font=f, fill=BLUE, anchor="mm")
        x += w + 18

# ── CAROUSEL (1080 × N·1080, ratio ≥ 1.8 → native carousel) ───────────────────
def render_carousel(spec: dict, upload_dir: Path) -> str:
    S, PAD = 1080, 92
    def base_slide():
        img = _vgrad(S, S)
        _radial(img, [S*0.45, -S*0.15, S*1.05, S*0.45], 120, 55)
        d = ImageDraw.Draw(img)
        d.text((PAD, S-64), "CONFISCORE", font=_font(True, 24), fill=GREEN)
        d.text((S-PAD, S-64), "confiscore.com", font=_font(False, 24), fill=MUTED, anchor="ra")
        return img, d

    def pill(d, text):
        f = _font(True, 24); tw = d.textlength(text, font=f)
        d.rounded_rectangle([PAD, 84, PAD+tw+44, 134], radius=25, fill=PILL)
        d.text((PAD+22, 109), text, font=f, fill=GREEN, anchor="lm")

    def cover(sp):
        img, d = base_slide(); pill(d, sp["label"])
        head = [(t, COLORS.get(c, WHITE)) for t, c in sp["headline"]]
        hf = _font(True, 96); y = 300; lh = 108
        for text, col in head:
            if col == GREEN: _glow(img, (PAD, y), text, hf, "lm")
            ImageDraw.Draw(img).text((PAD, y), text, font=hf, fill=col, anchor="lm")
            y += lh
        d = ImageDraw.Draw(img)
        for i, ln in enumerate(_wrap(d, sp["sub"], _font(False, 36), S-2*PAD)):
            d.text((PAD, y+10+i*48), ln, font=_font(False, 36), fill=MUTED)
        ly = 760
        d.rounded_rectangle([PAD, ly, S-PAD, ly+6], radius=3, fill=TRACK)
        d.rounded_rectangle([PAD, ly, PAD+int((S-2*PAD)*0.62), ly+6], radius=3, fill=GREEN)
        return img

    def content(sl, frac):
        img, d = base_slide(); pill(d, sl["tag"])
        hf = _font(True, 104); hl = _wrap(d, sl["hero"], hf, S-2*PAD)
        cy = 360 - (len(hl)-1)*54
        layer = Image.new("RGBA", img.size, (0,0,0,0)); ld = ImageDraw.Draw(layer)
        for i, ln in enumerate(hl):
            ld.text((S//2, cy+i*108), ln, font=hf, fill=GREEN+(255,), anchor="mm")
        blur = layer.filter(ImageFilter.GaussianBlur(22))
        img.alpha_composite(blur); img.alpha_composite(blur)
        d = ImageDraw.Draw(img)
        for i, ln in enumerate(hl):
            d.text((S//2, cy+i*108), ln, font=hf, fill=GREEN, anchor="mm")
        d.text((S//2, 520), sl["sub"], font=_font(False, 34), fill=WHITE, anchor="mm")
        # progress bar
        x, w, h = PAD, S-2*PAD, 14
        d.rounded_rectangle([x, 640, x+w, 640+h], radius=h//2, fill=TRACK)
        fw = max(h, int(w*frac))
        d.rounded_rectangle([x, 640, x+fw, 640+h], radius=h//2, fill=GREEN)
        d.ellipse([x+fw-h, 640-h//2, x+fw+h, 640+h+h//2], fill=WHITE)
        # insight card
        _softcard(img, [PAD, 730, S-PAD, 730+184], 22, CARD_LINE)
        d = ImageDraw.Draw(img)
        d.text((S//2, 730+66), sl["card_head"], font=_font(True, 34), fill=GREEN, anchor="mm")
        d.text((S//2, 730+120), sl["card_sub"], font=_font(False, 28), fill=MUTED, anchor="mm")
        return img

    def cta(sp):
        img, d = base_slide(); pill(d, sp.get("label", "THE FIX"))
        head = [(t, COLORS.get(c, WHITE)) for t, c in sp["headline"]]
        hf = _font(True, 92); lh = 108; ys = 400 - (len(head)-1)*lh//2
        for i, (text, col) in enumerate(head):
            yy = ys + i*lh
            if col == GREEN: _glow(img, (S//2, yy), text, hf, "mm")
            else: ImageDraw.Draw(img).text((S//2, yy), text, font=hf, fill=col, anchor="mm")
        d = ImageDraw.Draw(img)
        d.text((S//2, ys+len(head)*lh-6), sp["sub"], font=_font(False, 36), fill=MUTED, anchor="mm")
        btn = sp.get("button", "confiscore.com"); bf = _font(True, 34)
        bw = d.textlength(btn, font=bf)+90; bx = (S-bw)//2
        d.rounded_rectangle([bx, 760, bx+bw, 842], radius=41, fill=GREEN)
        d.text((S//2, 801), btn, font=bf, fill=(9, 20, 36), anchor="mm")
        return img

    slides = spec["slides"]
    panels = [cover(spec["cover"])]
    n = len(slides)
    for i, sl in enumerate(slides, 1):
        panels.append(content(sl, i/n))
    panels.append(cta(spec["cta"]))
    tall = Image.new("RGB", (S, S*len(panels)), NAVY_BOT)
    for i, p in enumerate(panels):
        tall.paste(p.convert("RGB"), (0, i*S))
    return _save(tall.convert("RGBA"), upload_dir)
