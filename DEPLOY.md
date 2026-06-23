# Deploying Confiscore Social Poster (free, shareable link)

This deploys the whole app — frontend + API — as **one free Render web service** with a
single URL you share with your team. A team password gates access.

> ⚠️ **Free tier tradeoffs (Route A):** the app sleeps after ~15 min idle (first visitor
> waits ~30s while it wakes), and the database resets on each redeploy/restart — so the
> LinkedIn connection and saved drafts may need to be re-done after an update. To keep data
> permanently, upgrade to Render's Starter plan ($7/mo) and add a persistent disk mounted
> at a path you set as `DATA_DIR`.

---

## 1. Push the code (already done if you committed)

The repo is already on GitHub at `kesh25-col/confiscore-social-poster`.

## 2. Create the Render service

1. Go to **https://render.com** and sign up (free) — use "Sign in with GitHub".
2. Click **New +** → **Blueprint**.
3. Pick the `confiscore-social-poster` repo. Render reads `render.yaml` and proposes the service.
4. Click **Apply**. It will start building from the `Dockerfile` (takes a few minutes the first time).

## 3. Add your secrets (Environment tab)

In the service's **Environment** settings, add these (values only you know):

| Key | Value |
|-----|-------|
| `ANTHROPIC_API_KEY` | your Anthropic key |
| `SERPER_API_KEY` | your Serper key |
| `APP_PASSWORD` | a password you make up — share it with your team |
| `LINKEDIN_CLIENT_ID` | `86e5hcl0uixzir` (from your LinkedIn app) |
| `LINKEDIN_CLIENT_SECRET` | your LinkedIn client secret |

> `BACKEND_URL` / `FRONTEND_URL` are auto-detected from Render's URL — leave them unset.

Click **Save**; Render redeploys automatically.

## 4. Point LinkedIn at the new URL

After the first deploy, Render gives you a URL like
`https://confiscore-social-poster.onrender.com`.

1. Open your LinkedIn app → **Auth** tab → **Authorized redirect URLs**.
2. **Add** (keep the localhost one too):
   ```
   https://confiscore-social-poster.onrender.com/api/auth/linkedin/callback
   ```
   (use YOUR actual Render URL)
3. Save.

## 5. Use it

1. Open the Render URL. You'll see the **login screen** → enter `APP_PASSWORD`.
2. Go to **Settings** → connect LinkedIn (it reuses the credentials above).
3. Share the URL + the password with your team. Done.

---

## Local development is unchanged

None of this affects local dev. With no env vars set, the login gate is off, URLs fall back
to `localhost`, and the data lives in `backend/`. Keep running it the same way:

```
# backend
cd backend && uvicorn main:app --reload
# frontend
cd frontend && npm run dev
```

## Changing the team password later

Edit `APP_PASSWORD` in Render's Environment tab and save. Everyone re-enters the new password.
