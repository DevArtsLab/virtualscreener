import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmt(value: number | null | undefined, decimals = 2): string {
  if (value == null) return "—";
  return value.toFixed(decimals);
}

export function scoreColor(score: number | null): string {
  if (score == null) return "text-slate-400";
  if (score >= 8) return "text-emerald-400";
  if (score >= 6) return "text-blue-400";
  if (score >= 4) return "text-amber-400";
  return "text-red-400";
}

export function dockingColor(score: number | null): string {
  if (score == null) return "text-slate-400";
  if (score <= -9) return "text-emerald-400";
  if (score <= -7) return "text-blue-400";
  if (score <= -5) return "text-amber-400";
  return "text-red-400";
}

export const STAGE_LABELS: Record<string, string> = {
  queued: "Queued",
  tier1: "Tier 1 — Molecular Filter",
  tier2: "Tier 2 — ML Scoring",
  tier3: "Tier 3 — Docking",
  done: "Complete",
  error: "Error",
};
