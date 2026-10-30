import { JobData, DataPreviewResponse, ExportFormat } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getErrorMessage(response: Response, fallback: string): Promise<string> {
  const error = await response.json().catch(() => ({}));
  return error.detail || error.message || fallback;
}

export async function createGenerationJob(prompt: string, formats: ExportFormat[]): Promise<JobData> {
  const res = await fetch(`${API_BASE}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, formats }),
  });
  if (!res.ok) {
    throw new Error(await getErrorMessage(res, "Failed to start generation job"));
  }
  return res.json();
}

export async function getJob(jobId: string): Promise<JobData> {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}`);
  if (!res.ok) throw new Error("Failed to load job status");
  return res.json();
}

export async function getJobDataPreview(jobId: string, limit = 100): Promise<DataPreviewResponse> {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}/data?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to load data preview");
  return res.json();
}

export async function requestAdditionalExport(jobId: string, formats: ExportFormat[], filters?: Record<string, any>) {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ formats, filters }),
  });
  if (!res.ok) throw new Error(await getErrorMessage(res, "Failed to request export"));
  return res.json();
}

export async function submitFollowup(jobId: string, prompt: string, regenerate = false): Promise<JobData> {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}/followup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, regenerate }),
  });
  if (!res.ok) throw new Error(await getErrorMessage(res, "Failed to process follow-up prompt"));
  return res.json();
}

export function getDownloadUrl(jobId: string, filename: string): string {
  return `${API_BASE}/api/jobs/${jobId}/export/${encodeURIComponent(filename)}`;
}

export function getWebSocketUrl(jobId: string): string {
  const wsBase = API_BASE.replace(/^http/, "ws");
  return `${wsBase}/api/ws/${jobId}`;
}
