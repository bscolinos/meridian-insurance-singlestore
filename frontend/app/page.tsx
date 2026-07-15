import { Sparkles } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { AnalystChat } from "@/components/analyst/AnalystChat";
import { DataMovementStrip } from "@/components/dashboard/DataMovementStrip";
import { KpiRow } from "@/components/dashboard/KpiRow";
import { CustomerIntelStrip } from "@/components/dashboard/CustomerIntelStrip";
import { GovernanceReadiness } from "@/components/dashboard/GovernanceReadiness";

export default function HomePage() {
  return (
    <div className="flex flex-col gap-6">
      {/* Co-branded hero */}
      <section className="rounded-2xl border border-gray-200 bg-gradient-to-br from-meridian-navy to-meridian-blue px-7 py-8 text-white shadow-sm">
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-white/70">
          <span>Meridian</span>
          <span className="text-white/30">×</span>
          <span>SingleStore</span>
        </div>
        <h1 className="mt-3 max-w-3xl text-3xl font-bold leading-tight">
          Every policyholder signal, in plain English —
          <span className="text-meridian-teal">
            {" "}
            one live engine from the first click to the final claim.
          </span>
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-white/80">
          Meridian&apos;s business — claims, underwriting, billing &amp;
          payments, fraud, and the digital customer experience — lives in
          disconnected operational and analytical silos today, so leaders work
          off stale snapshots. SingleStore unifies it into one live engine:
          real-time operational intelligence answers <em>&ldquo;why did claim
          approvals slow down?&rdquo;</em> on current data, while the AI Customer
          Intelligence Platform fuses identity, policies, Voice-of-Customer,
          transcripts, clickstream &amp; telemetry to predict and prevent
          negative customer outcomes — recommending the next best action while
          the customer is still engaged.
        </p>
      </section>

      {/* Data movement — every source in, any cloud out, one engine. */}
      <DataMovementStrip />

      {/* Pillar 1 — real-time operational headline KPIs. */}
      <KpiRow />

      {/* Pillar 2 — the AI Customer Intelligence "predict & prevent" scoreboard. */}
      <CustomerIntelStrip />

      {/* Carrier-grade governance — regulated-insurance compliance, built in. */}
      <GovernanceReadiness />

      {/* Aura Analyst — the dominant element. */}
      <Card className="overflow-hidden">
        <CardHeader className="border-b border-gray-100 bg-gradient-to-r from-s2-purple/[0.05] to-transparent">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Sparkles className="h-5 w-5 text-s2-purple" />
            Ask Aura Analyst
          </CardTitle>
          <CardDescription>
            Plain-English questions over the whole unified layer — identity,
            policies, claims, payments, Voice-of-Customer, call-center
            transcripts, digital clickstream and application telemetry, all in
            one engine. Follow-ups reuse the same session, so you can say
            &ldquo;now break that down by product line&rdquo;.
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-6">
          <AnalystChat />
        </CardContent>
      </Card>
    </div>
  );
}
