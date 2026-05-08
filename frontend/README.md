# VirtualScreener — Frontend

React + TypeScript + Vite frontend for the VirtualScreener AI drug discovery platform.

## Stack

- **React 18** + **TypeScript**
- **Vite** (dev server + build)
- **Tailwind CSS** (styling)
- **React Router** (client-side routing)
- **Recharts** (radar chart for drug-likeness)
- **NGL Viewer** (3D docking pose visualization)

## Development

```bash
npm install
npm run dev
# → http://localhost:5173
```

API calls to `/api/*` are proxied to the FastAPI backend at `http://localhost:8000` via `vite.config.ts`.

## Build

```bash
npm run build
# Output: dist/
```

In production (Hugging Face Spaces), the built `dist/` is served directly by FastAPI — no separate web server needed.

## Pages

- **`/`** — Upload form: drag-drop protein PDB + compound library, submit screening job
- **`/results/:jobId`** — Live job progress + paginated ranked results table with 2D structures and docking scores
