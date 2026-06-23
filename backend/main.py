# ── Confiscore Social Poster — Backend ───────────────────────────────────────
# Stack: FastAPI + Claude (Anthropic) + Serper + SQLite + cairosvg
# Run: uvicorn main:app --reload
# ─────────────────────────────────────────────────────────────────────────────

import os, json, re, sqlite3, base64, io, secrets, hashlib, time
from datetime import datetime
from typing import Optional
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests as req_lib
import httpx

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
    print("[OK] Loaded .env")
except ImportError:
    print("! python-dotenv not installed")

from guidelines import get_guideline, get_all_guidelines, get_facts
print("[OK] Guidelines loaded")
from poster_prompts import build_single_prompt, build_carousel_prompt, PLATFORM_DIMS as _POSTER_DIMS
print("[OK] Poster prompts loaded")

import anthropic

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
SERPER_KEY    = os.environ.get("SERPER_API_KEY")
LI_CLIENT_ID     = os.environ.get("LINKEDIN_CLIENT_ID", "")
LI_CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET", "")
FB_APP_ID        = os.environ.get("FACEBOOK_APP_ID", "")
FB_APP_SECRET    = os.environ.get("FACEBOOK_APP_SECRET", "")
IMGBB_API_KEY    = os.environ.get("IMGBB_API_KEY", "")

# ── Deployment config (all default to local dev — production sets these via env) ──
# Render injects RENDER_EXTERNAL_URL automatically, so a deploy needs zero URL config.
_render_url = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
# Where the backend itself is reachable (used for OAuth callback URLs).
BACKEND_URL  = os.environ.get("BACKEND_URL",  _render_url or "http://localhost:8000").rstrip("/")
# Where the user-facing app lives (used to redirect back after OAuth).
# In production the frontend is the same origin as the backend; locally it's Vite on 5173.
FRONTEND_URL = os.environ.get("FRONTEND_URL", _render_url or "http://localhost:5173").rstrip("/")
# Optional shared password gate — when unset (local dev) the app is open as before.
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
# Where persistent data (SQLite DB + uploads) lives. Defaults to the backend folder.
DATA_DIR = Path(os.environ.get("DATA_DIR", str(Path(__file__).parent)))
DATA_DIR.mkdir(parents=True, exist_ok=True)

if not ANTHROPIC_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY missing from .env")

claude = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
CLAUDE_MODEL = "claude-sonnet-4-6"   # best writing quality for brand voices + SVG
print("[OK] Claude ready (text + SVG posters)")
print(f"{'[OK]' if SERPER_KEY else '[!]'} Serper {'ready' if SERPER_KEY else 'missing - web search disabled'}")
print(f"{'[OK]' if LI_CLIENT_ID else '[!]'} LinkedIn {'configured' if LI_CLIENT_ID else 'not configured'}")
print(f"{'[OK]' if FB_APP_ID else '[!]'} Facebook {'configured' if FB_APP_ID else 'not configured'}")
print(f"{'[OK]' if IMGBB_API_KEY else '[!]'} imgbb {'configured' if IMGBB_API_KEY else 'not configured (needed for Instagram)'}")

# ── SQLite ─────────────────────────────────────────────────────────────────────
DB_PATH = DATA_DIR / "confiscore.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS posts (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            description   TEXT NOT NULL,
            platforms     TEXT NOT NULL,
            versions      TEXT NOT NULL,
            selected_version TEXT,
            image_path    TEXT,
            status        TEXT DEFAULT 'draft',
            created_at    TEXT NOT NULL,
            posted_at     TEXT,
            scheduled_for TEXT
        );
        CREATE TABLE IF NOT EXISTS connections (
            platform      TEXT PRIMARY KEY,
            access_token  TEXT,
            user_id       TEXT,
            username      TEXT,
            connected_at  TEXT
        );
        CREATE TABLE IF NOT EXISTS oauth_state (
            state         TEXT PRIMARY KEY,
            platform      TEXT,
            created_at    REAL
        );
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
        """)
        # Migration: add scheduled_for to existing DBs that predate it.
        cols = [r[1] for r in conn.execute("PRAGMA table_info(posts)").fetchall()]
        if "scheduled_for" not in cols:
            conn.execute("ALTER TABLE posts ADD COLUMN scheduled_for TEXT")
        conn.commit()

def get_setting(key: str) -> str:
    with get_db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else ""

def set_setting(key: str, value: str):
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
        conn.commit()

init_db()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Confiscore Social Poster")
_allowed_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
if FRONTEND_URL not in _allowed_origins:
    _allowed_origins.append(FRONTEND_URL)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# ── Optional password gate ───────────────────────────────────────────────────────
# When APP_PASSWORD is set (production), API calls require a matching token.
# When unset (local dev), the app is fully open — localhost behaviour is unchanged.
AUTH_TOKEN = hashlib.sha256(f"{APP_PASSWORD}:confiscore".encode()).hexdigest() if APP_PASSWORD else ""
# These paths stay open even with the gate on: the login check itself, the
# "is a gate enabled?" probe, and the OAuth browser redirects (which can't send headers).
_AUTH_EXEMPT = ("/api/login", "/api/auth-required", "/api/auth/")

@app.middleware("http")
async def auth_gate(request: Request, call_next):
    if APP_PASSWORD:
        path = request.url.path
        if path.startswith("/api/") and not path.startswith(_AUTH_EXEMPT):
            if request.headers.get("X-Auth-Token") != AUTH_TOKEN:
                return JSONResponse({"detail": "Authentication required"}, status_code=401)
    return await call_next(request)

class LoginRequest(BaseModel):
    password: str

@app.get("/api/auth-required")
async def auth_required():
    """Frontend asks this on load to decide whether to show the login screen."""
    return {"required": bool(APP_PASSWORD)}

@app.post("/api/login")
async def login(req: LoginRequest):
    if not APP_PASSWORD:
        return {"token": ""}          # no gate configured — let everyone in
    if req.password == APP_PASSWORD:
        return {"token": AUTH_TOKEN}
    raise HTTPException(401, "Incorrect password")

# ── Models ─────────────────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    description: str
    platforms: list[str]

class SaveDraftRequest(BaseModel):
    description: str
    platforms: list[str]
    versions: dict
    selected_version: Optional[str] = None
    image_path: Optional[str] = None
    scheduled_for: Optional[str] = None

class UpdateDraftRequest(BaseModel):
    selected_version: Optional[str] = None
    image_path: Optional[str] = None
    status: Optional[str] = None
    scheduled_for: Optional[str] = None

class PostNowRequest(BaseModel):
    post_id: int
    platforms: list[str]



# ── Web search ─────────────────────────────────────────────────────────────────
def web_search(query: str) -> str:
    if not SERPER_KEY:
        return ""
    try:
        resp = req_lib.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": 5},
            timeout=8
        )
        results = resp.json().get("organic", [])
        snippets = [f"- {r.get('title','')}: {r.get('snippet','')}" for r in results[:4]]
        return "\n".join(snippets) if snippets else ""
    except Exception as e:
        print(f"Web search failed: {e}")
        return ""

# ── Confiscore website context (cached) ──────────────────────────────────────────
_site_cache = {"text": "", "ts": 0.0}

def get_confiscore_context() -> str:
    """Fetch & cache visible text from confiscore.com to ground content in the real site."""
    if _site_cache["text"] and (time.time() - _site_cache["ts"]) < 3600:
        return _site_cache["text"]
    try:
        resp = req_lib.get("https://confiscore.com", timeout=8,
                           headers={"User-Agent": "Mozilla/5.0 (ConfiscorePoster)"})
        text = re.sub(r"<script.*?</script>", " ", resp.text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()[:2500]
        if text:
            _site_cache["text"] = text
            _site_cache["ts"] = time.time()
        return text or get_facts()
    except Exception as e:
        print(f"Confiscore site fetch failed: {e}")
        return get_facts()

def get_competitors() -> list[str]:
    """Competitor names/sites the user configured, newline- or comma-separated."""
    raw = get_setting("COMPETITORS")
    if not raw:
        return []
    parts = re.split(r"[\n,]+", raw)
    return [p.strip() for p in parts if p.strip()]

def competitor_research(topic: str) -> str:
    """Search each configured competitor against the topic and collect angles to differentiate from."""
    comps = get_competitors()
    if not comps:
        return ""
    blocks = []
    for c in comps[:4]:
        snippets = web_search(f"{c} {topic}".strip())
        if snippets:
            blocks.append(f"COMPETITOR — {c}:\n{snippets}")
    return "\n\n".join(blocks)

# ── Claude text helper ─────────────────────────────────────────────────────────
def claude_complete(prompt: str, json_mode: bool = False, temperature: float = 1.0,
                    max_tokens: int = 1500) -> str:
    user_content = prompt
    if json_mode:
        user_content += "\n\nRespond with ONLY the raw JSON object — no markdown fences, no preamble, no explanation."

    last_err = None
    for attempt in range(4):
        try:
            resp = claude.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": user_content}],
            )
            return resp.content[0].text
        except anthropic.APIStatusError as e:
            last_err = e
            if e.status_code in (429, 500, 503, 529):
                wait = 2 * (attempt + 1)
                print(f"! Claude busy ({e.status_code}, attempt {attempt+1}/4), retrying in {wait}s...")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError(f"Claude unavailable after retries: {last_err}")

def parse_json_safe(raw: str) -> dict:
    clean = re.sub(r"```json|```", "", raw).strip()
    match = re.search(r'\{.*\}', clean, re.DOTALL)
    if match:
        clean = match.group(0)
    return json.loads(clean)

def extract_svg(raw: str) -> str:
    """Pull the <svg>...</svg> block out of a model response, ignoring any prose/fences."""
    match = re.search(r'<svg.*?</svg>', raw, re.DOTALL | re.IGNORECASE)
    return match.group(0).strip() if match else ""

def svg_to_data_url(svg_text: str) -> str:
    """Return an SVG as a base64 data URL — the browser renders SVG natively, no native libs needed."""
    b64 = base64.b64encode(svg_text.encode("utf-8")).decode()
    return f"data:image/svg+xml;base64,{b64}"

# ── Stage 1: Engineer prompt ───────────────────────────────────────────────────
def engineer_prompt(description: str, platforms: list[str], search_results: str) -> str:
    facts = get_facts()
    platform_specs = []
    if "li" in platforms:
        platform_specs.append("LinkedIn: professional, 2-4 short paragraphs, no hashtag spam")
    if "fb" in platforms:
        platform_specs.append("Facebook: conversational, community-friendly, a question to drive comments")
    if "ig" in platforms:
        platform_specs.append("Instagram: engaging, 3-5 sentences, 5-8 hashtags at end")

    prompt = f"""You are a senior content strategist for Confiscore, a B2B confidence management SaaS.

{facts}

TASK: Create a detailed content brief from this raw idea.

RAW IDEA: "{description}"
PLATFORMS: {', '.join(platform_specs)}

{f'RECENT RELEVANT DATA FROM WEB:{chr(10)}{search_results}' if search_results else ''}

Write a structured brief covering:
1. Core message (1-2 sentences, specific and concrete)
2. Best hook strategy for each platform
3. Key data points or facts to include (from Confiscore or search results above)
4. Emotional insight the reader should walk away with
5. Specific dos and don'ts for this post
6. Any relevant stats or numbers to reference

Be specific and actionable. This brief goes directly to a post writer."""

    return claude_complete(prompt)

# ── Stage 2: Write 4 versions ──────────────────────────────────────────────────
def write_version(brief: str, platforms: list[str], voice_key: str, raw_description: str = "") -> dict:
    guideline = get_guideline(voice_key)
    facts = get_facts()
    platform_keys = [p for p in ["li", "fb", "ig"] if p in platforms]

    platform_rules = []
    if "li" in platforms:
        platform_rules.append(f"LINKEDIN RULES:\n{guideline['linkedin_rules']}")
    if "fb" in platforms:
        platform_rules.append(f"FACEBOOK RULES:\n{guideline['facebook_rules']}")
    if "ig" in platforms:
        platform_rules.append(f"INSTAGRAM RULES:\n{guideline['instagram_rules']}")

    keys_str = ", ".join(f'"{p}": "post text here"' for p in platform_keys)

    raw_desc_block = f"""
═══════════════════════════════════════════════════════════════
RAW INPUT FROM USER (use these EXACT numbers and facts — do not paraphrase)
═══════════════════════════════════════════════════════════════
{raw_description}
""" if raw_description else ""

    prompt = f"""{guideline['system_prompt']}

{facts}
{raw_desc_block}
═══════════════════════════════════════════════════════════════
CONTENT BRIEF FROM PROMPT ENGINEER
═══════════════════════════════════════════════════════════════
{brief}

═══════════════════════════════════════════════════════════════
PLATFORM-SPECIFIC RULES FOR THIS POST
═══════════════════════════════════════════════════════════════
{chr(10).join(platform_rules)}

═══════════════════════════════════════════════════════════════
CRITICAL RULES:
1. Use the EXACT statistics from the RAW INPUT. Never round, substitute, or invent numbers.
2. BE COMPACT. Obey the word limit in the platform rules above — a scannable post in seconds,
   NOT an essay. If you wrote more than the limit, cut it down before responding.
3. Do NOT restate the same stat in multiple ways. Each number appears once.
═══════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════
Respond ONLY with a valid JSON object. No markdown. No preamble. Nothing else.
{{ {keys_str} }}"""

    raw = claude_complete(prompt, json_mode=True)
    return parse_json_safe(raw)

# ── Generate endpoint ──────────────────────────────────────────────────────────
@app.post("/api/generate")
async def generate(req: GenerateRequest):
    if not req.description.strip():
        raise HTTPException(400, "Description cannot be empty")
    if not req.platforms:
        raise HTTPException(400, "Select at least one platform")

    # Web search for real data
    search_results = web_search(f"Confiscore confidence management HR {req.description[:80]}")

    # Stage 1: Engineer the prompt
    brief = engineer_prompt(req.description, req.platforms, search_results)

    # Stage 2: Write 4 versions in parallel
    versions = {}
    def write_one(voice_key):
        try:
            result = write_version(brief, req.platforms, voice_key, raw_description=req.description)
            return voice_key, result
        except Exception as e:
            print(f"Version {voice_key} failed: {e}")
            return voice_key, {p: f"Generation failed for {voice_key} voice." for p in req.platforms}

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(write_one, k): k for k in get_all_guidelines().keys()}
        for future in as_completed(futures):
            key, result = future.result()
            g = get_guideline(key)
            versions[key] = {
                "name": g["name"],
                "description": g["description"],
                "content": result
            }

    return {
        "versions": versions,
        "brief": brief,
        "search_used": bool(search_results)
    }

# ── Research / auto-description ──────────────────────────────────────────────────
class ResearchRequest(BaseModel):
    mode: str                       # "seed" | "auto"
    seed: Optional[str] = None      # required for "seed" mode
    platforms: list[str] = ["li"]

@app.post("/api/research")
async def research(req: ResearchRequest):
    site_context = get_confiscore_context()
    facts = get_facts()

    if req.mode == "seed":
        seed = (req.seed or "").strip()
        if not seed:
            raise HTTPException(400, "Provide a topic to research")

        web = web_search(f"{seed} confidence hiring HR recruitment trends 2026")
        comp = competitor_research(seed)

        prompt = f"""You are a B2B content strategist for Confiscore.

{facts}

CONFISCORE WEBSITE CONTENT (ground truth — use real positioning from here):
{site_context[:1500]}

SEED TOPIC FROM USER: "{seed}"

LIVE WEB RESEARCH:
{web or "(no web results)"}

{f'COMPETITOR ACTIVITY (find a differentiated angle vs these):{chr(10)}{comp}' if comp else ''}

TASK: Write a single, concrete post description (3-5 sentences) that a post writer can turn into
social content. Anchor it in Confiscore's real positioning, weave in a specific data point or angle
from the research, and stake out a position that stands apart from the competitors above.
Output ONLY the description text — no headings, no preamble."""

        description = claude_complete(prompt, temperature=0.9, max_tokens=600).strip()
        return {
            "description": description,
            "web_used": bool(web),
            "competitors_used": bool(comp),
        }

    # mode == "auto" — suggest several ready-to-use post ideas
    web = web_search("HR confidence hiring recruitment trends statistics 2026")
    comp = competitor_research("confidence measurement hiring assessment")

    prompt = f"""You are a B2B content strategist for Confiscore.

{facts}

CONFISCORE WEBSITE CONTENT:
{site_context[:1500]}

LIVE WEB RESEARCH (trends & data):
{web or "(no web results)"}

{f'COMPETITOR ACTIVITY (differentiate from these):{chr(10)}{comp}' if comp else ''}

TASK: Propose 5 distinct, timely social post ideas for Confiscore. Each must be grounded in the
research/site above and offer a fresh angle competitors are NOT covering.

Respond as a JSON object:
{{"ideas": [{{"title": "short punchy title", "description": "3-4 sentence post brief with a specific angle and data point"}}]}}"""

    raw = claude_complete(prompt, json_mode=True, temperature=0.95, max_tokens=1800)
    data = parse_json_safe(raw)
    return {
        "ideas": data.get("ideas", []),
        "web_used": bool(web),
        "competitors_used": bool(comp),
    }

# ── Image upload ───────────────────────────────────────────────────────────────
@app.post("/api/upload-image")
async def upload_image(file: UploadFile = File(...)):
    allowed = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(400, "Only JPEG, PNG, GIF, WEBP allowed")
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(400, "Image must be under 10MB")

    ext = file.filename.split(".")[-1].lower()
    fname = f"{secrets.token_hex(16)}.{ext}"
    fpath = UPLOAD_DIR / fname

    content = await file.read()
    with open(fpath, "wb") as f:
        f.write(content)

    b64 = base64.b64encode(content).decode()
    return {
        "path": str(fname),
        "url": f"data:{file.content_type};base64,{b64}"
    }

# ── Draft CRUD ─────────────────────────────────────────────────────────────────
@app.post("/api/drafts")
async def save_draft(req: SaveDraftRequest):
    now = datetime.utcnow().isoformat()
    status = "scheduled" if req.scheduled_for else "draft"
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO posts
               (description, platforms, versions, selected_version, image_path, status, created_at, scheduled_for)
               VALUES (?,?,?,?,?,?,?,?)""",
            (req.description, json.dumps(req.platforms), json.dumps(req.versions),
             req.selected_version, req.image_path, status, now, req.scheduled_for)
        )
        conn.commit()
        return {"id": cur.lastrowid, "status": status, "created_at": now}

@app.get("/api/drafts")
async def get_drafts():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM posts ORDER BY created_at DESC"
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["platforms"] = json.loads(d["platforms"])
        d["versions"] = json.loads(d["versions"])
        result.append(d)
    return result

@app.patch("/api/drafts/{post_id}")
async def update_draft(post_id: int, req: UpdateDraftRequest):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Draft not found")
        updates = {}
        if req.selected_version is not None:
            updates["selected_version"] = req.selected_version
        if req.image_path is not None:
            updates["image_path"] = req.image_path
        if req.status is not None:
            updates["status"] = req.status
        if req.scheduled_for is not None:
            # empty string clears the schedule (back to plain draft)
            updates["scheduled_for"] = req.scheduled_for or None
            if not req.status:
                updates["status"] = "scheduled" if req.scheduled_for else "draft"
        if updates:
            set_clause = ", ".join(f"{k}=?" for k in updates)
            conn.execute(f"UPDATE posts SET {set_clause} WHERE id=?",
                        (*updates.values(), post_id))
            conn.commit()
    return {"success": True}

@app.delete("/api/drafts/{post_id}")
async def delete_draft(post_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM posts WHERE id=?", (post_id,))
        conn.commit()
    return {"deleted": post_id}

# ── Platform connections ───────────────────────────────────────────────────────
@app.get("/api/connections")
async def get_connections():
    with get_db() as conn:
        rows = conn.execute("SELECT platform, username, connected_at FROM connections").fetchall()
    return {r["platform"]: {"username": r["username"], "connected_at": r["connected_at"]} for r in rows}

# ── LinkedIn OAuth ─────────────────────────────────────────────────────────────
@app.get("/api/auth/linkedin")
async def linkedin_auth():
    client_id = get_setting("LINKEDIN_CLIENT_ID") or LI_CLIENT_ID
    if not client_id:
        raise HTTPException(400, "LinkedIn not configured — add credentials via the app settings")
    state = secrets.token_urlsafe(32)
    with get_db() as conn:
        conn.execute("INSERT INTO oauth_state VALUES (?,?,?)", (state, "linkedin", time.time()))
        conn.commit()
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": f"{BACKEND_URL}/api/auth/linkedin/callback",
        "state": state,
        # OpenID Connect scopes (modern). r_liteprofile/r_emailaddress are deprecated.
        # Requires "Sign In with LinkedIn using OpenID Connect" + "Share on LinkedIn" products.
        "scope": "openid profile email w_member_social"
    }
    url = "https://www.linkedin.com/oauth/v2/authorization?" + urlencode(params)
    return RedirectResponse(url)

@app.get("/api/auth/linkedin/callback")
async def linkedin_callback(code: str, state: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM oauth_state WHERE state=? AND platform=?",
                          (state, "linkedin")).fetchone()
        if not row or time.time() - row["created_at"] > 600:
            raise HTTPException(400, "Invalid or expired OAuth state")
        conn.execute("DELETE FROM oauth_state WHERE state=?", (state,))
        conn.commit()

    client_id     = get_setting("LINKEDIN_CLIENT_ID")     or LI_CLIENT_ID
    client_secret = get_setting("LINKEDIN_CLIENT_SECRET") or LI_CLIENT_SECRET

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": f"{BACKEND_URL}/api/auth/linkedin/callback",
                "client_id": client_id,
                "client_secret": client_secret,
            }
        )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(400, f"LinkedIn token exchange failed: {token_data}")

        # OpenID Connect userinfo endpoint — returns sub (member id), name, email
        profile_resp = await client.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        profile = profile_resp.json()
        user_id = profile.get("sub", "")
        username = profile.get("name", "").strip() or "LinkedIn Account"

    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO connections
               (platform, access_token, user_id, username, connected_at)
               VALUES (?,?,?,?,?)""",
            ("linkedin", access_token, user_id, username, datetime.utcnow().isoformat())
        )
        conn.commit()

    return RedirectResponse(f"{FRONTEND_URL}/?connected=linkedin")

# ── Facebook + Instagram OAuth (Meta Graph API) ────────────────────────────────
# Both Facebook Page posting and Instagram Business posting use the same Meta app.
# One OAuth flow with combined scopes stores both connections simultaneously.

META_GRAPH = "https://graph.facebook.com/v19.0"

@app.get("/api/auth/facebook")
async def facebook_auth():
    app_id = get_setting("FACEBOOK_APP_ID") or FB_APP_ID
    if not app_id:
        raise HTTPException(400, "Facebook not configured — add FACEBOOK_APP_ID via Settings")
    state = secrets.token_urlsafe(32)
    with get_db() as conn:
        conn.execute("INSERT INTO oauth_state VALUES (?,?,?)", (state, "facebook", time.time()))
        conn.commit()
    params = {
          feat/voice-guided-posters
        "client_id":     app_id,
        "redirect_uri":  "http://localhost:8000/api/auth/facebook/callback",
        "state":         state,
        "scope":         "pages_manage_posts,pages_read_engagement,pages_show_list,"
                         "instagram_basic,instagram_content_publish,business_management",

        "client_id": app_id,
        "redirect_uri": f"{BACKEND_URL}/api/auth/instagram/callback",
        "scope": "instagram_basic,instagram_content_publish",
         master
        "response_type": "code",
    }
    url = "https://www.facebook.com/dialog/oauth?" + urlencode(params)
    return RedirectResponse(url)

@app.get("/api/auth/facebook/callback")
async def facebook_callback(code: str, state: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM oauth_state WHERE state=? AND platform=?",
                           (state, "facebook")).fetchone()
        if not row or time.time() - row["created_at"] > 600:
            raise HTTPException(400, "Invalid or expired OAuth state")
        conn.execute("DELETE FROM oauth_state WHERE state=?", (state,))
        conn.commit()

    app_id     = get_setting("FACEBOOK_APP_ID")     or FB_APP_ID
    app_secret = get_setting("FACEBOOK_APP_SECRET") or FB_APP_SECRET

    async with httpx.AsyncClient() as client:
        # Exchange code for user access token
        token_resp = await client.get(
            f"{META_GRAPH}/oauth/access_token",
            params={
                "client_id":     app_id,
                "client_secret": app_secret,
     feat/voice-guided-posters
                "redirect_uri":  "http://localhost:8000/api/auth/facebook/callback",
                "code":          code,
                "grant_type": "authorization_code",
                "redirect_uri": f"{BACKEND_URL}/api/auth/instagram/callback",
                "code": code,
     master
            }
        )
        token_data = token_resp.json()
        user_token = token_data.get("access_token")
        if not user_token:
            raise HTTPException(400, f"Facebook token exchange failed: {token_data}")

        # Fetch the Pages this user manages, including any linked Instagram account
        pages_resp = await client.get(
            f"{META_GRAPH}/me/accounts",
            params={
                "fields":       "id,name,access_token,instagram_business_account",
                "access_token": user_token,
            }
        )
        pages_data = pages_resp.json()
        pages = pages_data.get("data", [])
        if not pages:
            raise HTTPException(400,
                "No Facebook Pages found. Create a Facebook Page first, "
                "then reconnect."
            )

        # Use the first page (or let user choose later)
        page = pages[0]
        page_id    = page["id"]
        page_name  = page["name"]
        page_token = page["access_token"]

        # Check for a linked Instagram Business Account
        ig_account = page.get("instagram_business_account")

        # Fetch IG username if available
        ig_username = None
        if ig_account:
            ig_id = ig_account["id"]
            ig_resp = await client.get(
                f"{META_GRAPH}/{ig_id}",
                params={"fields": "username", "access_token": page_token}
            )
            ig_username = ig_resp.json().get("username", "Instagram Account")

    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        # Store Facebook Page connection
        conn.execute(
            "INSERT OR REPLACE INTO connections (platform, access_token, user_id, username, connected_at)"
            " VALUES (?,?,?,?,?)",
            ("facebook", page_token, page_id, page_name, now)
        )
        # Store Instagram Business Account connection (if found)
        if ig_account:
            conn.execute(
                "INSERT OR REPLACE INTO connections (platform, access_token, user_id, username, connected_at)"
                " VALUES (?,?,?,?,?)",
                ("instagram", page_token, ig_account["id"], ig_username or "Instagram Account", now)
            )
        conn.commit()

  feat/voice-guided-posters
    connected_param = "facebook" + (",instagram" if ig_account else "")
    return RedirectResponse(f"http://localhost:5173?connected={connected_param}")

# Keep a /api/auth/instagram route that redirects to the Facebook flow
# (Instagram Graph API uses the same OAuth — same app, same redirect)
@app.get("/api/auth/instagram")
async def instagram_auth():
    return RedirectResponse("/api/auth/facebook")

    return RedirectResponse(f"{FRONTEND_URL}/?connected=instagram")
 master

# ── Disconnect ─────────────────────────────────────────────────────────────────
@app.delete("/api/connections/{platform}")
async def disconnect(platform: str):
    with get_db() as conn:
        conn.execute("DELETE FROM connections WHERE platform=?", (platform,))
        conn.commit()
    return {"disconnected": platform}

# ── Post to LinkedIn ───────────────────────────────────────────────────────────
async def post_to_linkedin(text: str, image_path: Optional[str], access_token: str, user_id: str):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    author = f"urn:li:person:{user_id}"

    async with httpx.AsyncClient() as client:
        if image_path:
            image_file = UPLOAD_DIR / image_path
            if image_file.exists():
                reg_resp = await client.post(
                    "https://api.linkedin.com/v2/assets?action=registerUpload",
                    headers=headers,
                    json={
                        "registerUploadRequest": {
                            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                            "owner": author,
                            "serviceRelationships": [{
                                "relationshipType": "OWNER",
                                "identifier": "urn:li:userGeneratedContent"
                            }]
                        }
                    }
                )
                reg = reg_resp.json()
                upload_url = reg["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
                asset = reg["value"]["asset"]

                with open(image_file, "rb") as f:
                    await client.put(upload_url, content=f.read(),
                                   headers={"Authorization": f"Bearer {access_token}"})

                post_body = {
                    "author": author,
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {"text": text},
                            "shareMediaCategory": "IMAGE",
                            "media": [{"status": "READY", "media": asset}]
                        }
                    },
                    "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
                }
            else:
                post_body = _li_text_body(author, text)
        else:
            post_body = _li_text_body(author, text)

        resp = await client.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=headers,
            json=post_body
        )
        if resp.status_code not in (200, 201):
            raise Exception(f"LinkedIn post failed: {resp.text}")
        return resp.json()

def _li_text_body(author, text):
    return {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }

# ── imgbb image upload (public URL needed by Instagram Graph API) ───────────────
async def upload_to_imgbb(image_path: str) -> str:
    """Upload a local image to imgbb and return its public URL."""
    key = get_setting("IMGBB_API_KEY") or IMGBB_API_KEY
    if not key:
        raise Exception(
            "IMGBB_API_KEY not configured. "
            "Get a free key at https://api.imgbb.com and add it in Settings."
        )
    image_file = UPLOAD_DIR / image_path
    if not image_file.exists():
        raise Exception(f"Image file not found: {image_path}")
    with open(image_file, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.imgbb.com/1/upload",
            data={"key": key, "image": b64}
        )
        data = resp.json()
    if not data.get("success"):
        raise Exception(f"imgbb upload failed: {data.get('error', data)}")
    return data["data"]["url"]

# ── Post to Facebook (Graph API — Page feed) ────────────────────────────────────
async def post_to_facebook(text: str, image_path: Optional[str], access_token: str, page_id: str):
    async with httpx.AsyncClient(timeout=30) as client:
        if image_path:
            image_file = UPLOAD_DIR / image_path
            if image_file.exists():
                with open(image_file, "rb") as f:
                    img_bytes = f.read()
                # Upload photo with caption — publishes immediately
                resp = await client.post(
                    f"{META_GRAPH}/{page_id}/photos",
                    params={"access_token": access_token},
                    data={"caption": text, "published": "true"},
                    files={"source": ("image.png", img_bytes, "image/png")},
                )
                result = resp.json()
                if "id" not in result:
                    raise Exception(f"Facebook photo post failed: {result}")
                return result

        # Text-only post to page feed
        resp = await client.post(
            f"{META_GRAPH}/{page_id}/feed",
            params={"access_token": access_token},
            data={"message": text},
        )
        result = resp.json()
        if "id" not in result:
            raise Exception(f"Facebook post failed: {result}")
        return result

# ── Post to Instagram (Graph API — Business account) ───────────────────────────
async def post_to_instagram(caption: str, image_path: Optional[str], access_token: str, ig_user_id: str):
    if not image_path:
        raise Exception(
            "Instagram requires an image. Please add an image before posting to Instagram."
        )

    # Get a public URL — Instagram Graph API must fetch the image from the internet
    public_url = await upload_to_imgbb(image_path)

    async with httpx.AsyncClient(timeout=30) as client:
        # Step 1: Create media container
        media_resp = await client.post(
            f"{META_GRAPH}/{ig_user_id}/media",
            params={
                "image_url":    public_url,
                "caption":      caption,
                "access_token": access_token,
            }
        )
        media_data = media_resp.json()
        creation_id = media_data.get("id")
        if not creation_id:
            raise Exception(f"Instagram media container creation failed: {media_data}")

        # Step 2: Publish the container
        publish_resp = await client.post(
            f"{META_GRAPH}/{ig_user_id}/media_publish",
            params={
                "creation_id":  creation_id,
                "access_token": access_token,
            }
        )
        publish_data = publish_resp.json()
        if "id" not in publish_data:
            raise Exception(f"Instagram publish failed: {publish_data}")
        return publish_data

# ── Platform key mapping (frontend uses li/fb/ig; content stored with same keys)
# When posting, frontend sends full names: linkedin, facebook, instagram
PLATFORM_SHORT = {"linkedin": "li", "facebook": "fb", "instagram": "ig"}

# ── Post now ───────────────────────────────────────────────────────────────────
@app.post("/api/post")
async def post_now(req: PostNowRequest):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM posts WHERE id=?", (req.post_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Draft not found")
        post = dict(row)
        post["versions"] = json.loads(post["versions"])

        connections = {r["platform"]: dict(r) for r in
                      conn.execute("SELECT * FROM connections").fetchall()}

    if not post.get("selected_version"):
        raise HTTPException(400, "Select a version before posting")

    selected = post["versions"].get(post["selected_version"], {})
    results = {}

    PLATFORM_KEY_MAP = {"linkedin": "li", "facebook": "fb", "instagram": "ig"}

    for platform in req.platforms:
        conn_data = connections.get(platform)
        if not conn_data:
            results[platform] = {"success": False, "error": f"{platform} not connected"}
            continue
        try:
            # Map full platform name to the short content key (li/fb/ig)
            content_key = PLATFORM_KEY_MAP.get(platform, platform)
            text = selected["content"].get(content_key, "") or selected["content"].get(platform, "")
            if platform == "linkedin":
                await post_to_linkedin(text, post.get("image_path"),
                                       conn_data["access_token"], conn_data["user_id"])
            elif platform == "facebook":
                await post_to_facebook(text, post.get("image_path"),
                                       conn_data["access_token"], conn_data["user_id"])
            elif platform == "instagram":
                await post_to_instagram(text, post.get("image_path"),
                                        conn_data["access_token"], conn_data["user_id"])
            results[platform] = {"success": True}
        except Exception as e:
            results[platform] = {"success": False, "error": str(e)}

    if any(r["success"] for r in results.values()):
        with get_db() as conn:
            conn.execute("UPDATE posts SET status='published', posted_at=? WHERE id=?",
                        (datetime.utcnow().isoformat(), req.post_id))
            conn.commit()

    return results

# ── Diagram generation (Claude → SVG → PNG) ───────────────────────────────────
class DiagramRequest(BaseModel):
    description: str
    post_text: str
    platform: str = "li"

@app.post("/api/poster/diagram")
async def generate_diagram(req: DiagramRequest):
    W, H, _ = PLATFORM_DIMS.get(req.platform, PLATFORM_DIMS["li"])

    prompt = f"""You are an expert SVG infographic designer. Create a stunning, professional SVG diagram for a social media post about Confiscore — a B2B SaaS that measures candidate confidence on a 0-1000 scale to help companies make better hiring decisions.

POST CONTEXT: {req.description}
POST TEXT: {req.post_text[:400]}
CANVAS: {W}x{H}px

DESIGN RULES (follow exactly):
- Background: deep navy rectangle #070B1B filling entire canvas
- Add a large radial gradient glow blob in center-top using the accent color at ~15% opacity
- Draw 30-40 plexus network nodes: small glowing circles connected by faint lines (opacity 0.15-0.25)
- Accent color: choose ONE of [#38EF7D, #38C8EF, #B464FF, #FFA032, #3B5BDB] based on mood
- Typography: system-ui, -apple-system, sans-serif — NO external fonts
- Text hierarchy: 52-64px bold headline, 24-28px body, 16-18px labels
- Content cards: rounded rectangles (rx=12) with rgba fill and colored border with glow effect using SVG filter
- Layout fills the ENTIRE {W}x{H}px canvas — no empty space
- Bottom right: small text "Confidence Is the New KPI" in accent color, "confiscore.com" below it
- Bottom left: text "Confiscore" in white, bold, 22px

DIAGRAM STRUCTURE — pick best for content:
- Key stat/number → huge centered number (120px) with label below, 2-3 supporting cards around it
- List/steps/reasons → vertical cards with numbered accent circles on left
- Before/after → two columns with VS badge in center divider
- Central concept + points → hub circle in center with lines to surrounding cards
- Process → horizontal flow with connected rounded boxes and arrows

OUTPUT: Raw SVG only. No markdown fences. No explanation. Must start with <svg and end with </svg>. Complete and self-contained."""

    try:
        resp = claude.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=8000,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )
        svg_text = extract_svg(resp.content[0].text)
        if not svg_text:
            raise HTTPException(500, f"Claude returned no SVG: {resp.content[0].text[:120]}")

        return {"image": svg_to_data_url(svg_text), "type": "diagram", "svg": svg_text}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Diagram generation failed: {e}")


# ── Settings / Credentials ─────────────────────────────────────────────────────
class CredentialsRequest(BaseModel):
    platform: str      # "linkedin" | "instagram"
    client_id: str
    client_secret: str

@app.get("/api/settings/status")
async def settings_status():
    li_id = get_setting("LINKEDIN_CLIENT_ID") or LI_CLIENT_ID
    fb_id = get_setting("FACEBOOK_APP_ID")    or FB_APP_ID
    return {
        "linkedin":  bool(li_id),
        "facebook":  bool(fb_id),
        "instagram": bool(fb_id),   # Instagram uses the same Meta app as Facebook
    }

@app.post("/api/settings/credentials")
async def save_credentials(req: CredentialsRequest):
    if not req.client_id.strip() or not req.client_secret.strip():
        raise HTTPException(400, "Both Client ID and Client Secret are required")
    if req.platform == "linkedin":
        set_setting("LINKEDIN_CLIENT_ID",     req.client_id.strip())
        set_setting("LINKEDIN_CLIENT_SECRET", req.client_secret.strip())
    elif req.platform in ("facebook", "instagram"):
        # Facebook and Instagram share the same Meta app credentials
        set_setting("FACEBOOK_APP_ID",     req.client_id.strip())
        set_setting("FACEBOOK_APP_SECRET", req.client_secret.strip())
    else:
        raise HTTPException(400, f"Unknown platform: {req.platform}")
    return {"success": True, "platform": req.platform}

class CompetitorsRequest(BaseModel):
    competitors: str   # newline- or comma-separated names/sites

@app.get("/api/settings/competitors")
async def get_competitors_setting():
    return {"competitors": get_setting("COMPETITORS"), "list": get_competitors()}

@app.post("/api/settings/competitors")
async def save_competitors_setting(req: CompetitorsRequest):
    set_setting("COMPETITORS", req.competitors.strip())
    return {"success": True, "list": get_competitors()}

@app.post("/api/settings/imgbb")
async def save_imgbb_key(request: Request):
    body = await request.json()
    key = body.get("api_key", "").strip()
    if not key:
        raise HTTPException(400, "API key is required")
    set_setting("IMGBB_API_KEY", key)
    return {"success": True}

@app.delete("/api/settings/credentials/{platform}")
async def delete_credentials(platform: str):
    if platform == "linkedin":
        set_setting("LINKEDIN_CLIENT_ID",     "")
        set_setting("LINKEDIN_CLIENT_SECRET", "")
    elif platform in ("facebook", "instagram"):
        set_setting("FACEBOOK_APP_ID",     "")
        set_setting("FACEBOOK_APP_SECRET", "")
    return {"success": True}


class AIPosterRequest(BaseModel):
    description: str
    platform: str = "li"
    post_text: Optional[str] = None
    format: str = "single"   # "single" | "carousel"
    voice: str = "brand"     # debasis | brand | data | inspiring

PLATFORM_DIMS = _POSTER_DIMS  # imported from poster_prompts.py

@app.post("/api/poster/ai")
async def ai_poster(req: AIPosterRequest):
    # Carousel is LinkedIn-only; Instagram always gets a single poster.
    is_carousel = req.format == "carousel" and req.platform == "li"

    if is_carousel:
        prompt = build_carousel_prompt(req)
        max_tokens = 20000
    else:
        W, H, platform_str = PLATFORM_DIMS.get(req.platform, PLATFORM_DIMS["li"])
        prompt = build_single_prompt(req, W, H, platform_str)
        max_tokens = 12000

    try:
        resp = claude.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            temperature=0.85,
            messages=[{"role": "user", "content": prompt}],
        )
        svg_text = extract_svg(resp.content[0].text)
        if not svg_text:
            raise HTTPException(500, f"Claude returned no SVG: {resp.content[0].text[:120]}")

        return {
            "image": svg_to_data_url(svg_text),
            "model": "claude-svg",
            "format": "carousel" if is_carousel else "single",
            "svg": svg_text,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"AI poster generation failed: {e}")


@app.get("/api/status")
async def status():
    with get_db() as conn:
        connections = {r["platform"]: r["username"] for r in
                      conn.execute("SELECT platform, username FROM connections").fetchall()}
    return {
        "claude":          "ready",
        "serper":          "ready" if SERPER_KEY else "not configured",
        "linkedin_oauth":  "configured" if LI_CLIENT_ID else "not configured",
        "facebook_oauth":  "configured" if FB_APP_ID else "not configured",
        "imgbb":           "configured" if IMGBB_API_KEY else "not configured",
        "connections":     connections
    }

# ── Serve the built frontend (production only) ────────────────────────────────────
# In local dev the React app runs on Vite (5173) and `dist/` does not exist, so this
# mount is skipped and nothing about the local workflow changes. In production the
# Docker build produces frontend/dist and FastAPI serves it from the same origin —
# one service, one URL, no CORS or proxy needed.
# NOTE: mounted at "/" LAST so all /api and /uploads routes above take precedence.
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
    print(f"✓ Serving frontend from {FRONTEND_DIST}")
else:
    print("! frontend/dist not found — API-only mode (this is normal for local dev)")
