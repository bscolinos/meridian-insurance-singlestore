import { ArrowRight, FileText, ShieldCheck, Sparkles, Activity, Layers } from "lucide-react";

// The lifecycle-architecture strip — the money visual for "one engine, end to
// end." Enova's lending lifecycle spans application & decisioning → origination
// & funding → servicing & portfolio; today those live in separate analytics
// silos. They flow INTO SingleStore, which unifies them into one live
// transactional + analytical layer that Aura Analyst answers questions against.
// Static / config-driven, no backend.

const SOURCES = [
  {
    icon: ShieldCheck,
    title: "Application & Decisioning",
    tag: "Top of funnel",
    detail: "Applications, ML model scores, and fraud flags.",
    tone: "text-slate-700 bg-slate-50 border-slate-200",
  },
  {
    icon: FileText,
    title: "Origination & Funding",
    tag: "The book",
    detail: "Funded loans, brands, APR & terms.",
    tone: "text-enova-blue bg-enova-blue/5 border-enova-blue/20",
  },
  {
    icon: Activity,
    title: "Servicing & Portfolio",
    tag: "Repayment truth",
    detail: "Payments, collections, and delinquency.",
    tone: "text-enova-navy bg-enova-navy/5 border-enova-navy/20",
  },
];

export function ArchStrip() {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white/80 p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-enova-navy">
        <Layers className="h-4 w-4 text-s2-purple" />
        One engine across the lending lifecycle — not another silo
      </div>

      <div className="flex flex-col items-stretch gap-3 lg:flex-row lg:items-center">
        {/* Source stages */}
        <div className="grid flex-1 grid-cols-1 gap-3 sm:grid-cols-3">
          {SOURCES.map((s) => {
            const Icon = s.icon;
            return (
              <div key={s.title} className={`rounded-xl border p-3 ${s.tone}`}>
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4" />
                  <span className="text-sm font-semibold">{s.title}</span>
                </div>
                <div className="mt-1 text-[11px] font-medium uppercase tracking-wide opacity-70">
                  {s.tag}
                </div>
                <div className="mt-1 text-xs text-gray-600">{s.detail}</div>
              </div>
            );
          })}
        </div>

        <ArrowRight className="mx-auto hidden h-6 w-6 shrink-0 text-gray-300 lg:block" />

        {/* SingleStore unification layer */}
        <div className="flex-1 rounded-xl border border-s2-purple/30 bg-gradient-to-br from-s2-purple/[0.06] to-transparent p-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-s2-purple">
            <span className="flex h-5 w-5 items-center justify-center rounded bg-s2-purple text-white">
              <Layers className="h-3 w-3" />
            </span>
            SingleStore
          </div>
          <div className="mt-1 text-[11px] font-medium uppercase tracking-wide text-s2-purple/70">
            Unifies into one live transactional + analytical layer
          </div>
          <div className="mt-1 text-xs text-gray-600">
            Applications, loans, payments & portfolio joined in one engine.
          </div>
        </div>

        <ArrowRight className="mx-auto hidden h-6 w-6 shrink-0 text-gray-300 lg:block" />

        {/* Aura Analyst node */}
        <div className="flex-1 rounded-xl border border-enova-navy/25 bg-enova-navy p-3 text-white">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Sparkles className="h-4 w-4 text-enova-green" />
            Aura Analyst
          </div>
          <div className="mt-1 text-[11px] font-medium uppercase tracking-wide text-white/60">
            Plain-English, across the whole lifecycle
          </div>
          <div className="mt-1 text-xs text-white/80">
            Risk, portfolio & ops ask; Aura writes the SQL and answers.
          </div>
        </div>
      </div>
    </div>
  );
}
