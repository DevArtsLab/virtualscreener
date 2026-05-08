const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

export interface LipinskiResult {
  mw: number;
  logp: number;
  hbd: number;
  hba: number;
  tpsa: number;
  rotatable_bonds: number;
  passes_ro5: boolean;
  passes_pains: boolean;
}

export interface MoleculeResult {
  mol_id: string;
  name: string;
  smiles: string;
  rank: number;
  predicted_pic50: number | null;
  pic50_uncertainty: number | null;
  deepchem_score: number | null;
  ensemble_score: number | null;
  docking_score: number | null;
  has_pose: boolean;
  lipinski: LipinskiResult | null;
  svg_2d: string | null;
  filtered_out: boolean;
  filter_reason: string | null;
}

export type JobStatus =
  | "queued"
  | "tier1"
  | "tier2"
  | "tier3"
  | "done"
  | "error";

export interface JobResponse {
  job_id: string;
  status: JobStatus;
  progress: number;
  current_stage: string;
  molecules_total: number;
  molecules_processed: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ScreeningResults {
  job_id: string;
  total_molecules: number;
  passed_tier1: number;
  passed_tier2: number;
  docked_molecules: number;
  results: MoleculeResult[];
  page: number;
  page_size: number;
  total_pages: number;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  async submitScreening(
    proteinFile: File,
    libraryFile: File,
    topK: number
  ): Promise<JobResponse> {
    const form = new FormData();
    form.append("protein_file", proteinFile);
    form.append("library_file", libraryFile);
    form.append("top_k", String(topK));
    const res = await fetch(`${BASE}/screen`, { method: "POST", body: form });
    return handleResponse<JobResponse>(res);
  },

  async getJobStatus(jobId: string): Promise<JobResponse> {
    const res = await fetch(`${BASE}/jobs/${jobId}`);
    return handleResponse<JobResponse>(res);
  },

  async getResults(
    jobId: string,
    page = 1,
    pageSize = 50,
    onlyPassed = true,
    sortBy = "rank",
    sortAsc = true
  ): Promise<ScreeningResults> {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
      only_passed: String(onlyPassed),
      sort_by: sortBy,
      sort_asc: String(sortAsc),
    });
    const res = await fetch(`${BASE}/molecules/${jobId}?${params}`);
    return handleResponse<ScreeningResults>(res);
  },

  async getPose(jobId: string, molId: string): Promise<string> {
    const res = await fetch(`${BASE}/molecules/${jobId}/${molId}/pose`);
    if (!res.ok) throw new Error("Pose not available");
    return res.text();
  },

  exportCsvUrl(jobId: string): string {
    return `${BASE}/molecules/${jobId}/export/csv`;
  },
};
