# ── Stage 1: Build React frontend ────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
# Point API calls to the same origin (HF Space serves both on :8000)
ENV VITE_API_URL=/api
RUN npm run build

# ── Stage 2: Python backend + serve built frontend as static files ─────────────
FROM python:3.11-slim

WORKDIR /app

# System deps: Boost + SWIG for vina compilation, Open Babel for PDBQT conversion
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxrender1 \
    libxext6 \
    openbabel \
    autodock-vina \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Static file serving
RUN pip install --no-cache-dir aiofiles

COPY backend/ .
COPY --from=frontend-builder /frontend/dist ./static

# Serve static frontend from FastAPI at root /
# (add StaticFiles mount — handled via HF_STATIC env var in main.py)
ENV HF_STATIC=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
