import { cn } from "@/lib/cn";

// The Meridian wordmark (fictional carrier — clean inline SVG, navy + brand
// blue meridian-arc glyph) on a light header. "Intelligence Platform" is the
// demo product line beside it. Plain <img> (not next/image) so the SVG serves
// as-is with no optimizer config.
export function Logo({ className }: { className?: string }) {
  return (
    <div
      className={cn("flex items-center gap-3", className)}
      aria-label="Meridian — Intelligence Platform on SingleStore"
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/brand/meridian-logo.svg"
        alt="Meridian"
        className="h-7 w-auto"
      />
      <span className="hidden h-6 w-px bg-gray-300 sm:block" />
      <span className="hidden text-[11px] font-semibold uppercase leading-tight tracking-wide text-gray-500 sm:block">
        Intelligence
        <br />
        Platform
      </span>
    </div>
  );
}
