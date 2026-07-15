import { cn } from "@/lib/cn";

export function KpiCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border bg-white p-4 shadow-sm",
        accent
          ? "border-meridian-amber/40 ring-1 ring-meridian-amber/10"
          : "border-gray-200",
      )}
    >
      <div className="text-xs font-medium uppercase tracking-wide text-gray-500">
        {label}
      </div>
      <div
        className={cn(
          "mt-1 text-2xl font-bold tabular-nums",
          accent ? "text-meridian-amber" : "text-meridian-navy",
        )}
      >
        {value}
      </div>
      {sub && <div className="mt-0.5 text-xs text-gray-400">{sub}</div>}
    </div>
  );
}
