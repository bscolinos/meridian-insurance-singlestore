// Base URL for the Meridian Intelligence Platform backend (FastAPI).
// Defaults to http://localhost:8050; override with NEXT_PUBLIC_BACKEND_URL.

export function apiBase(): string {
  if (typeof process !== "undefined" && process.env.NEXT_PUBLIC_BACKEND_URL) {
    return process.env.NEXT_PUBLIC_BACKEND_URL;
  }
  return "http://localhost:8050";
}

// Pillar 1 — real-time operational KPI row (GET /api/overview/kpis).
export interface OverviewKpis {
  open_claims: number;
  avg_approval_hours_24h: number;
  payment_failure_rate_24h: number;
  active_policies: number;
}

export async function fetchKpis(): Promise<OverviewKpis | null> {
  try {
    const res = await fetch(`${apiBase()}/api/overview/kpis`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as OverviewKpis;
  } catch {
    return null;
  }
}

// Pillar 2 — Customer Intelligence "at-risk" scoreboard (GET /api/cip/at_risk).
export interface AtRisk {
  at_risk_customers: number;
  at_risk_ltv: number;
  top_signal: string;
  top_action: string;
  by_signal: { risk_signal: string; customers: number; ltv: number }[];
}

export async function fetchAtRisk(): Promise<AtRisk | null> {
  try {
    const res = await fetch(`${apiBase()}/api/cip/at_risk`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as AtRisk;
  } catch {
    return null;
  }
}
