# ── Confiscore Poster Generator v5 — Bold Design ─────────────────────────────
# Split panels · Hero numbers · Strong color fills · Clear focal points
# ─────────────────────────────────────────────────────────────────────────────

import base64, io, os, math, re, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
FONT_DIR  = os.path.join(BASE_DIR, 'fonts')
LOGO_PATH = os.path.join(FONT_DIR, 'logo.png')

_FONT_REG  = [os.path.join(FONT_DIR, 'Inter-Variable.ttf'),
              "C:/Windows/Fonts/segoeui.ttf",  "C:/Windows/Fonts/calibri.ttf",  "C:/Windows/Fonts/arial.ttf"]
_FONT_BOLD = [os.path.join(FONT_DIR, 'Inter-Bold.ttf'),
              "C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/calibrib.ttf", "C:/Windows/Fonts/arialbd.ttf"]
_FONT_LITE = [os.path.join(FONT_DIR, 'Inter-Light.ttf'),
              "C:/Windows/Fonts/segoeuil.ttf", "C:/Windows/Fonts/calibril.ttf", "C:/Windows/Fonts/arial.ttf"]

def font(size, weight='regular'):
    paths = _FONT_BOLD if weight == 'bold' else (_FONT_LITE if weight == 'light' else _FONT_REG)
    for p in paths:
        try:    return ImageFont.truetype(p, size)
        except: pass
    return ImageFont.load_default()

# ── Palette ────────────────────────────────────────────────────────────────────
BG     = (5,   8,  22)
BG2    = (10,  16, 40)
BG3    = (16,  26, 62)
BG4    = (22,  38, 88)

ACCENT  = (59,  91, 219)
ACCENT2 = (99, 131, 255)
GREEN   = (56, 239, 125)
DKGREEN = (14,  70,  38)
CYAN    = (56, 200, 239)
DKCYAN  = (10,  60,  80)
ORANGE  = (255, 160,  50)
DKORANGE= (80,  40,  10)
PURPLE  = (180, 100, 255)
DKPURPLE= (50,  20,  90)
RED     = (255,  75,  90)

WHITE       = (255, 255, 255)
WHITE_DIM   = (195, 208, 238)
WHITE_MUTED = (105, 122, 168)
BORDER2     = (38,  62, 138)

BAND_COLORS = {
    'critical': (220, 50,  50),
    'at-risk':  (255, 140, 50),
    'stable':   (240, 200, 40),
    'strong':   (50,  200, 100),
    'champion': (56,  239, 125),
}

# ── Core helpers ───────────────────────────────────────────────────────────────

def img_to_b64(img):
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=96)
    buf.seek(0)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.read()).decode()

def radial_glow(img, cx, cy, r, color, alpha=60):
    glow  = Image.new('RGBA', img.size, (0,0,0,0))
    gd    = ImageDraw.Draw(glow)
    for i in range(16, 0, -1):
        a   = int(alpha * (i/16)**2.4)
        rad = int(r * i/16)
        gd.ellipse([cx-rad, cy-rad, cx+rad, cy+rad], fill=(*color, a))
    blurred = glow.filter(ImageFilter.GaussianBlur(radius=r//5))
    return Image.alpha_composite(img.convert('RGBA'), blurred).convert('RGB')

def noise_overlay(img, strength=4):
    W, H = img.size
    noise = Image.new('RGBA', (W,H), (0,0,0,0))
    nd    = ImageDraw.Draw(noise)
    rng   = random.Random(7)
    for _ in range(W*H//60):
        v = rng.randint(180,255)
        nd.point((rng.randint(0,W-1), rng.randint(0,H-1)), fill=(v,v,v,rng.randint(0,strength)))
    return Image.alpha_composite(img.convert('RGBA'), noise).convert('RGB')

def wrap(draw, text, f, maxw):
    words = text.split()
    lines, cur = [], []
    for w in words:
        test = ' '.join(cur + [w])
        if draw.textbbox((0,0), test, font=f)[2] <= maxw:
            cur.append(w)
        else:
            if cur: lines.append(' '.join(cur))
            cur = [w]
    if cur: lines.append(' '.join(cur))
    return lines

def extract_metric(metric):
    """Return (number_str, label_str) from a metric string like '40% reduction in bad hires'."""
    m = re.search(r'[\d]+(?:\.\d+)?[x%]?', metric)
    if m:
        num  = m.group()
        rest = metric[m.end():].strip(' –-—.,').strip()
        return num, rest
    return metric[:8], ""

def logo(img, x, y, w=130):
    try:
        l  = Image.open(LOGO_PATH).convert('RGBA')
        h2 = int(w * l.height / l.width)
        l  = l.resize((w, h2), Image.LANCZOS)
        img.paste(l, (x, y), l)
    except:
        pass

def tag_pill(draw, x, y, text, color):
    f  = font(13)
    bb = draw.textbbox((0,0), text, font=f)
    w  = (bb[2]-bb[0]) + 26
    draw.rounded_rectangle([x, y, x+w, y+24], radius=12,
                            fill=(*color, 16), outline=(*color, 110), width=1)
    draw.text((x+13, y+5), text, font=f, fill=color)
    return x + w + 12

def dot_grid(draw, W, H, x0=0, y0=0, spacing=36, color=WHITE, alpha=7):
    for gy in range(y0, H, spacing):
        for gx in range(x0, W, spacing):
            draw.ellipse([gx-1, gy-1, gx+1, gy+1], fill=(*color, alpha))

def section_line(draw, x0, x1, y, color, alpha=55):
    draw.line([(x0,y),(x1,y)], fill=(*color, alpha), width=1)

def score_ring(draw, cx, cy, score, r=80):
    draw.ellipse([cx-r-7, cy-r-7, cx+r+7, cy+r+7], outline=(*ACCENT, 14), width=12)
    draw.ellipse([cx-r,   cy-r,   cx+r,   cy+r  ], outline=(*BORDER2, 95), width=10)
    c = RED if score<200 else ORANGE if score<450 else (240,200,40) if score<650 else (50,200,100) if score<850 else GREEN
    draw.arc([cx-r,cy-r,cx+r,cy+r], start=-90, end=-90+int(score/1000*360), fill=c, width=10)
    draw.text((cx, cy-12), str(score), font=font(42,'bold'), fill=WHITE,       anchor='mm')
    draw.text((cx, cy+20), '/1000',    font=font(15),        fill=WHITE_MUTED, anchor='mm')


# ── Canvas factory ─────────────────────────────────────────────────────────────

def dark_canvas(W, H, accent):
    """Standard dark canvas with gradient, arc decoration, glow."""
    img  = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(img, 'RGBA')
    # Vertical gradient
    for i in range(H):
        t = i/H
        draw.line([(0,i),(W,i)], fill=(*BG2, int(65*(1-t*0.6))))
    # Decorative arcs top-right
    cr = int(min(W,H)*0.78)
    draw.arc([W-cr, -cr//2, W+cr//2, cr], start=128, end=215, fill=(*accent,55), width=2)
    draw.arc([W-cr+26, -cr//2+26, W+cr//2-26, cr-26], start=128, end=215, fill=(*accent,24), width=1)
    # Small arc bottom-left
    sr = int(min(W,H)*0.35)
    draw.arc([-sr//2, H-sr, sr//2, H+sr//2], start=295, end=35, fill=(*ACCENT2,20), width=1)
    # Glow
    img = radial_glow(img, W,    0,      int(W*0.50), accent, alpha=18)
    img = radial_glow(img, 0,    H,      int(W*0.30), ACCENT, alpha=10)
    draw = ImageDraw.Draw(img, 'RGBA')
    dot_grid(draw, W, H)
    return img, draw

def split_canvas(W, H, accent, panel_w, dark_color):
    """Canvas with colored left panel + dark right panel."""
    img  = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(img, 'RGBA')
    # Left panel fill — gradient from darker to BG
    for x in range(panel_w + 30):
        t = x / (panel_w + 30)
        r = int(dark_color[0] * (1-t*0.5))
        g = int(dark_color[1] * (1-t*0.5))
        b = int(dark_color[2] * (1-t*0.5))
        draw.line([(x,0),(x,H)], fill=(r,g,b,255))
    # Glow in left panel
    img = radial_glow(img, panel_w//2, H//2, panel_w, accent, alpha=28)
    # Glow top-right of right panel
    img = radial_glow(img, W, 0, int(W*0.45), accent, alpha=12)
    draw = ImageDraw.Draw(img, 'RGBA')
    # Dot grid on right panel only
    dot_grid(draw, W, H, x0=panel_w+20, color=WHITE, alpha=6)
    # Subtle vertical separator
    for y in range(H):
        t = abs(y/H - 0.5) * 2
        draw.line([(panel_w, y),(panel_w+1, y)], fill=(*accent, int(55*(1-t*0.7))))
    return img, draw

def footer_dark(draw, img, W, H, pad=55):
    draw.line([(pad, H-65),(W-pad, H-65)], fill=(*BORDER2, 60), width=1)
    logo(img, pad, H-54, 120)
    draw.text((W-pad, H-48), "Confidence Is the New KPI", font=font(13), fill=WHITE_MUTED, anchor='ra')
    draw.text((W-pad, H-28), "confiscore.com",             font=font(13), fill=ACCENT2,    anchor='ra')

def footer_panel(draw, img, panel_w, H, accent):
    """Footer that sits inside the left panel."""
    logo(img, 22, H-54, 110)
    draw.text((panel_w//2, H-20), "confiscore.com", font=font(12), fill=(*accent,160), anchor='mm')


# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE 1 — STAT  (hero number + supporting content)
# ══════════════════════════════════════════════════════════════════════════════
def tpl_stat(stat, stat_label, headline, body, tag="CONFISCORE INSIGHT", platform='li'):
    W, H = (1080,1080) if platform=='ig' else (1200,627)
    img, draw = dark_canvas(W, H, ACCENT)
    P = 60

    if platform == 'ig':
        # Hero number takes top half
        tag_pill(draw, P, P, tag, ACCENT2)
        # Big glow behind number
        img = radial_glow(img, W//2, int(H*0.32), 280, ACCENT2, alpha=30)
        draw = ImageDraw.Draw(img, 'RGBA')
        draw.text((W//2+3, int(H*0.32)+3), stat, font=font(155,'bold'), fill=(0,0,0,90), anchor='mm')
        draw.text((W//2,   int(H*0.32)),   stat, font=font(155,'bold'), fill=ACCENT2,    anchor='mm')
        draw.text((W//2, int(H*0.32)+98),  stat_label.upper(), font=font(22), fill=(*ACCENT2,180), anchor='mm')
        section_line(draw, P, W-P, int(H*0.52), ACCENT2, alpha=60)
        y = int(H*0.54)
        for line in wrap(draw, headline, font(50,'bold'), W-P*2)[:2]:
            draw.text((P,y), line, font=font(50,'bold'), fill=WHITE); y += 62
        y += 6
        for line in wrap(draw, body, font(27), W-P*2)[:3]:
            draw.text((P,y), line, font=font(27), fill=WHITE_DIM); y += 38
    else:
        MID = int(W*0.42)
        tag_pill(draw, P, P, tag, ACCENT2)
        # Left: giant number
        img = radial_glow(img, MID//2, H//2-10, 230, ACCENT2, alpha=28)
        draw = ImageDraw.Draw(img, 'RGBA')
        draw.text((P+3, P+48+3), stat, font=font(130,'bold'), fill=(0,0,0,90))
        draw.text((P,   P+48),   stat, font=font(130,'bold'), fill=ACCENT2)
        draw.text((P, P+195), stat_label.upper(), font=font(20), fill=(*ACCENT3,190))
        # Vertical divider
        draw.line([(MID,P+20),(MID,H-75)], fill=(*ACCENT,40), width=1)
        draw.line([(MID+2,P+20),(MID+2,H-75)], fill=(*BORDER2,55), width=1)
        # Right: headline + body
        y = P + 14
        for line in wrap(draw, headline, font(40,'bold'), W-MID-P-48)[:3]:
            draw.text((MID+44, y), line, font=font(40,'bold'), fill=WHITE); y += 52
        section_line(draw, MID+44, W-P, y+6, BORDER2, alpha=70)
        y += 22
        for line in wrap(draw, body, font(22), W-MID-P-48)[:4]:
            draw.text((MID+44, y), line, font=font(22), fill=WHITE_DIM); y += 33

    footer_dark(draw, img, W, H, P)
    return img_to_b64(noise_overlay(img))


# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE 2 — SERIES  (big number texture + numbered list)
# ══════════════════════════════════════════════════════════════════════════════
def tpl_series(number, title, points, footnote="", platform='li'):
    W, H = (1080,1080) if platform=='ig' else (1200,627)
    img, draw = dark_canvas(W, H, GREEN)
    P = 60

    # Large series number as background texture (top right)
    draw.text((W-P+10, P-30), f"#{number}", font=font(200,'bold'), fill=(*GREEN,8), anchor='ra')

    tag_pill(draw, P, P, f"CONFISCORE SERIES — {number}", GREEN)
    y = P + 52

    fsz = 50 if platform=='ig' else 40
    for line in wrap(draw, title, font(fsz,'bold'), W-P*2)[:2]:
        draw.text((P,y), line, font=font(fsz,'bold'), fill=WHITE); y += fsz+14
    section_line(draw, P, W-P, y+4, GREEN, alpha=50)
    y += 26

    COLS = [ACCENT2, GREEN, CYAN, ORANGE, PURPLE]
    n    = len(points[:5])
    rh   = max(50, (H-y-82) // max(n,1))
    pf   = 23 if platform=='ig' else 20

    for i, pt in enumerate(points[:5]):
        if y > H-100: break
        nc = COLS[i % len(COLS)]
        # Colored bar instead of card
        draw.rounded_rectangle([P, y, P+4, y+rh-8], radius=2, fill=(*nc,220))
        # Number circle
        cx2, cy2 = P+24, y+(rh-8)//2
        draw.ellipse([cx2-15,cy2-15,cx2+15,cy2+15], fill=(*nc,18), outline=(*nc,170), width=2)
        draw.text((cx2,cy2), str(i+1), font=font(17,'bold'), fill=nc, anchor='mm')
        # Text
        plines = wrap(draw, pt, font(pf), W-P*2-60)
        py = y + (rh-8)//2 - (min(len(plines),2)*(pf+6))//2
        for pl in plines[:2]:
            draw.text((P+48, py), pl, font=font(pf), fill=WHITE_DIM if i else WHITE); py += pf+6
        y += rh

    if footnote:
        draw.text((P, H-90), footnote[:90], font=font(15), fill=WHITE_MUTED)

    footer_dark(draw, img, W, H, P)
    return img_to_b64(noise_overlay(img))


# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE 3 — COMPARISON  (two strong colored columns)
# ══════════════════════════════════════════════════════════════════════════════
def tpl_comparison(title, left_label, left_pts, right_label, right_pts, platform='li'):
    W, H = (1080,1080) if platform=='ig' else (1200,627)
    img, draw = dark_canvas(W, H, ACCENT)
    P = 50; MID = W//2

    fsz = 34 if platform=='ig' else 28
    y   = P+4
    for line in wrap(draw, title, font(fsz,'bold'), W-P*2)[:2]:
        draw.text((W//2,y), line, font=font(fsz,'bold'), fill=WHITE, anchor='ma'); y += fsz+10
    section_line(draw, P, W-P, y+6, BORDER2)
    col_y = y + 22

    # Strong colored header panels
    draw.rounded_rectangle([P,   col_y, MID-12, col_y+50], radius=8, fill=(*RED,   30))
    draw.rounded_rectangle([P,   col_y, MID-12, col_y+50], radius=8, outline=(*RED,  100), width=1)
    draw.text((P+(MID-12-P)//2, col_y+25), left_label.upper(),  font=font(18,'bold'), fill=RED,   anchor='mm')
    draw.rounded_rectangle([MID+12,col_y,W-P,col_y+50], radius=8, fill=(*GREEN,30))
    draw.rounded_rectangle([MID+12,col_y,W-P,col_y+50], radius=8, outline=(*GREEN,100), width=1)
    draw.text((MID+12+(W-P-MID-12)//2, col_y+25), right_label.upper(), font=font(18,'bold'), fill=GREEN, anchor='mm')
    draw.ellipse([MID-24,col_y+10,MID+24,col_y+40], fill=(*BG3,255), outline=(*BORDER2,180), width=2)
    draw.text((MID,col_y+25), 'VS', font=font(16,'bold'), fill=WHITE_MUTED, anchor='mm')

    y2  = col_y + 60
    n   = min(len(left_pts), len(right_pts), 4 if platform=='li' else 5)
    rh  = max(44, (H-y2-80)//max(n,1))
    pf  = 19 if platform=='li' else 21

    for i in range(n):
        if i % 2 == 0:
            draw.rectangle([P, y2, MID-12, y2+rh], fill=(*RED,  9))
            draw.rectangle([MID+12,y2,W-P,  y2+rh], fill=(*GREEN,9))
        draw.line([(P,y2),(W-P,y2)], fill=(*BORDER2,40), width=1)
        draw.text((P+12,    y2+rh//2-pf//2), '✗  '+left_pts[i][:42],  font=font(pf), fill=(215,80,85))
        draw.text((MID+18,  y2+rh//2-pf//2), '✓  '+right_pts[i][:42], font=font(pf), fill=(60,210,105))
        draw.line([(MID,y2),(MID,y2+rh)], fill=(*BORDER2,50), width=1)
        y2 += rh

    footer_dark(draw, img, W, H, P)
    return img_to_b64(noise_overlay(img))


# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE 4 — QUOTE  (centered, giant marks, author badge)
# ══════════════════════════════════════════════════════════════════════════════
def tpl_quote(quote, author="Dr. Debasis Chatterji", role="Founder & CEO, Confiscore", platform='li'):
    W, H = (1080,1080) if platform=='ig' else (1200,627)
    img, draw = dark_canvas(W, H, PURPLE)
    P = 70

    img = radial_glow(img, P+70, P+90, 250, PURPLE, alpha=26)
    draw = ImageDraw.Draw(img, 'RGBA')
    draw.text((P-12, P-45), '“', font=font(190,'bold'), fill=(*PURPLE,52))

    fsz   = 40 if platform=='ig' else 34
    lines = wrap(draw, quote, font(fsz,'bold'), W-P*2)
    y     = P+70
    for line in lines[:5]:
        draw.text((P+2,y+2), line, font=font(fsz,'bold'), fill=(0,0,0,85))
        draw.text((P,  y),   line, font=font(fsz,'bold'), fill=WHITE)
        y += fsz+16

    draw.text((W-P-32,y+8), '”', font=font(110,'bold'), fill=(*PURPLE,44))
    y += 52

    # Author badge
    draw.rounded_rectangle([P, y, P+350, y+70], radius=10,
                            fill=(*BG2,230), outline=(*PURPLE,70), width=1)
    draw.rounded_rectangle([P, y, P+5, y+70], radius=2, fill=(*PURPLE,220))
    draw.text((P+20, y+14), author, font=font(22,'bold'), fill=ACCENT2)
    draw.text((P+20, y+40), role,   font=font(16),        fill=WHITE_MUTED)

    footer_dark(draw, img, W, H, P)
    return img_to_b64(noise_overlay(img))


# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE 5 — SCORE SHOWCASE
# ══════════════════════════════════════════════════════════════════════════════
def tpl_score(score, band, headline, description, use_case="", platform='li'):
    bc = BAND_COLORS.get(band.lower(), GREEN)
    W, H = (1080,1080) if platform=='ig' else (1200,627)
    img, draw = dark_canvas(W, H, bc)
    P = 65

    if platform == 'ig':
        tag_pill(draw, P, P, "CONFIDENCE SCORE", bc)
        img = radial_glow(img, W//2, 320, 300, bc, alpha=32)
        draw = ImageDraw.Draw(img, 'RGBA')
        score_ring(draw, W//2, 320, score, r=118)
        draw.rounded_rectangle([W//2-70,468,W//2+70,506], radius=20,
                                fill=(*bc,30), outline=(*bc,100), width=1)
        draw.text((W//2,487), band.upper(), font=font(26,'bold'), fill=bc, anchor='mm')
        section_line(draw, P, W-P, 524, BORDER2)
        y = 544
        for line in wrap(draw, headline, font(44,'bold'), W-P*2)[:2]:
            draw.text((P,y), line, font=font(44,'bold'), fill=WHITE); y += 56
        for line in wrap(draw, description, font(26), W-P*2)[:3]:
            draw.text((P,y), line, font=font(26), fill=WHITE_DIM); y += 36
    else:
        MID = 370
        tag_pill(draw, P, P, "CONFIDENCE SCORE", bc)
        img = radial_glow(img, MID//2+P//2, H//2-24, 210, bc, alpha=32)
        draw = ImageDraw.Draw(img, 'RGBA')
        score_ring(draw, MID//2+P//2, H//2-28, score, r=98)
        draw.rounded_rectangle([MID//2+P//2-52,H//2+82,MID//2+P//2+52,H//2+116],
                                radius=17, fill=(*bc,30), outline=(*bc,100), width=1)
        draw.text((MID//2+P//2,H//2+99), band.upper(), font=font(20,'bold'), fill=bc, anchor='mm')
        draw.line([(MID,P+20),(MID,H-76)], fill=(*BORDER2,80), width=1)
        y = P+12
        for line in wrap(draw, headline, font(38,'bold'), W-MID-P-44)[:2]:
            draw.text((MID+42,y), line, font=font(38,'bold'), fill=WHITE); y += 50
        section_line(draw, MID+42, W-P, y+6, BORDER2)
        y += 22
        for line in wrap(draw, description, font(21), W-MID-P-44)[:4]:
            draw.text((MID+42,y), line, font=font(21), fill=WHITE_DIM); y += 32
        if use_case:
            draw.text((MID+42,y+10), f'Use case: {use_case}', font=font(17), fill=CYAN)

    footer_dark(draw, img, W, H, P)
    return img_to_b64(noise_overlay(img))


# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE 6 — INDUSTRY SPOTLIGHT
# ══════════════════════════════════════════════════════════════════════════════
def tpl_industry(industry, headline, use_cases, stat="", stat_label="", platform='li'):
    W, H = (1080,1080) if platform=='ig' else (1200,627)
    img, draw = dark_canvas(W, H, CYAN)
    P = 65

    tag_pill(draw, P, P, f"CONFISCORE FOR {industry.upper()}", CYAN)
    y = P+52
    fsz = 46 if platform=='ig' else 38
    for line in wrap(draw, headline, font(fsz,'bold'), W-P*2)[:2]:
        draw.text((P,y), line, font=font(fsz,'bold'), fill=WHITE); y += fsz+14
    section_line(draw, P, W-P, y+4, CYAN, alpha=48)
    y += 24

    n   = len(use_cases[:4])
    rh  = max(50,(H-y-(130 if stat else 80))//max(n,1))
    ucf = 22 if platform=='ig' else 19

    for i, uc in enumerate(use_cases[:4]):
        if y > H-110: break
        draw.rounded_rectangle([P, y, P+4, y+rh-8], radius=2, fill=(*CYAN,210))
        draw.text((P+18, y+(rh-8)//2-ucf//2), '→', font=font(20,'bold'), fill=CYAN)
        for line in wrap(draw, uc, font(ucf), W-P*2-50)[:1]:
            draw.text((P+46, y+(rh-8)//2-ucf//2), line, font=font(ucf), fill=WHITE_DIM)
        y += rh

    if stat:
        draw.rounded_rectangle([P,H-116,P+290,H-74], radius=8,
                                fill=(*CYAN,18), outline=(*CYAN,80), width=1)
        draw.text((P+16,H-108), stat,       font=font(26,'bold'), fill=CYAN)
        draw.text((P+16,H-82),  stat_label, font=font(14),        fill=WHITE_MUTED)

    footer_dark(draw, img, W, H, P)
    return img_to_b64(noise_overlay(img))


# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE 7 — COGNITIVE BIAS
# ══════════════════════════════════════════════════════════════════════════════
def tpl_bias(bias_name, definition, business_impact, how_confiscore_fixes, series_num="", platform='li'):
    W, H = (1080,1080) if platform=='ig' else (1200,627)
    img, draw = dark_canvas(W, H, PURPLE)
    P = 65

    if series_num:
        tag_pill(draw, P, P, f"COGNITIVE BIAS SERIES — {series_num}", PURPLE)
    y = P+52

    img = radial_glow(img, W-P-80, P+90, 200, PURPLE, alpha=26)
    draw = ImageDraw.Draw(img, 'RGBA')

    bnf = 46 if platform=='ig' else 36
    draw.text((P+2,y+2), bias_name.upper(), font=font(bnf,'bold'), fill=(0,0,0,85))
    draw.text((P,  y),   bias_name.upper(), font=font(bnf,'bold'), fill=PURPLE)
    y += bnf+16
    section_line(draw, P, W-P, y, BORDER2)
    y += 20

    sections = [
        ("WHAT IT IS",              WHITE_MUTED, definition,          WHITE_DIM),
        ("BUSINESS IMPACT",         ORANGE,      business_impact,     WHITE_DIM),
        ("HOW CONFISCORE FIXES IT", GREEN,       how_confiscore_fixes, WHITE),
    ]
    tf  = 22 if platform=='ig' else 19
    sh  = (H - y - 80) // 3

    for lbl, lc, txt, tc in sections:
        draw.rounded_rectangle([P, y, P+4, y+sh-8], radius=2, fill=(*lc,220))
        draw.text((P+14, y+8), lbl, font=font(12,'bold'), fill=lc)
        ty = y+28
        for line in wrap(draw, txt, font(tf), W-P*2-22)[:2]:
            draw.text((P+14,ty), line, font=font(tf), fill=tc); ty += tf+8
        y += sh

    footer_dark(draw, img, W, H, P)
    return img_to_b64(noise_overlay(img))


# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE 8 — 5 REASONS
# ══════════════════════════════════════════════════════════════════════════════
def tpl_reasons(title, reasons, cta="", platform='li'):
    W, H = (1080,1080) if platform=='ig' else (1200,627)
    img, draw = dark_canvas(W, H, ACCENT)
    P = 65

    tag_pill(draw, P, P, "TOP REASONS", ACCENT2)
    y = P+52
    fsz = 44 if platform=='ig' else 36
    for line in wrap(draw, title, font(fsz,'bold'), W-P*2)[:2]:
        draw.text((P,y), line, font=font(fsz,'bold'), fill=WHITE); y += fsz+14
    section_line(draw, P, W-P, y+4, ACCENT, alpha=48)
    y += 24

    COLS = [ACCENT2, GREEN, CYAN, ORANGE, PURPLE]
    n    = len(reasons[:5])
    rh   = max(50,(H-y-(108 if cta else 82))//max(n,1))
    rf   = 22 if platform=='ig' else 19

    for i, reason in enumerate(reasons[:5]):
        if y > H-100: break
        nc = COLS[i]
        draw.rounded_rectangle([P, y, P+4, y+rh-8], radius=2, fill=(*nc,220))
        bx,by = P+16, y+(rh-8)//2-18
        draw.rounded_rectangle([bx,by,bx+36,by+36], radius=7,
                                fill=(*nc,25), outline=(*nc,190), width=1)
        draw.text((bx+18,by+18), str(i+1), font=font(18,'bold'), fill=WHITE, anchor='mm')
        rlines = wrap(draw, reason, font(rf), W-P*2-62)
        ry = y+(rh-8)//2-(min(len(rlines),2)*(rf+6))//2
        for rl in rlines[:2]:
            draw.text((P+62,ry), rl, font=font(rf), fill=WHITE_DIM); ry += rf+6
        y += rh

    if cta:
        draw.text((P, H-86), cta, font=font(18), fill=CYAN)

    footer_dark(draw, img, W, H, P)
    return img_to_b64(noise_overlay(img))


# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE 9 — BEFORE / AFTER  (proper split-panel)
# ══════════════════════════════════════════════════════════════════════════════
def tpl_before_after(context, before_pts, after_pts, result="", platform='li'):
    W, H = (1080,1080) if platform=='ig' else (1200,627)
    MID   = W // 2
    img, draw = dark_canvas(W, H, GREEN)
    P = 50

    # Left panel red tint, right panel green tint
    draw.rectangle([P, P+55, MID-8, H-80], fill=(*RED,  7))
    draw.rectangle([MID+8, P+55, W-P, H-80], fill=(*GREEN,7))

    tag_pill(draw, P, P, "TRANSFORMATION STORY", GREEN)
    # Context text
    cf = 22 if platform=='ig' else 18
    draw.text((W//2, P+34), context[:70], font=font(cf), fill=WHITE_DIM, anchor='mm')

    # Column headers
    y = P+60
    draw.rounded_rectangle([P,y,MID-8,y+42], radius=8, fill=(*RED,25), outline=(*RED,90), width=1)
    draw.text((P+(MID-8-P)//2,y+21), "BEFORE", font=font(18,'bold'), fill=RED, anchor='mm')
    draw.rounded_rectangle([MID+8,y,W-P,y+42], radius=8, fill=(*GREEN,25), outline=(*GREEN,90), width=1)
    draw.text((MID+8+(W-P-MID-8)//2,y+21), "AFTER CONFISCORE", font=font(18,'bold'), fill=GREEN, anchor='mm')
    y += 50

    n  = min(len(before_pts), len(after_pts), 4)
    rh = max(44,(H-y-(90 if result else 80))//max(n,1))
    pf = 18 if platform=='li' else 21

    for i in range(n):
        draw.line([(P,y),(W-P,y)], fill=(*BORDER2,45), width=1)
        draw.text((P+12,    y+rh//2-pf//2), '✗  '+before_pts[i][:40], font=font(pf), fill=(215,80,85))
        draw.text((MID+18,  y+rh//2-pf//2), '✓  '+after_pts[i][:40], font=font(pf), fill=(60,210,105))
        draw.line([(MID,y),(MID,y+rh)], fill=(*BORDER2,50), width=1)
        y += rh

    if result:
        draw.rounded_rectangle([P,H-88,W-P,H-68], radius=8, fill=(*GREEN,20), outline=(*GREEN,70), width=1)
        draw.text((W//2,H-78), f'✦  Result: {result}', font=font(18,'bold'), fill=GREEN, anchor='mm')

    footer_dark(draw, img, W, H, P)
    return img_to_b64(noise_overlay(img))


# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE 10 — TIMELINE
# ══════════════════════════════════════════════════════════════════════════════
def tpl_timeline(title, milestones, platform='li'):
    W, H = (1080,1080) if platform=='ig' else (1200,627)
    img, draw = dark_canvas(W, H, CYAN)
    P = 65

    tag_pill(draw, P, P, "CONFISCORE JOURNEY", CYAN)
    y = P+52
    fsz = 42 if platform=='ig' else 34
    for line in wrap(draw, title, font(fsz,'bold'), W-P*2)[:2]:
        draw.text((P,y), line, font=font(fsz,'bold'), fill=WHITE); y += fsz+14
    section_line(draw, P, W-P, y+4, CYAN, alpha=48)
    y += 28

    COLS = [ACCENT2, CYAN, GREEN, ORANGE, PURPLE]
    n    = len(milestones[:5])
    rh   = max(56,(H-y-82)//max(n,1))
    LX   = P+22
    ef   = 20 if platform=='ig' else 18

    for i, (period, event) in enumerate(milestones[:5]):
        if y > H-100: break
        nc = COLS[i%len(COLS)]
        if i < n-1:
            draw.line([(LX,y+26),(LX,y+rh)], fill=(*BORDER2,90), width=2)
        draw.ellipse([LX-10,y+6,LX+10,y+26], fill=(*nc,22), outline=nc, width=2)
        draw.ellipse([LX-4, y+12,LX+4, y+20], fill=nc)
        # Content row with left bar
        draw.rounded_rectangle([LX+22,y,W-P,y+rh-8], radius=8,
                                fill=(*BG2,180), outline=(*nc,40), width=1)
        draw.rounded_rectangle([LX+22,y,LX+26,y+rh-8], radius=2, fill=(*nc,200))
        draw.text((LX+36,y+8), period, font=font(14,'bold'), fill=nc)
        for line in wrap(draw, event, font(ef), W-LX-P-52)[:2]:
            draw.text((LX+36,y+30), line, font=font(ef), fill=WHITE_DIM); break
        y += rh

    footer_dark(draw, img, W, H, P)
    return img_to_b64(noise_overlay(img))


# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE 11 — DID YOU KNOW
# ══════════════════════════════════════════════════════════════════════════════
def tpl_did_you_know(fact, explanation, source="", cta="", platform='li'):
    W, H = (1080,1080) if platform=='ig' else (1200,627)
    img, draw = dark_canvas(W, H, ORANGE)
    P = 65

    draw.text((W-P+12, P-28), "?", font=font(220,'bold'), fill=(*ORANGE,9), anchor='ra')
    tag_pill(draw, P, P, "DID YOU KNOW?", ORANGE)
    img = radial_glow(img, W-P-70, P+120, 230, ORANGE, alpha=20)
    draw = ImageDraw.Draw(img, 'RGBA')

    y = P+58
    fsz = 46 if platform=='ig' else 38
    for line in wrap(draw, fact, font(fsz,'bold'), W-P*2)[:3]:
        draw.text((P+2,y+2), line, font=font(fsz,'bold'), fill=(0,0,0,90))
        draw.text((P,  y),   line, font=font(fsz,'bold'), fill=WHITE); y += fsz+14

    section_line(draw, P, W-P, y+4, ORANGE, alpha=48)
    y += 24

    ef = 24 if platform=='ig' else 20
    for line in wrap(draw, explanation, font(ef), W-P*2)[:3]:
        draw.text((P,y), line, font=font(ef), fill=WHITE_DIM); y += ef+10

    if source:
        draw.text((P,y+14), f'Source: {source}', font=font(15), fill=WHITE_MUTED)
    if cta:
        draw.rounded_rectangle([P,H-104,W-P,H-72], radius=8,
                                fill=(*ORANGE,20), outline=(*ORANGE,70), width=1)
        draw.text((W//2,H-87), cta, font=font(19,'bold'), fill=ORANGE, anchor='mm')

    footer_dark(draw, img, W, H, P)
    return img_to_b64(noise_overlay(img))


# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE 12 — PRODUCT FEATURE
# ══════════════════════════════════════════════════════════════════════════════
def tpl_feature(feature_name, what_it_does, how_it_works_pts, benefit, platform='li'):
    W, H = (1080,1080) if platform=='ig' else (1200,627)
    img, draw = dark_canvas(W, H, ACCENT)
    P = 65

    tag_pill(draw, P, P, "PRODUCT FEATURE", ACCENT2)
    y = P+52
    img = radial_glow(img, W-P-80, P+90, 220, ACCENT, alpha=26)
    draw = ImageDraw.Draw(img, 'RGBA')

    fnf = 46 if platform=='ig' else 38
    draw.text((P+2,y+2), feature_name.upper(), font=font(fnf,'bold'), fill=(0,0,0,88))
    draw.text((P,  y),   feature_name.upper(), font=font(fnf,'bold'), fill=ACCENT2)
    y += fnf+16
    section_line(draw, P, W-P, y, BORDER2)
    y += 18

    wf = 26 if platform=='ig' else 22
    for line in wrap(draw, what_it_does, font(wf), W-P*2)[:2]:
        draw.text((P,y), line, font=font(wf), fill=WHITE); y += wf+10
    y += 12

    draw.text((P,y), "HOW IT WORKS", font=font(12,'bold'), fill=WHITE_MUTED)
    y += 22
    hf = 21 if platform=='ig' else 18
    for pt in how_it_works_pts[:3]:
        if y > H-120: break
        draw.rounded_rectangle([P,y,P+4,y+hf+24], radius=2, fill=(*ACCENT2,200))
        draw.text((P+16,y+10), f'▸  {pt}', font=font(hf), fill=WHITE_DIM); y += hf+30

    if benefit:
        draw.rounded_rectangle([P,H-100,W-P,H-68], radius=8, fill=(*GREEN,20), outline=(*GREEN,70), width=1)
        draw.text((P+18,H-87), f'✦  Result: {benefit}', font=font(20,'bold'), fill=GREEN)

    footer_dark(draw, img, W, H, P)
    return img_to_b64(noise_overlay(img))


# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE 13 — CASE STUDY  (split panel — big metric left, content right)
# ══════════════════════════════════════════════════════════════════════════════
def tpl_case_study(industry, challenge, solution, result, metric="", platform='li'):
    W, H = (1080,1080) if platform=='ig' else (1200,627)

    if platform == 'li':
        PANEL = int(W * 0.34)
        img, draw = split_canvas(W, H, GREEN, PANEL, DKGREEN)

        # LEFT PANEL
        # Industry as ghost text
        draw.text((PANEL//2, H//2+20), industry.upper(),
                  font=font(52,'bold'), fill=(*WHITE,7), anchor='mm')
        # Case study label
        draw.text((PANEL//2, 38), "CASE STUDY", font=font(13,'bold'), fill=(*GREEN,160), anchor='mm')
        draw.line([(30,52),(PANEL-30,52)], fill=(*GREEN,35), width=1)

        # BIG METRIC
        if metric:
            num, rest = extract_metric(metric)
            img = radial_glow(img, PANEL//2, H//2-10, 200, GREEN, alpha=30)
            draw = ImageDraw.Draw(img, 'RGBA')
            draw.text((PANEL//2+2, H//2-18+2), num, font=font(96,'bold'), fill=(0,0,0,70), anchor='mm')
            draw.text((PANEL//2,   H//2-18),   num, font=font(96,'bold'), fill=GREEN,      anchor='mm')
            if rest:
                for i, line in enumerate(wrap(draw, rest, font(16), PANEL-44)[:3]):
                    draw.text((PANEL//2, H//2+58+i*22), line, font=font(16), fill=(*WHITE,175), anchor='mm')
        else:
            img = radial_glow(img, PANEL//2, H//2, 200, GREEN, alpha=30)
            draw = ImageDraw.Draw(img, 'RGBA')
            draw.text((PANEL//2, H//2), industry.upper(), font=font(34,'bold'), fill=GREEN, anchor='mm')

        footer_panel(draw, img, PANEL, H, GREEN)

        # RIGHT PANEL
        RX  = PANEL + 42
        RW  = W - RX - 44
        draw = ImageDraw.Draw(img, 'RGBA')
        # Decorative arc on right
        cr = int(H * 0.8)
        draw.arc([W-cr, -cr//2, W+cr//2, cr], start=130, end=210, fill=(*GREEN,40), width=2)

        y = 36
        draw.text((RX, y), f"// {industry.upper()} SECTOR",
                  font=font(13,'bold'), fill=(*WHITE_MUTED,180))
        y += 40

        sections = [
            ("⚡  CHALLENGE", ORANGE, challenge),
            ("✦  SOLUTION",   CYAN,   solution),
            ("▸  RESULT",     GREEN,  result),
        ]
        avail = H - y - 72
        sh    = avail // 3

        for idx, (lbl, nc, txt) in enumerate(sections):
            # Colored accent left bar
            draw.rounded_rectangle([RX, y, RX+4, y+sh-10], radius=2, fill=(*nc,220))
            draw.text((RX+16, y+4), lbl, font=font(13,'bold'), fill=nc)
            ty = y + 26
            tf = 21
            max_rows = max(1, (sh-36)//(tf+8))
            for line in wrap(draw, txt, font(tf), RW-10)[:max_rows]:
                if ty+tf > y+sh-12: break
                draw.text((RX+16, ty), line, font=font(tf), fill=WHITE_DIM); ty += tf+8
            y += sh
            if idx < 2:
                section_line(draw, RX, W-44, y-5, BORDER2, alpha=50)

        # Right footer
        draw.text((W-44, H-44), "confiscore.com",              font=font(13), fill=ACCENT2,    anchor='ra')
        draw.text((W-44, H-24), "Confidence Is the New KPI",   font=font(12), fill=WHITE_MUTED, anchor='ra')

    else:  # Instagram square — top panel + bottom content
        PANEL = int(H * 0.38)
        img  = Image.new('RGB', (W, H), BG)
        draw = ImageDraw.Draw(img, 'RGBA')
        # Top panel fill
        for y_row in range(PANEL+20):
            t = y_row/(PANEL+20)
            r2 = int(DKGREEN[0]*(1-t*0.5))
            g2 = int(DKGREEN[1]*(1-t*0.5))
            b2 = int(DKGREEN[2]*(1-t*0.5))
            draw.line([(0,y_row),(W,y_row)], fill=(r2,g2,b2,255))
        img = radial_glow(img, W//2, PANEL//2, W//2, GREEN, alpha=28)
        img = radial_glow(img, W,    H,       int(W*0.4), ACCENT, alpha=10)
        draw = ImageDraw.Draw(img, 'RGBA')
        dot_grid(draw, W, H, y0=PANEL+20, color=WHITE, alpha=6)

        # TOP PANEL: metric
        draw.text((W//2, 36), "CASE STUDY", font=font(14,'bold'), fill=(*GREEN,160), anchor='mm')
        if metric:
            num, rest = extract_metric(metric)
            draw.text((W//2+2, PANEL//2+2), num, font=font(110,'bold'), fill=(0,0,0,80), anchor='mm')
            draw.text((W//2,   PANEL//2),   num, font=font(110,'bold'), fill=GREEN,      anchor='mm')
            if rest:
                for i, line in enumerate(wrap(draw, rest, font(20), W-120)[:2]):
                    draw.text((W//2, PANEL//2+65+i*26), line, font=font(20), fill=(*WHITE,180), anchor='mm')
        else:
            draw.text((W//2, PANEL//2), industry.upper(), font=font(44,'bold'), fill=GREEN, anchor='mm')

        draw.line([(50,PANEL+2),(W-50,PANEL+2)], fill=(*GREEN,60), width=2)

        # BOTTOM: sections
        y = PANEL + 28
        P2 = 55
        sections = [("⚡  CHALLENGE", ORANGE, challenge),
                    ("✦  SOLUTION",   CYAN,   solution),
                    ("▸  RESULT",     GREEN,  result)]
        avail = H - y - 72
        sh    = avail // 3

        for idx, (lbl, nc, txt) in enumerate(sections):
            draw.rounded_rectangle([P2,y,P2+4,y+sh-10], radius=2, fill=(*nc,220))
            draw.text((P2+16,y+4), lbl, font=font(14,'bold'), fill=nc)
            ty = y+28
            tf = 24
            for line in wrap(draw, txt, font(tf), W-P2*2-16)[:2]:
                if ty+tf > y+sh-10: break
                draw.text((P2+16,ty), line, font=font(tf), fill=WHITE_DIM); ty += tf+8
            y += sh
            if idx < 2:
                section_line(draw, P2, W-P2, y-5, BORDER2, alpha=50)

        footer_dark(draw, img, W, H, P2)

    return img_to_b64(noise_overlay(img))


# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE 14 — MYTH VS FACT
# ══════════════════════════════════════════════════════════════════════════════
def tpl_myth_fact(topic, myths, facts, platform='li'):
    W, H = (1080,1080) if platform=='ig' else (1200,627)
    img, draw = dark_canvas(W, H, PURPLE)
    P = 50; MID = W//2

    tag_pill(draw, P, P, "MYTH VS FACT", PURPLE)
    y = P+50
    tf2 = 32 if platform=='ig' else 26
    for line in wrap(draw, topic, font(tf2,'bold'), W-P*2)[:2]:
        draw.text((P,y), line, font=font(tf2,'bold'), fill=WHITE); y += tf2+10
    section_line(draw, P, W-P, y+5, BORDER2)
    y += 22

    draw.rounded_rectangle([P,y,MID-12,y+44], radius=8, fill=(*RED,  26), outline=(*RED,  95), width=1)
    draw.text((P+(MID-12-P)//2,y+22), "MYTH", font=font(18,'bold'), fill=RED,   anchor='mm')
    draw.rounded_rectangle([MID+12,y,W-P,y+44], radius=8, fill=(*GREEN,26), outline=(*GREEN,95), width=1)
    draw.text((MID+12+(W-P-MID-12)//2,y+22), "FACT", font=font(18,'bold'), fill=GREEN, anchor='mm')
    y += 52

    n  = min(len(myths),len(facts),4)
    rh = max(50,(H-y-82)//max(n,1))
    mf = 17 if platform=='li' else 20

    for i in range(n):
        draw.line([(P,y),(W-P,y)], fill=(*BORDER2,45), width=1)
        if i%2==0:
            draw.rectangle([P,y,MID-12,y+rh], fill=(*RED,  8))
            draw.rectangle([MID+12,y,W-P,y+rh], fill=(*GREEN,8))
        m_lines = wrap(draw, '✗  '+myths[i], font(mf), MID-P-30)
        f_lines = wrap(draw, '✓  '+facts[i], font(mf), W-MID-P-30)
        draw.text((P+12,    y+rh//2-mf//2), m_lines[0][:46] if m_lines else '', font=font(mf), fill=(215,80,85))
        draw.text((MID+18,  y+rh//2-mf//2), f_lines[0][:46] if f_lines else '', font=font(mf), fill=(60,210,105))
        draw.line([(MID,y),(MID,y+rh)], fill=(*BORDER2,52), width=1)
        y += rh

    footer_dark(draw, img, W, H, P)
    return img_to_b64(noise_overlay(img))


# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE 15 — WEEKLY INSIGHT
# ══════════════════════════════════════════════════════════════════════════════
def tpl_weekly_insight(week_number, insight_title, key_thought, data_point, data_label, takeaway, platform='li'):
    W, H = (1080,1080) if platform=='ig' else (1200,627)
    img, draw = dark_canvas(W, H, CYAN)
    P = 65

    draw.text((W-P, P-12), f"W{week_number}", font=font(80,'bold'), fill=(*CYAN,12), anchor='ra')
    tag_pill(draw, P, P, f"WEEKLY INSIGHT — WEEK {week_number}", CYAN)
    y = P+52

    fsz = 46 if platform=='ig' else 38
    for line in wrap(draw, insight_title, font(fsz,'bold'), W-P*2)[:2]:
        draw.text((P,y), line, font=font(fsz,'bold'), fill=WHITE); y += fsz+14
    section_line(draw, P, W-P, y+4, CYAN, alpha=48)
    y += 22

    kf = 24 if platform=='ig' else 20
    for line in wrap(draw, key_thought, font(kf), W-P*2)[:3]:
        draw.text((P,y), line, font=font(kf), fill=WHITE_DIM); y += kf+10
    y += 14

    # Data pill
    draw.rounded_rectangle([P,y,P+260,y+72], radius=12,
                            fill=(*CYAN,18), outline=(*CYAN,80), width=1)
    draw.rounded_rectangle([P,y,P+4,y+72], radius=2, fill=(*CYAN,220))
    draw.text((P+18,y+14), data_point, font=font(30,'bold'), fill=CYAN)
    draw.text((P+18,y+50), data_label, font=font(13),        fill=WHITE_MUTED)
    y += 90

    draw.text((P,y), "TAKEAWAY", font=font(12,'bold'), fill=WHITE_MUTED); y += 20
    tf3 = 23 if platform=='ig' else 19
    for line in wrap(draw, takeaway, font(tf3), W-P*2)[:2]:
        draw.text((P,y), line, font=font(tf3), fill=GREEN); y += tf3+10

    footer_dark(draw, img, W, H, P)
    return img_to_b64(noise_overlay(img))


# ── Router ─────────────────────────────────────────────────────────────────────
TEMPLATES = {
    'stat':           tpl_stat,
    'series':         tpl_series,
    'comparison':     tpl_comparison,
    'quote':          tpl_quote,
    'score':          tpl_score,
    'industry':       tpl_industry,
    'bias':           tpl_bias,
    'reasons':        tpl_reasons,
    'before_after':   tpl_before_after,
    'timeline':       tpl_timeline,
    'did_you_know':   tpl_did_you_know,
    'feature':        tpl_feature,
    'case_study':     tpl_case_study,
    'myth_fact':      tpl_myth_fact,
    'weekly_insight': tpl_weekly_insight,
}

TEMPLATE_LIST = list(TEMPLATES.keys())

def generate_poster(template, platform, data):
    try:
        fn = TEMPLATES.get(template)
        if not fn:
            print(f"Unknown template: {template}")
            return None
        return fn(platform=platform, **data)
    except Exception as e:
        import traceback
        print(f"Poster error ({template}): {e}")
        traceback.print_exc()
        return None
