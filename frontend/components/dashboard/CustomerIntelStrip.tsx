"use client";

import { useEffect, useState } from "react";
import { Sparkles, ShieldAlert, ArrowRight } from "lucide-react";
import { fetchAtRisk, type AtRisk } from "@/lib/api";

// Pillar 2 — the AI Customer Intelligence Platform "at-risk" scoreboard. Reads
// GET /api/cip/at_risk on mount and frames the numbers as the CIP watching live
// behavioral signals (payment friction, quote abandonment, auth friction,
// sentiment drops, claim friction) and recommending next-best actions to
// predict & prevent negative customer outcomes. Amber/red = at-risk.
// Dollars are honest (never scaled).

// Honest dollar formatting — $X.XB / $XXXM / $XXXK.
function fmtDollars(n: number): string {
  if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `$${Math.round(n / 1e6)}M`;
  if (n >= 1e3) return `$${Math.round(n / 1e3)}K`;
  return `$${Math.round(n)}`;
}

function fmtInt(n: number): string {
  return Math.round(n).toLocaleString();
}

// Turn a compact enum-ish label ("PaymentFriction") into readable text
// ("Payment Friction") for chips and the breakdown list.
function humanize(s: string): string {
  return s.replace(/([a-z])([A-Z])/g, "$1 $2");
}

export function CustomerIntelStrip() {
  const [data, setData] = useState<AtRisk | null>(null);

  useEffect(() => {
    fetchAtRisk().then(setData);
  }, []);

  const dash = "—";
  const bySignal = data?.by_signal ?? [];
  const maxLtv = bySignal.reduce((m, s) => Math.max(m, s.ltv), 0) || 1;

  return (
    <div className="rounded-2xl border border-meridian-amber/30 bg-gradient-to-br from-meridian-amber/[0.05] to-transparent p-5 shadow-sm">
      <div className="mb-1 flex items-center gap-2 text-sm font-semibold text-meridian-navy">
        <ShieldAlert className="h-4 w-4 text-meridian-amber" />
        Customer Intelligence — predict &amp; prevent
      </div>
      <div className="mb-4 flex items-center gap-1.5 text-xs text-gray-600">
        <Sparkles className="h-3.5 w-3.5 text-s2-purple" />
        The CIP is watching live behavioral signals across every policyholder and
        recommending the next best action — while the customer is still engaged.
      </div>

      <div className="flex flex-col gap-4 lg:flex-row lg:items-stretch">
        {/* Headline at-risk figures */}
        <div className="flex flex-1 gap-3">
          <div className="flex-1 rounded-xl border border-meridian-amber/30 bg-white p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-gray-500">
              At-risk customers
            </div>
            <div className="mt-1 text-3xl font-bold tabular-nums text-meridian-amber">
              {data ? fmtInt(data.at_risk_customers) : dash}
            </div>
            <div className="mt-0.5 text-xs text-gray-400">
              Carrying an active risk signal
            </div>
          </div>
          <div className="flex-1 rounded-xl border border-gray-200 bg-white p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-gray-500">
              Lifetime value at risk
            </div>
            <div className="mt-1 text-3xl font-bold tabular-nums text-meridian-navy">
              {data ? fmtDollars(data.at_risk_ltv) : dash}
            </div>
            <div className="mt-0.5 text-xs text-gray-400">
              Recoverable with the right action
            </div>
          </div>
        </div>

        {/* Top signal + recommended action chips */}
        <div className="flex flex-1 flex-col justify-center gap-3 rounded-xl border border-gray-200 bg-white p-4">
          <div>
            <div className="mb-1 text-[11px] font-medium uppercase tracking-wide text-gray-400">
              Top risk signal
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-meridian-amber/30 bg-meridian-amber/10 px-2.5 py-1 text-sm font-semibold text-meridian-amber">
              <ShieldAlert className="h-3.5 w-3.5" />
              {data ? humanize(data.top_signal) : dash}
            </span>
          </div>
          <div className="flex items-center gap-2 text-gray-300">
            <ArrowRight className="h-4 w-4" />
            <span className="text-[11px] font-medium uppercase tracking-wide text-gray-400">
              Next best action
            </span>
          </div>
          <div>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-meridian-teal/30 bg-meridian-teal/10 px-2.5 py-1 text-sm font-semibold text-meridian-teal">
              <Sparkles className="h-3.5 w-3.5" />
              {data ? humanize(data.top_action) : dash}
            </span>
          </div>
        </div>

        {/* By-signal breakdown */}
        <div className="flex-1 rounded-xl border border-gray-200 bg-white p-4">
          <div className="mb-2 text-[11px] font-medium uppercase tracking-wide text-gray-400">
            By risk signal
          </div>
          {bySignal.length === 0 ? (
            <div className="text-xs text-gray-400">
              {data ? "No active signals." : "Loading live signals…"}
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {bySignal.map((s) => (
                <div key={s.risk_signal}>
                  <div className="flex items-baseline justify-between gap-2 text-xs">
                    <span className="font-medium text-meridian-navy">
                      {humanize(s.risk_signal)}
                    </span>
                    <span className="tabular-nums text-gray-500">
                      {fmtInt(s.customers)} · {fmtDollars(s.ltv)}
                    </span>
                  </div>
                  <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
                    <div
                      className="h-full rounded-full bg-meridian-amber"
                      style={{
                        width: `${Math.max(4, (s.ltv / maxLtv) * 100)}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
