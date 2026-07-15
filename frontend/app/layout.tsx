import "./globals.css";
import type { Metadata } from "next";
import { Header } from "@/components/brand/Header";
import { Footer } from "@/components/brand/Footer";

export const metadata: Metadata = {
  title: "Meridian — Intelligence Platform, powered by SingleStore",
  description:
    "Every policyholder signal, in plain English — one live engine from the "
    + "first click to the final claim. SingleStore Aura Analyst powers "
    + "real-time operational intelligence across claims, underwriting, "
    + "payments, and fraud, plus an AI Customer Intelligence Platform that "
    + "predicts and prevents negative customer outcomes before they happen.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col bg-[#f5f7fa] text-gray-900">
        {/* Subtle brand wash behind the whole app. */}
        <div
          aria-hidden
          className="pointer-events-none fixed inset-0 -z-10 bg-gradient-to-b from-meridian-navy/[0.05] via-transparent to-transparent"
        />
        <Header />
        <main className="flex-1 w-full">
          <div className="mx-auto w-full max-w-6xl px-6 py-8">{children}</div>
        </main>
        <Footer />
      </body>
    </html>
  );
}
