import { ShieldCheck, Users, ScrollText, Scale, Globe } from "lucide-react";

// Governance panel for a regulated insurance carrier. As Meridian unifies
// policy, claims, payments, PII and Voice-of-Customer data into one engine,
// compliance / governance / data-standards are front-of-mind for data & EA
// leaders. This panel shows that carrier-grade governance ships WITH the engine
// — not bolted on later. Static / config-driven, no backend.

const CAPABILITIES = [
  {
    icon: Users,
    title: "Role-based access & RLS",
    detail:
      "Row-level security scopes every result by role & line of business.",
    tone: "text-meridian-blue bg-meridian-blue/5 border-meridian-blue/20",
  },
  {
    icon: ScrollText,
    title: "Audit & lineage",
    detail: "Every query logged and traceable — who asked what, when.",
    tone: "text-meridian-navy bg-meridian-navy/5 border-meridian-navy/20",
  },
  {
    icon: Scale,
    title: "Regulatory readiness",
    detail: "Controls aligned to NAIC, state DOI, PCI-DSS & SOC 2.",
    tone: "text-slate-700 bg-slate-50 border-slate-200",
  },
  {
    icon: Globe,
    title: "Data residency",
    detail: "Multi-region deployment keeps PII where regulators require.",
    tone: "text-meridian-teal bg-meridian-teal/5 border-meridian-teal/20",
  },
];

export function GovernanceReadiness() {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white/80 p-5 shadow-sm">
      <div className="mb-1 flex items-center gap-2 text-sm font-semibold text-meridian-navy">
        <ShieldCheck className="h-4 w-4 text-s2-purple" />
        Carrier-grade governance — built in, not bolted on
      </div>
      <div className="mb-4 text-xs text-gray-600">
        Unifying policyholder PII, claims, payments & Voice-of-Customer data
        raises the compliance bar — so governance, auditability & regulatory
        controls come with the engine, not as a stack you assemble later.
      </div>

      {/* Governance capability cards */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {CAPABILITIES.map((c) => {
          const Icon = c.icon;
          return (
            <div key={c.title} className={`rounded-xl border p-3 ${c.tone}`}>
              <div className="flex items-center gap-2">
                <Icon className="h-4 w-4" />
                <span className="text-sm font-semibold">{c.title}</span>
              </div>
              <div className="mt-1 text-xs text-gray-600">{c.detail}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
