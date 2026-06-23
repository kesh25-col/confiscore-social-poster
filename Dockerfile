# ── Stage 1: build the React frontend ────────────────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python backend that also serves the built frontend ───────────────────
FROM python:3.11-slim
WORKDIR /app

# Install backend deps
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy the compiled frontend from stage 1 (FastAPI serves this at "/")
COPY --from=frontend /app/frontend/dist ./frontend/dist

WORKDIR /app/backend

# Render provides $PORT; default to 8000 for local docker runs.
ENV PORT=8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
