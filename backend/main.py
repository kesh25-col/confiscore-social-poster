# ── Confiscore Social Poster — Backend ───────────────────────────────────────
# Stack: FastAPI + Groq + Serper + SQLite + Pillow
# Run: uvicorn main:app --reload
# ─────────────────────────────────────────────────────────────────────────────

import os, json, re, sqlite3, base64, io, secrets, hashlib, time
from datetime import datetime
from typing import Optional
from contextlib import contextmanager
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
import requests as req_lib
import httpx

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
    print("✓ Loaded .env")
    print(">>> KEY:", os.environ.get("GROQ_API_KEY"))
except ImportError:
    print("! python-dotenv not installed")

from guidelines import get_guideline, get_all_guidelines, get_facts
print("✓ Guidelines loaded")

try:
    from poster import generate_poster, TEMPLATE_LIST
    print(f"✓ Poster generator ready — {len(TEMPLATE_LIST)} templates")
except Exception as e:
    print(f"! Poster generator failed: {e}")
    generate_poster = None

from groq import Groq

try:
    from google import genai as google_genai
    GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
    if GEMINI_KEY:
        gemini_client = google_genai.Client(api_key=GEMINI_KEY)
        GEMINI_MODEL  = "gemini-2.5-flash"
        print("✓ Gemini ready")
    else:
        gemini_client = None
        print("! Gemini not configured — add GEMINI_API_KEY to .env")
except ImportError:
    gemini_client = None
    print("! google-genai not installed — run: pip install google-genai")

GROQ_KEY    = os.environ.get("GROQ_API_KEY")
SERPER_KEY  = os.environ.get("SERPER_API_KEY")
LI_CLIENT_ID     = os.environ.get("LINKEDIN_CLIENT_ID", "")
LI_CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET", "")
IG_APP_ID        = os.environ.get("INSTAGRAM_APP_ID", "")
IG_APP_SECRET    = os.environ.get("INSTAGRAM_APP_SECRET", "")

if not GROQ_KEY:
    raise RuntimeError("GROQ_API_KEY missing from .env")

groq = Groq(api_key=GROQ_KEY)
print("✓ Groq ready")
print(f"{'✓' if SERPER_KEY else '!'} Serper {'ready' if SERPER_KEY else 'missing — web search disabled'}")
print(f"{'✓' if LI_CLIENT_ID else '!'} LinkedIn {'configured' if LI_CLIENT_ID else 'not configured'}")
print(f"{'✓' if IG_APP_ID else '!'} Instagram {'configured' if IG_APP_ID else 'not configured'}")

# ── SQLite ─────────────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent / "confiscore.db"

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
            posted_at     TEXT
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

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

class UpdateDraftRequest(BaseModel):
    selected_version: Optional[str] = None
    image_path: Optional[str] = None
    status: Optional[str] = None

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

# ── Groq helper ────────────────────────────────────────────────────────────────
def groq_complete(prompt: str, json_mode: bool = False) -> str:
    kwargs = dict(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.7,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = groq.chat.completions.create(**kwargs)
    return resp.choices[0].message.content

def parse_json_safe(raw: str) -> dict:
    clean = re.sub(r"```json|```", "", raw).strip()
    match = re.search(r'\{.*\}', clean, re.DOTALL)
    if match:
        clean = match.group(0)
    return json.loads(clean)

# ── Stage 1: Engineer prompt ───────────────────────────────────────────────────
def engineer_prompt(description: str, platforms: list[str], search_results: str) -> str:
    facts = get_facts()
    platform_specs = []
    if "li" in platforms:
        platform_specs.append("LinkedIn: professional, 2-4 short paragraphs, no hashtag spam")
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

    return groq_complete(prompt)

# ── Stage 2: Write 4 versions ──────────────────────────────────────────────────
def write_version(brief: str, platforms: list[str], voice_key: str) -> dict:
    guideline = get_guideline(voice_key)
    facts = get_facts()
    platform_keys = [p for p in ["li", "ig"] if p in platforms]

    # Build platform-specific rules
    platform_rules = []
    if "li" in platforms:
        platform_rules.append(f"LINKEDIN RULES:\n{guideline['linkedin_rules']}")
    if "ig" in platforms:
        platform_rules.append(f"INSTAGRAM RULES:\n{guideline['instagram_rules']}")

    keys_str = ", ".join(f'"{p}": "post text here"' for p in platform_keys)

    prompt = f"""{guideline['system_prompt']}

{facts}

═══════════════════════════════════════════════════════════════
CONTENT BRIEF FROM PROMPT ENGINEER
═══════════════════════════════════════════════════════════════
{brief}

═══════════════════════════════════════════════════════════════
PLATFORM-SPECIFIC RULES FOR THIS POST
═══════════════════════════════════════════════════════════════
{chr(10).join(platform_rules)}

═══════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════
Respond ONLY with a valid JSON object. No markdown. No preamble. Nothing else.
{{ {keys_str} }}"""

    raw = groq_complete(prompt, json_mode=True)
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
            result = write_version(brief, req.platforms, voice_key)
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
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO posts
               (description, platforms, versions, selected_version, image_path, status, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (req.description, json.dumps(req.platforms), json.dumps(req.versions),
             req.selected_version, req.image_path, "draft", now)
        )
        conn.commit()
        return {"id": cur.lastrowid, "status": "draft", "created_at": now}

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
        "redirect_uri": "http://localhost:8000/api/auth/linkedin/callback",
        "state": state,
        "scope": "w_member_social r_liteprofile r_emailaddress"
    }
    url = "https://www.linkedin.com/oauth/v2/authorization?" + "&".join(f"{k}={v}" for k, v in params.items())
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
                "redirect_uri": "http://localhost:8000/api/auth/linkedin/callback",
                "client_id": client_id,
                "client_secret": client_secret,
            }
        )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(400, f"LinkedIn token exchange failed: {token_data}")

        profile_resp = await client.get(
            "https://api.linkedin.com/v2/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        profile = profile_resp.json()
        user_id = profile.get("id", "")
        username = f"{profile.get('localizedFirstName','')} {profile.get('localizedLastName','')}".strip()

    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO connections
               (platform, access_token, user_id, username, connected_at)
               VALUES (?,?,?,?,?)""",
            ("linkedin", access_token, user_id, username, datetime.utcnow().isoformat())
        )
        conn.commit()

    return RedirectResponse("http://localhost:5173?connected=linkedin")

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
        "redirect_uri": "http://localhost:8000/api/auth/instagram/callback",
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
                "redirect_uri": "http://localhost:8000/api/auth/instagram/callback",
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

    return RedirectResponse("http://localhost:5173?connected=instagram")

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

    for platform in req.platforms:
        conn_data = connections.get(platform)
        if not conn_data:
            results[platform] = {"success": False, "error": f"{platform} not connected"}
            continue
        try:
            text = selected["content"].get(platform, "")
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

# ── Status ─────────────────────────────────────────────────────────────────────

# ── Poster generation ──────────────────────────────────────────────────────────
class PosterRequest(BaseModel):
    template: str       # stat | series | comparison
    platform: str       # ig | li
    data: dict

@app.post("/api/poster")
async def create_poster(req: PosterRequest):
    if not generate_poster:
        raise HTTPException(500, "Poster generator not available — check Pillow installation")
    result = generate_poster(req.template, req.platform, req.data)
    if not result:
        raise HTTPException(500, "Poster generation failed")
    return {"image": result}

@app.post("/api/poster/auto")
async def auto_poster(req: GenerateRequest):
    """Auto-generate poster data from description using Groq, then render poster."""
    if not generate_poster:
        raise HTTPException(500, "Poster generator not available")

    facts = get_facts()
    platform = req.platforms[0] if req.platforms else 'li'

    prompt = f"""You are creating data for a Confiscore social media poster.

{facts}

Description: "{req.description}"
Platform: {platform} (li=LinkedIn landscape, ig=Instagram square)

Choose the BEST template from these 15 options:

1. stat — big number/cost/percentage as the hero. Data: headline, stat, stat_label, body, tag
2. series — numbered educational list (like Dr. Debasis's Series posts). Data: number, title, points(5 items), footnote
3. comparison — two columns left vs right. Data: title, left_label, left_pts(4), right_label, right_pts(4)
4. quote — bold founder quote on dark bg. Data: quote, author, role
5. score — shows the 0-1000 gauge. Data: score(int), band(critical/at-risk/stable/strong/champion), headline, description, use_case
6. industry — targets a specific industry. Data: industry, headline, use_cases(4 items), stat, stat_label
7. bias — cognitive bias educational post. Data: bias_name, definition, business_impact, how_confiscore_fixes, series_num
8. reasons — "5 reasons" list format. Data: title, reasons(5 items), cta
9. before_after — transformation story. Data: context, before_pts(4), after_pts(4), result
10. timeline — journey/milestones. Data: title, milestones(list of [period, event] pairs, 4-5 items)
11. did_you_know — surprising fact hook. Data: fact, explanation, source, cta
12. feature — single product feature deep dive. Data: feature_name, what_it_does, how_it_works_pts(3), benefit
13. case_study — customer success story. Data: industry, challenge, solution, result, metric
14. myth_fact — debunking misconceptions. Data: topic, myths(4), facts(4)
15. weekly_insight — regular insight series. Data: week_number, insight_title, key_thought, data_point, data_label, takeaway

Pick the template that best matches the description. Generate realistic, specific Confiscore-branded content.
All text should be DESCRIPTIVE but concise — 8-15 words per point, 10-15 words per headline.
For case_study: challenge should be a full problem statement, solution should explain what Confiscore does, result should include a specific metric like "40% reduction in bad hires" or "3x faster screening".
For stat: stat should be a bold number like "73%", stat_label should be descriptive like "of recruiters cite overconfidence as top hiring failure", body should be 2-3 sentences of context.
For series: each point should be a complete insight, not just 1-2 words.
Never use placeholder words like "Hiring" or "Confiscore" alone — always add context.
Use real numbers from the facts above where possible.

Respond ONLY with valid JSON, no markdown:
{{
  "template": "template_name_here",
  "data": {{ ... all required fields for that template ... }}
}}"""

    try:
        raw = groq_complete(prompt, json_mode=True)
        parsed = parse_json_safe(raw)
        template = parsed.get('template', 'stat')
        data = parsed.get('data', {})
        image = generate_poster(template, platform, data)
        return {"image": image, "template": template, "data": data}
    except Exception as e:
        raise HTTPException(500, f"Auto poster failed: {{e}}")


# ── Diagram generation (Gemini → SVG → PNG) ───────────────────────────────────
class DiagramRequest(BaseModel):
    description: str
    post_text: str
    platform: str = "li"

@app.post("/api/poster/diagram")
async def generate_diagram(req: DiagramRequest):
    if not gemini_client:
        raise HTTPException(500, "Gemini not configured — add GEMINI_API_KEY to .env")

    W, H = (1200, 627) if req.platform == "li" else (1080, 1080)

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
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        svg_text = response.text.strip()

        # Strip markdown if present
        if "```svg" in svg_text:
            svg_text = svg_text.split("```svg")[1].split("```")[0].strip()
        elif "```" in svg_text:
            svg_text = svg_text.split("```")[1].split("```")[0].strip()

        if not svg_text.startswith("<svg"):
            raise HTTPException(500, f"Gemini returned invalid SVG: {svg_text[:100]}")

        try:
            import cairosvg
            png_bytes = cairosvg.svg2png(
                bytestring=svg_text.encode(),
                output_width=W,
                output_height=H
            )
            b64 = base64.b64encode(png_bytes).decode()
            return {"image": f"data:image/png;base64,{b64}", "type": "diagram", "svg": svg_text}
        except ImportError:
            svg_b64 = base64.b64encode(svg_text.encode()).decode()
            return {"image": f"data:image/svg+xml;base64,{svg_b64}", "type": "diagram_svg", "svg": svg_text}

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

@app.post("/api/poster/ai")
async def ai_poster(req: AIPosterRequest):
    if not gemini_client:
        raise HTTPException(500, "Gemini not configured — add GEMINI_API_KEY to .env")

    aspect       = "16:9" if req.platform == "li" else "1:1"
    platform_str = "LinkedIn landscape (1200×627px)" if req.platform == "li" else "Instagram square (1080×1080px)"

    prompt = f"""Design a premium professional social media infographic poster for Confiscore.

COMPANY: Confiscore — B2B SaaS that measures human confidence on a 0–1000 scale using patented Valence-Arousal psycho-technology. Used by HR teams, recruiters, and business leaders.

CONTENT TO VISUALIZE:
{req.description}

{f"POST CONTEXT:{chr(10)}{req.post_text[:400]}" if req.post_text else ""}

DESIGN REQUIREMENTS:
- Background: very deep navy blue gradient (#070B1B → #0D1433)
- Primary accent: electric green (#38EF7D) — use boldly for the hero number or headline
- Secondary: electric blue (#3B5BDB), bright blue-white (#99ABFF)
- Typography: large bold modern sans-serif headlines, clean body text — strong hierarchy
- One dominant focal element (large stat, bold number, or powerful headline)
- Subtle glowing halo behind the hero element
- Abstract geometric accents (circles, lines, gradients — no people, no photos)
- Include these brand elements somewhere: "Confiscore", "confiscore.com", "Confidence Is the New KPI"
- Format: {platform_str}

STYLE REFERENCE: Think Bloomberg data graphic meets premium SaaS marketing — analytical, trustworthy, visually striking. Dark background, glowing accents, clean typography. High contrast. Minimal clutter."""

    try:
        from google.genai import types as gt

        # Primary: Imagen 3 — highest quality
        try:
            resp = gemini_client.models.generate_images(
                model="imagen-3.0-generate-001",
                prompt=prompt,
                config=gt.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio=aspect,
                    safety_filter_level="block_some",
                    person_generation="dont_allow",
                )
            )
            b64 = base64.b64encode(resp.generated_images[0].image.image_bytes).decode()
            return {"image": f"data:image/png;base64,{b64}", "model": "imagen-3"}
        except Exception as e1:
            print(f"Imagen 3 failed ({e1}), falling back to Gemini flash image gen...")

        # Fallback: Gemini 2.0 Flash image generation
        resp = gemini_client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=prompt,
            config=gt.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"])
        )
        for part in resp.candidates[0].content.parts:
            if part.inline_data is not None:
                return {
                    "image": f"data:{part.inline_data.mime_type};base64,{part.inline_data.data}",
                    "model": "gemini-flash"
                }
        raise Exception("No image returned by Gemini")

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
        "groq": "ready",
        "serper": "ready" if SERPER_KEY else "not configured",
        "linkedin_oauth": "configured" if LI_CLIENT_ID else "not configured",
        "instagram_oauth": "configured" if IG_APP_ID else "not configured",
        "connections": connections
    }
