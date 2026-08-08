# Confiscore Social Poster

An AI-assisted social-media posting tool for **Confiscore** — a B2B SaaS that measures
candidate/team confidence on a 0–1000 scale. Describe a post idea, and the app researches
context, drafts multiple on-brand voices with Claude, generates a poster image, and
publishes (or schedules) to LinkedIn — including native multi-slide **carousels**.

## Stack

- **Backend:** FastAPI (Python), SQLite, Anthropic Claude API, Serper (web research)
- **Frontend:** React + Vite
- **Publishing:** LinkedIn (posts, image posts, and PDF-document carousels)

## Features

- Generate multiple voice variants of a post from a short description
- Auto-research the topic for supporting context (Serper)
- AI-generated poster images (SVG → PNG) and native LinkedIn carousels
- Draft, schedule, and auto-publish (in-process scheduler, checks every 60s)
- Optional team password gate for shared/hosted deployments
- Token-usage tracking per post

## Running locally

You need **Python 3.10+** and **Node 18+**.

### 1. Backend (port 8000)

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # then fill in your keys (at minimum ANTHROPIC_API_KEY)
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

> **Windows note:** the startup logs use Unicode (`✓`) characters. On the default
> Windows console (cp1252) this can throw `UnicodeEncodeError` at launch. Start the
> server with UTF-8 output to avoid it:
>
> ```bash
> PYTHONIOENCODING=utf-8 python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
> ```

### 2. Frontend (port 5173)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The Vite dev server proxies `/api/*` to the backend,
so start the backend first (a few `ECONNREFUSED` proxy errors during the ~1s startup
window are harmless).

## Environment variables

See [`backend/.env.example`](backend/.env.example) for the full list. Summary:

| Variable | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | **Yes** | Claude — content and poster generation |
| `SERPER_API_KEY` | Optional | Web research for post context |
| `LINKEDIN_CLIENT_ID` / `LINKEDIN_CLIENT_SECRET` | For LinkedIn OAuth connect | Connecting a LinkedIn account |
| `LINKEDIN_API_VERSION` | Optional | LinkedIn versioned API (default `202606`) |
| `FACEBOOK_APP_ID` / `FACEBOOK_APP_SECRET` | For Facebook | Facebook connect/publish |
| `INSTAGRAM_APP_ID` / `INSTAGRAM_APP_SECRET` | For Instagram | Instagram connect/publish |
| `IMGBB_API_KEY` | For Instagram | Public image hosting Instagram requires |
| `APP_PASSWORD` | Optional | Team password gate (leave empty = open locally) |
| `BACKEND_URL` / `FRONTEND_URL` / `DATA_DIR` | Optional | Deployment overrides |

Secrets live only in `backend/.env`, which is git-ignored and has never been committed.

## Deployment

See [`DEPLOY.md`](DEPLOY.md) for hosting the whole app (frontend + API) as a single
service. `render.yaml`, `Dockerfile`, and `Dockerfile.prebuilt` are provided.

## Known limitations

- **LinkedIn is the only fully working platform.** Single posts, image posts, and
  carousels publish and auto-schedule reliably.
- **Instagram posting is not working** and **Facebook has an app-key mismatch** — both
  need further work before they can be relied on.
- **No automated tests yet.**
