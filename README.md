---
title: VirtualScreener
emoji: 🧬
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 8000
pinned: false
---

# VirtualScreener — AI Drug Discovery Platform

AI-powered virtual screening: upload a protein PDB + compound library → ranked binding affinity predictions via a 3-tier ML + physics pipeline.

---

## Pipeline

| Tier  | Tool                                   | Task                                                |
| ----- | -------------------------------------- | --------------------------------------------------- |
| **1** | RDKit                                  | Lipinski Ro5 + PAINS filter, 2D SVG rendering       |
| **2** | Chemprop D-MPNN + DeepChem AttentiveFP | ML binding affinity (pIC50), MC-Dropout uncertainty |
| **3** | AutoDock Vina                          | Physics-based docking, 3D pose generation           |

---

## Quick Start (Docker)

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs

---

## Local Development

### Backend

```bash
cd backend

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the API server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## Input Formats

| File             | Format                   | Notes                                      |
| ---------------- | ------------------------ | ------------------------------------------ |
| Protein          | `.pdb`                   | Standard PDB format from RCSB or AlphaFold |
| Compound library | `.smi` / `.txt` / `.csv` | One SMILES per line: `SMILES name`         |
| Compound library | `.sdf`                   | Standard SDF with molecule names           |

### Example SMILES file (`library.smi`)

```
CC(=O)Oc1ccccc1C(=O)O Aspirin
CC12CCC3C(C1CCC2O)CCC4=CC(=O)CCC34C Testosterone
CN1C=NC2=C1C(=O)N(C(=O)N2C)C Caffeine
```

---

## API Endpoints

| Method | Endpoint                                | Description                                                     |
| ------ | --------------------------------------- | --------------------------------------------------------------- |
| `POST` | `/api/screen`                           | Submit job (multipart: `protein_file`, `library_file`, `top_k`) |
| `GET`  | `/api/jobs/{job_id}`                    | Poll status & progress                                          |
| `GET`  | `/api/molecules/{job_id}`               | Paginated results                                               |
| `GET`  | `/api/molecules/{job_id}/{mol_id}/pose` | Docking pose PDB                                                |
| `GET`  | `/api/molecules/{job_id}/export/csv`    | Download CSV                                                    |

---

## ML Models

### Chemprop D-MPNN

- Place a pre-trained checkpoint at `backend/models/chemprop_bindingdb.pt`
- If absent, the app runs in **demo mode** with a fingerprint-similarity heuristic
- Train your own: `chemprop train --data_path your_data.csv --smiles_column smiles --target_columns pic50`

### DeepChem AttentiveFP

- Checkpoint auto-saved to `backend/models/attentivefp/`
- Falls back to heuristic if no checkpoint found

### AutoDock Vina

- Installed as a system binary via `apt install autodock-vina` (no source compilation)
- Requires `obabel` (Open Babel) for PDBQT conversion
- Falls back to a physics-inspired heuristic score if binary is unavailable

---

## Project Structure

```
virtualscreener/
├── backend/
│   ├── app/
│   │   ├── main.py               FastAPI entry point
│   │   ├── core/
│   │   │   ├── config.py         Settings (Pydantic)
│   │   │   └── job_store.py      In-memory async job store
│   │   ├── routers/
│   │   │   ├── screening.py      POST /api/screen
│   │   │   ├── jobs.py           GET /api/jobs/{id}
│   │   │   └── molecules.py      GET /api/molecules/{id}
│   │   ├── services/
│   │   │   ├── pipeline.py       3-tier orchestrator
│   │   │   ├── molecular_proc.py RDKit processing (Tier 1)
│   │   │   ├── protein_proc.py   BioPython PDB parser
│   │   │   ├── ml_scoring.py     Chemprop + DeepChem ensemble (Tier 2)
│   │   │   └── docking.py        AutoDock Vina (Tier 3)
│   │   └── schemas/models.py     Pydantic schemas
│   ├── models/                   ML checkpoints
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/client.ts         Typed API client
│       ├── components/
│       │   ├── UploadZone.tsx    Drag-drop file upload
│       │   ├── ProgressTracker.tsx Live pipeline progress
│       │   ├── ResultsTable.tsx  Sortable results table
│       │   ├── MolCard.tsx       Molecule detail card
│       │   ├── MolViewer.tsx     NGL 3D docking pose viewer
│       │   └── DruglikenessRadar.tsx Recharts radar chart
│       └── pages/
│           ├── Home.tsx          Upload form
│           └── Results.tsx       Job status + results
└── docker-compose.yml
```
