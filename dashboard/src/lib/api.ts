const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Alert {
  alert_id: string;
  frame_id: string;
  source_id: string;
  description: string;
  severity: number;
  tags: string[];
  thumbnail_base64: string | null;
  timestamp: string;
}

export interface AnalysisResult {
  frame_id: string;
  source_id: string;
  timestamp: string;
  description: string;
  severity: number;
  is_alert: boolean;
  tags: string[];
}

export interface HealthStatus {
  service: string;
  status: string;
  version: string;
  timestamp: string;
}

export async function fetchAlerts(params?: {
  limit?: number;
  offset?: number;
  min_severity?: number;
}): Promise<Alert[]> {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  if (params?.min_severity) searchParams.set("min_severity", String(params.min_severity));

  const res = await fetch(`${API_BASE}/alerts?${searchParams}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch alerts: ${res.status}`);
  return res.json();
}

export async function fetchAlertCount(min_severity?: number): Promise<number> {
  const params = min_severity ? `?min_severity=${min_severity}` : "";
  const res = await fetch(`${API_BASE}/alerts/count${params}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch count: ${res.status}`);
  const data = await res.json();
  return data.count;
}

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Gateway unreachable: ${res.status}`);
  return res.json();
}

export function getWebSocketUrl(): string {
  const wsBase = API_BASE.replace(/^http/, "ws");
  return `${wsBase}/ws/stream`;
}
