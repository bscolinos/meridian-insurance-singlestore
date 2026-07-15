import {
  ArrowRight,
  ArrowLeftRight,
  Radio,
  HardDrive,
  GitBranch,
  Cloud,
  Layers,
  ShieldCheck,
} from "lucide-react";

// The data-movement strip — the answer to the data-engineering concern: "how
// does data get in and out, across clouds." SingleStore ingests CDC from the
// policy-admin / claims / billing systems, Kafka clickstream & app telemetry,
// and the S3 data lake, unifies into one live engine, and pushes back out
// (egress) to downstream warehouses, BI, and ML feature stores — no bolt-on
// pipeline stack. Runs on AWS, Azure, and GCP. Static / config-driven.

const INGESTION = [
  {
    icon: GitBranch,
    title: "CDC",
    tag: "Policy / claims / billing DBs",
    detail: "Change data capture from policy admin, claims & billing systems.",
    tone: "text-meridian-navy bg-meridian-navy/5 border-meridian-navy/20",
  },
  {
    icon: Radio,
    title: "Kafka / streaming",
    tag: "Clickstream & telemetry",
    detail: "Native pipelines for digital clickstream & app telemetry events.",
    tone: "text-meridian-blue bg-meridian-blue/5 border-meridian-blue/20",
  },
  {
    icon: HardDrive,
    title: "S3 data lake",
    tag: "Batch & files",
    detail: "Parquet, CSV & JSON loaded straight from the object-storage lake.",
    tone: "text-slate-700 bg-slate-50 border-slate-200",
  },
];

const EGRESS = [
  {
    icon: Layers,
    title: "Warehouses",
    detail: "Push curated data downstream on demand.",
  },
  {
    icon: ShieldCheck,
    title: "BI & reporting",
    detail: "Serve exec dashboards straight from the engine.",
  },
  {
    icon: ArrowLeftRight,
    title: "ML feature stores",
    detail: "Feed risk & churn models with fresh, joined features.",
  },
];

const CLOUDS = ["AWS", "Azure", "GCP"];

export function DataMovementStrip() {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white/80 p-5 shadow-sm">
      <div className="mb-1 flex items-center gap-2 text-sm font-semibold text-meridian-navy">
        <ArrowLeftRight className="h-4 w-4 text-s2-purple" />
        Get data in and out — every source, any cloud
      </div>
      <div className="mb-4 text-xs text-gray-500">
        Ingestion, egress, and movement in one engine — no bolt-on pipeline stack.
      </div>

      <div className="flex flex-col items-stretch gap-3 lg:flex-row lg:items-center">
        {/* Ingestion sources */}
        <div className="flex-1">
          <div className="mb-2 text-[11px] font-medium uppercase tracking-wide text-gray-400">
            Ingest
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {INGESTION.map((s) => {
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
        </div>

        <ArrowRight className="mx-auto hidden h-6 w-6 shrink-0 text-gray-300 lg:block" />

        {/* SingleStore engine node */}
        <div className="flex-1 rounded-xl border border-s2-purple/30 bg-gradient-to-br from-s2-purple/[0.06] to-transparent p-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-s2-purple">
            <span className="flex h-5 w-5 items-center justify-center rounded bg-s2-purple text-white">
              <Layers className="h-3 w-3" />
            </span>
            SingleStore
          </div>
          <div className="mt-1 text-[11px] font-medium uppercase tracking-wide text-s2-purple/70">
            One engine for ingest, transform & serve
          </div>
          <div className="mt-1 text-xs text-gray-600">
            Land, join & query live — then move it back out, no separate pipeline tier.
          </div>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {CLOUDS.map((c) => (
              <span
                key={c}
                className="inline-flex items-center gap-1 rounded-full border border-s2-purple/20 bg-white px-2 py-0.5 text-[11px] font-medium text-s2-purple"
              >
                <Cloud className="h-3 w-3" />
                {c}
              </span>
            ))}
          </div>
        </div>

        <ArrowLeftRight className="mx-auto hidden h-6 w-6 shrink-0 text-meridian-teal lg:block" />

        {/* Egress targets */}
        <div className="flex-1">
          <div className="mb-2 text-[11px] font-medium uppercase tracking-wide text-gray-400">
            Egress
          </div>
          <div className="grid grid-cols-1 gap-3">
            {EGRESS.map((t) => {
              const Icon = t.icon;
              return (
                <div
                  key={t.title}
                  className="rounded-xl border border-meridian-teal/25 bg-meridian-teal/5 p-3"
                >
                  <div className="flex items-center gap-2 text-sm font-semibold text-meridian-navy">
                    <Icon className="h-4 w-4 text-meridian-teal" />
                    {t.title}
                  </div>
                  <div className="mt-1 text-xs text-gray-600">{t.detail}</div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
