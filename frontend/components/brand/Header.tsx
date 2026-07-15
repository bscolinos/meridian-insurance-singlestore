import Link from "next/link";
import { Logo } from "./Logo";

export function Header() {
  return (
    <header className="sticky top-0 z-40 h-16 w-full border-b border-gray-200 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/80">
      <div className="mx-auto flex h-full w-full max-w-6xl items-center gap-4 px-6">
        <Link href="/" className="shrink-0">
          <Logo />
        </Link>

        <div className="ml-auto flex shrink-0 items-center gap-3">
          {/* Powered by SingleStore. */}
          <div className="flex items-center gap-1.5 rounded-full border border-s2-purple/20 bg-s2-purple/5 px-3 py-1.5 text-xs font-medium text-s2-purple">
            <span className="h-2 w-2 rounded-full bg-s2-purple" />
            <span>Powered by SingleStore Aura Analyst</span>
          </div>
        </div>
      </div>
    </header>
  );
}
