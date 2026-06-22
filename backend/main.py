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
    print("✓ Loaded .env")
except ImportError:
    print("! python-dotenv not installed")

from guidelines import get_guideline, get_all_guidelines, get_facts
print("✓ Guidelines loaded")

import anthropic

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
SERPER_KEY    = os.environ.get("SERPER_API_KEY")
LI_CLIENT_ID     = os.environ.get("LINKEDIN_CLIENT_ID", "")
LI_CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET", "")
IG_APP_ID        = os.environ.get("INSTAGRAM_APP_ID", "")
IG_APP_SECRET    = os.environ.get("INSTAGRAM_APP_SECRET", "")

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
print("✓ Claude ready (text + SVG posters)")
print(f"{'✓' if SERPER_KEY else '!'} Serper {'ready' if SERPER_KEY else 'missing — web search disabled'}")
print(f"{'✓' if LI_CLIENT_ID else '!'} LinkedIn {'configured' if LI_CLIENT_ID else 'not configured'}")
print(f"{'✓' if IG_APP_ID else '!'} Instagram {'configured' if IG_APP_ID else 'not configured'}")

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

# ── Instagram OAuth ────────────────────────────────────────────────────────────
@app.get("/api/auth/instagram")
async def instagram_auth():
    app_id = get_setting("INSTAGRAM_APP_ID") or IG_APP_ID
    if not app_id:
        raise HTTPException(400, "Instagram not configured — add credentials via the app settings")
    state = secrets.token_urlsafe(32)
    with get_db() as conn:
        conn.execute("INSERT INTO oauth_state VALUES (?,?,?)", (state, "instagram", time.time()))
        conn.commit()
    params = {
        "client_id": app_id,
        "redirect_uri": f"{BACKEND_URL}/api/auth/instagram/callback",
        "scope": "instagram_basic,instagram_content_publish",
        "response_type": "code",
        "state": state
    }
    url = "https://api.instagram.com/oauth/authorize?" + "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url)

@app.get("/api/auth/instagram/callback")
async def instagram_callback(code: str, state: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM oauth_state WHERE state=? AND platform=?",
                          (state, "instagram")).fetchone()
        if not row or time.time() - row["created_at"] > 600:
            raise HTTPException(400, "Invalid or expired OAuth state")
        conn.execute("DELETE FROM oauth_state WHERE state=?", (state,))
        conn.commit()

    app_id     = get_setting("INSTAGRAM_APP_ID")     or IG_APP_ID
    app_secret = get_setting("INSTAGRAM_APP_SECRET") or IG_APP_SECRET

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://api.instagram.com/oauth/access_token",
            data={
                "client_id": app_id,
                "client_secret": app_secret,
                "grant_type": "authorization_code",
                "redirect_uri": f"{BACKEND_URL}/api/auth/instagram/callback",
                "code": code,
            }
        )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        user_id = str(token_data.get("user_id", ""))
        if not access_token:
            raise HTTPException(400, f"Instagram token exchange failed: {token_data}")

    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO connections
               (platform, access_token, user_id, username, connected_at)
               VALUES (?,?,?,?,?)""",
            ("instagram", access_token, user_id, "Instagram Account", datetime.utcnow().isoformat())
        )
        conn.commit()

    return RedirectResponse(f"{FRONTEND_URL}/?connected=instagram")

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

# ── Post to Instagram ──────────────────────────────────────────────────────────
async def post_to_instagram(caption: str, image_path: Optional[str], access_token: str, user_id: str):
    if not image_path:
        raise Exception("Instagram requires an image")

    image_file = UPLOAD_DIR / image_path
    if not image_file.exists():
        raise Exception("Image file not found")

    raise Exception("Instagram posting requires a public image URL. Host your image publicly first.")

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
            content_key = PLATFORM_KEY_MAP.get(platform, platform)
            text = selected["content"].get(content_key, "")
            if platform == "linkedin":
                await post_to_linkedin(text, post.get("image_path"),
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
    ig_id = get_setting("INSTAGRAM_APP_ID")   or IG_APP_ID
    return {
        "linkedin":  bool(li_id),
        "instagram": bool(ig_id),
    }

@app.post("/api/settings/credentials")
async def save_credentials(req: CredentialsRequest):
    if not req.client_id.strip() or not req.client_secret.strip():
        raise HTTPException(400, "Both Client ID and Client Secret are required")
    if req.platform == "linkedin":
        set_setting("LINKEDIN_CLIENT_ID",     req.client_id.strip())
        set_setting("LINKEDIN_CLIENT_SECRET", req.client_secret.strip())
    elif req.platform == "instagram":
        set_setting("INSTAGRAM_APP_ID",     req.client_id.strip())
        set_setting("INSTAGRAM_APP_SECRET", req.client_secret.strip())
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

@app.delete("/api/settings/credentials/{platform}")
async def delete_credentials(platform: str):
    if platform == "linkedin":
        set_setting("LINKEDIN_CLIENT_ID",     "")
        set_setting("LINKEDIN_CLIENT_SECRET", "")
    elif platform == "instagram":
        set_setting("INSTAGRAM_APP_ID",     "")
        set_setting("INSTAGRAM_APP_SECRET", "")
    return {"success": True}


class AIPosterRequest(BaseModel):
    description: str
    platform: str = "li"
    post_text: Optional[str] = None
    format: str = "single"   # "single" | "carousel"

# Per-platform poster dimensions (W, H, label) — each platform's recommended feed image size.
PLATFORM_DIMS = {
    "li": (1200, 627, "LinkedIn landscape"),
    "fb": (1200, 630, "Facebook landscape"),
    "ig": (1080, 1080, "Instagram square"),
}

SVG_BRAND_BLOCK = """COMPANY: Confiscore — B2B SaaS that measures human confidence on a 0–1000 scale using
patented Valence-Arousal psycho-technology. Used by HR teams, recruiters, and business leaders.

BRAND DESIGN SYSTEM (fixed Confiscore palette — always use exactly these colours):
- Background: deep navy gradient <linearGradient> from #070B1B to #0D1433, filling the whole canvas.
- Primary accent: electric green #38EF7D — use boldly on hero numbers/headlines and the left accent bar.
- Secondary accents: electric blue #3B5BDB and blue-white #99ABFF for body/labels.
- Muted "before" values: grey #5A6B82. Footer/secondary text: #8FA8C0.
- A thin 8px green accent bar down the left edge of the canvas.
- Typography: font-family="system-ui, -apple-system, Segoe UI, sans-serif" ONLY (no external fonts).
- Subtle geometric accents only: thin lines, concentric circles, faint dot grid — never photos or people.
- Use the EXACT numbers from the content. Never invent data.

CHARTS — when the data suits it, draw a simple clean chart instead of plain text (always brand colours):
- A before→after stat → a thin horizontal progress bar (grey track, green fill to the % value).
- A 0–1000 score → a horizontal gauge bar with a marker at the score, or a donut arc.
- A set of comparable values → short horizontal bars of proportional length with the number at the end.
- Keep charts minimal and precise — align to a grid, label clearly, no clutter.
- CHART LABELS MUST NOT OVERLAP THE BAR. A bar's track ends at a fixed x; any end-label (e.g. "Predictive",
  "Reactive") goes to the RIGHT of where the bar track ENDS, with ≥ 12px gap — never on top of the fill.
  If space is tight, place the label ABOVE or BELOW the bar instead. Reserve label width before sizing the bar.
- A value label at the end of a bar must sit just past the fill's end, not over coloured fill.

CRITICAL — PRECISION (the previous version had misaligned arrows and uneven boxes; fix this):
- BEFORE → AFTER pairs: put "before", the arrow, and "after" on ONE shared baseline (identical y).
  Draw the arrow as a real shape (a <line> + small <polygon> head) OR a "→" glyph vertically centred to the
  number's optical middle — never floating above or below. Use consistent horizontal gaps around it.
- CARD GRID: every card identical width AND height, snapped to a strict grid with EQUAL gutters.
  Compute: card_w = (zone_width - gutter) / cols; card_h = (zone_height - gutter) / rows. Reuse these exact
  values for every card. Align all card x/y to the grid — no card offset by a few px.
- Center the content inside each card (use text-anchor="middle" on a shared center x).

CRITICAL — SVG TEXT DOES NOT WRAP. You MUST prevent text overflow:
- SVG <text> never auto-wraps. A long string WILL run off its area and overlap other elements.
- Break every long line into multiple <text> elements stacked vertically (increment y by ~1.15x font-size).
- Budget characters per line by font size. At the given width, a line must satisfy roughly:
  max_chars ≈ (available_width_px) / (font_size_px * 0.6). Stay UNDER that. When unsure, use fewer.
- Headlines: keep each line SHORT (≤ 18 characters for 60-90px text). Prefer 2-3 short lines over 1 long line.
- A text element placed inside a card or column MUST fit within that box's width — measure before placing.
- Estimate text width as chars * font_size * 0.6 and confirm it fits the element's width before committing.
- Never let any text cross into a neighbouring card, column, or the canvas edge. Leave ≥ 40px margins."""


def _build_single_prompt(req: AIPosterRequest, W: int, H: int, platform_str: str) -> str:
    primary = (req.post_text or req.description or "").strip()
    context = req.description.strip() if (req.post_text and req.description) else ""
    return f"""You are a world-class graphic designer who builds polished marketing posters in raw SVG.
Design a premium social media poster for Confiscore as a complete, self-contained SVG.

{SVG_BRAND_BLOCK}

THE POST THIS POSTER ACCOMPANIES (design the visual to match ITS message, tone, and key numbers):
{primary[:600]}

{f"BACKGROUND TOPIC (context only):{chr(10)}{context[:200]}" if context else ""}

CANVAS: {W}x{H}px ({platform_str}). Set the root <svg> width="{W}" height="{H}" viewBox="0 0 {W} {H}".

PICK A LAYOUT that best fits the post (vary it — do not always use the same one):
  A) HERO STAT — one dominant number (110-160px) centered/left, 2-3 small supporting cards
  B) SPLIT GRID — headline on the left half, a 2x2 stat-card grid on the right half
  C) STACKED BANDS — 3-4 horizontal bands, each a stat with a label, accent rule between them
  D) BIG STATEMENT — a bold 3-4 line headline as the focus, one stat strip along the bottom
Choose the layout from the post's content: many numbers → B or C; one key number → A; a strong line → D.

LAYOUT SAFETY (must hold for whichever layout you pick):
- Define clear zones/cards with explicit x,y,width,height. NO element may cross into another zone or card.
- Keep ≥ 40px outer margins and ≥ 30px gutters between cards.
- Cards: rounded rect (rx=16), rgba fill, thin glowing accent border; big number in accent, SHORT label under it.
- A soft radial glow blob (~18% opacity) behind the focal element, contained within its zone.
- Brand footer: "Confiscore" bottom-left in white bold 24px; "confiscore.com" bottom-right in accent color.

Before finishing, re-check every <text>: does it fit its zone/card width given chars * fontsize * 0.6? If not, shorten it or add a line break.

OUTPUT: Raw SVG only. Start with <svg and end with </svg>. No markdown, no explanation."""


def _build_carousel_prompt(req: AIPosterRequest) -> str:
    primary = (req.post_text or req.description or "").strip()
    context = req.description.strip() if (req.post_text and req.description) else ""
    return f"""You are a world-class graphic designer who builds LinkedIn carousels in raw SVG.
Design a premium multi-slide carousel for Confiscore as ONE complete, self-contained SVG with
all slides stacked vertically.

{SVG_BRAND_BLOCK}

THE POST THIS CAROUSEL IS BASED ON (turn ITS message and numbers into slides):
{primary[:700]}

{f"BACKGROUND TOPIC (context only):{chr(10)}{context[:200]}" if context else ""}

CAROUSEL STRUCTURE:
- Each slide is exactly 1080x1080px (Instagram/LinkedIn square)
- Decide the slide count from the content: 1 cover slide + one slide per key stat/point + 1 CTA slide
  (typically 4-6 slides total)
- Stack them vertically using <g transform="translate(0, N*1080)"> for slide index N
- Root <svg>: width="1080" height="{{TOTAL}}" viewBox="0 0 1080 {{TOTAL}}" where TOTAL = slideCount * 1080

SLIDE DESIGN:
- COVER slide: brand eyebrow label, a bold 2-line headline (90-116px), a one-line subtext,
  a short "Swipe to see the numbers →" hint, decorative concentric circles
- STAT slides: an eyebrow like "01 / TEAM CONFIDENCE", a giant number (260-280px) in accent green,
  a bold white stat label, one line of grey context, a small "confiscore.com" badge
- For a before→after stat, show both numbers with an arrow (e.g. 550 → 700+), the lower one muted
- CTA slide (last): the closing stat or message + a filled accent button "Try Confiscore today →"
- Every slide: navy background, the 8px left accent bar, consistent 72px left margin

Replace {{TOTAL}} with the real computed pixel height. Use the EXACT numbers from the content.

OUTPUT: Raw SVG only. Start with <svg and end with </svg>. No markdown, no explanation."""


@app.post("/api/poster/ai")
async def ai_poster(req: AIPosterRequest):
    # Carousel is LinkedIn-only; Instagram always gets a single poster.
    is_carousel = req.format == "carousel" and req.platform == "li"

    if is_carousel:
        prompt = _build_carousel_prompt(req)
        max_tokens = 16000
    else:
        W, H, platform_str = PLATFORM_DIMS.get(req.platform, PLATFORM_DIMS["li"])
        prompt = _build_single_prompt(req, W, H, platform_str)
        max_tokens = 8000

    try:
        resp = claude.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            temperature=0.8,
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
        "claude": "ready",
        "serper": "ready" if SERPER_KEY else "not configured",
        "linkedin_oauth": "configured" if LI_CLIENT_ID else "not configured",
        "instagram_oauth": "configured" if IG_APP_ID else "not configured",
        "connections": connections
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
