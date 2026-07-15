"use client";

import { useEffect, useState } from "react";
import { fetchKpis, type OverviewKpis } from "@/lib/api";
import { KpiCard } from "./KpiCard";

function fmtInt(n: number): string {
  return Math.round(n).toLocaleString();
}

// Approval time in hours, exact — "XX.Xh". Not scaled.
function fmtHours(n: number): string {
  return `${n.toFixed(1)}h`;
}

// Payment failure rate as "XX.X%", exact. Accepts either a fraction (0..1) or
// an already-percent value (e.g. 8.4) from the backend. Not scaled.
function fmtPct(n: number): string {
  const pct = n <= 1 ? n * 100 : n;
  return `${pct.toFixed(1)}%`;
}

// Normalize the failure rate to a percentage number so we can flag "elevated".
function pctValue(n: number): number {
  return n <= 1 ? n * 100 : n;
}

export function KpiRow() {
  const [kpis, setKpis] = useState<OverviewKpis | null>(null);

  useEffect(() => {
    fetchKpis().then(setKpis);
  }, []);

  const dash = "—";
  // Display-only scaling so the COUNT cards reflect a full production footprint
  // (millions of policyholders). Applies ONLY to integer counts (open_claims,
  // active_policies). Hours and rates stay exact — never scaled.
  const S = 100;

  // Payment failure rate is a live-incident signal — flag it amber/red when it
  // rises materially above the book average (~8% per the domain spec).
  const failElevated =
    kpis != null && pctValue(kpis.payment_failure_rate_24h) >= 12;

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <KpiCard
        label="Open claims"
        value={kpis ? fmtInt(kpis.open_claims * S) : dash}
        sub="Not yet paid, closed or denied"
      />
      <KpiCard
        label="Avg approval time · 24h"
        value={kpis ? fmtHours(kpis.avg_approval_hours_24h) : dash}
        sub="Claims decided in the last 24h"
      />
      <KpiCard
        label="Payment failure rate · 24h"
        value={kpis ? fmtPct(kpis.payment_failure_rate_24h) : dash}
        sub={
          failElevated
            ? "Elevated vs book average"
            : "Failed payments, last 24h"
        }
        accent={failElevated}
      />
      <KpiCard
        label="Active policies"
        value={kpis ? fmtInt(kpis.active_policies * S) : dash}
        sub="In-force across all lines"
      />
    </div>
  );
}
