"""FastAPI entrypoint for the Meridian Intelligence Platform demo.

Meridian Mutual Insurance runs on ONE engine, and the demo tells a two-pillar
story about what that unlocks:

  Pillar 1 — Real-Time Operational Intelligence. Claims, underwriting queues,
  billing/payments, and fraud investigations stream into a single SingleStore
  database and are analyzable in the same instant they land. Employees ask in
  plain English — "Why did claim approvals slow down yesterday?", "Which
  underwriting queues are backlogged?", "What payment systems are failing?" —
  and get millisecond answers on LIVE operational data, not overnight warehouse
  snapshots.

  Pillar 2 — AI Customer Intelligence Platform. Identity, policies, claims,
  payments, Voice-of-Customer feedback, call-center interactions, and digital
  clickstream are fused into one operational view. The platform doesn't just
  report history — it recognizes behavioral signals (payment friction, quote
  abandonment, auth failures, declining sentiment, claim friction) and
  recommends the next best action to predict and prevent negative outcomes
  before they happen, while the customer is still engaged.

Aura Analyst is the centerpiece: an ops leader, underwriter, or CX analyst asks
a plain-English question and Aura writes the SQL, runs it on the unified
database, and streams back the answer. The backend holds the server-side
Analyst API key and proxies requests — the browser never sees the key.

Routes:
  GET  /health              -> liveness + row counts + whether Analyst is configured
  GET  /api/overview/kpis   -> Pillar-1 operational KPI row
  GET  /api/cip/at_risk     -> Pillar-2 Customer-Intelligence at-risk summary
  POST /analyst/query       -> single JSON object (sql / data / chart / text)
  POST /analyst/chat        -> passthrough SSE stream (reasoning + token deltas)
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load the demo-root .env whether uvicorn is launched from backend/ or the
# demo root, then fall back to a plain cwd search.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv()

import singlestore  # noqa: E402

app = FastAPI(
    title="Meridian Intelligence Platform (SingleStore Aura Analyst)",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://localhost:\d+$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    configured = bool(
        os.environ.get("ANALYST_API_URL") and os.environ.get("ANALYST_API_KEY")
    )
    try:
        counts = singlestore.table_counts()
    except Exception:  # noqa: BLE001
        counts = {}
    return {
        "ok": True,
        "demo": os.environ.get("DEMO_NAME", "meridian-insurance"),
        "analyst_configured": configured,
        "row_counts": counts,
    }


# --- Dashboard KPIs --------------------------------------------------------
try:
    from routers import dashboard  # noqa: E402

    app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
except Exception:  # noqa: BLE001
    pass


# --- Aura Analyst (natural-language text-to-SQL) ---------------------------
# Guarded import so a missing/broken router never bricks boot.
try:
    from routers import analyst  # noqa: E402

    app.include_router(analyst.router, prefix="/analyst", tags=["analyst"])
except Exception:  # noqa: BLE001
    pass
