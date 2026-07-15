# Meridian × SingleStore — Intelligence Platform (Aura Analyst demo)

A co-branded, single-page demo for **Meridian Mutual Insurance** (a fictional
large, multiline U.S. carrier — Personal, Commercial, and Specialty lines). It
makes **SingleStore Aura Analyst** the hero: a natural-language layer that lets a
claims, underwriting, payments, or customer-experience leader ask plain-English
questions across the whole business and get governed SQL answers instantly, on
**live** operational data — not a stale warehouse snapshot.

Tagline on the hero: **"Every policyholder signal, in plain English — one live
engine from the first click to the final claim."**

## The story it tells — two pillars

**Pillar 1 — Real-Time Operational Intelligence.** Replace disconnected
operational + analytical silos with one engine that delivers millisecond
analytics on live business data. Ask *"Why did claim approvals slow down
yesterday?"*, *"Which underwriting queues are backlogged?"*, *"What payment
systems are failing?"*, *"Where are fraud investigations increasing?"* — and get
immediate, accurate answers on current operational data.

**Pillar 2 — AI Customer Intelligence Platform (predict & prevent).** Unify
identity, policies, claims, payments, Voice-of-Customer, call transcripts,
clickstream/page visits/journeys, and app telemetry into a single operational
view. Recognize behavioral signals (repeated payment attempts, excessive
refreshes, abandoned quotes, repeated auth failures, declining sentiment,
unusual claims activity) and recommend the **next-best action** while the
customer is still engaged — reducing lapse, accelerating claims, and proactively
engaging.

## What it shows (money moments — click the chips)

Operational (Pillar 1):
1. Why claim approvals slowed in the last 24h — avg approval time by product line
   (Home/Property stands out).
2. Which underwriting queues are most backlogged (Commercial-Property).
3. Payment systems with elevated failure rates (CardGateway) + top failure reason.
4. Where fraud investigations are increasing — last-30d vs prior-30d.

Customer intelligence (Pillar 2):
5. How many high-value customers are at risk, by risk signal.
6. The single best next-best-action by total customer LTV at risk.
7. Which feedback topic has the lowest sentiment, and how it relates to churn.
8. Customers with repeated payment retries + auth failures flagged for retention.

## Stack

- **Backend** — FastAPI (`backend/`). Thin Aura Analyst proxy
  (`routers/analyst.py`, key server-side) + dashboard endpoints
  (`routers/dashboard.py`: `/api/overview/kpis` + `/api/cip/at_risk`). Connects
  to SingleStore via `singlestore.py`.
- **Frontend** — Next.js App Router + Tailwind (`frontend/`). Co-branded hero,
  data-movement strip, operational KPI row, **Customer Intelligence at-risk
  strip** (`CustomerIntelStrip.tsx`), governance strip, and the dominant
  `AnalystChat` (SSE streaming with live reasoning + recharts viz).
- **Data** — `backend/db/` — `schema.sql` (10 tables + `v_customer_360`),
  `apply.py`, `generate_data.py` (deterministic, 6 planted money-moment cohorts),
  `seed_minimal.py` (reduced-volume seed for a quick populate).

Brand colors: navy `#0A2540`, blue `#1E5EFF`, teal `#0FB5AE`, amber `#F5A623`,
alongside SingleStore purple `#553BCC` for all Aura chrome.

## Database — `meridian_intel`

The customer is the join spine; all customer-scoped facts SHARD on `customer_id`
so identity → policy → claim → payment → interaction joins stay local.

| Table | Role | Store |
| --- | --- | --- |
| `customers`, `policies` | Identity + policy portfolio | rowstore |
| `claims`, `underwriting_queue`, `payment_transactions`, `fraud_investigations` | Real-time operations (Pillar 1) | columnstore |
| `interactions`, `web_events`, `voc_feedback` | Customer-intelligence signals (Pillar 2) | columnstore |
| `customer_signals` | At-risk scoreboard (risk_signal + recommended_action) | rowstore |
| `v_customer_360` | Unified per-customer view | view |

See `docs/DOMAIN_SPEC.md` (binding contract) and `docs/SCHEMA.md`.

## Run it

```bash
source /Users/billscolinos/Documents/code_factory/.venv/bin/activate
cp .env.example .env   # then fill SINGLESTORE_* for your workspace

# 1. schema (idempotent)
python backend/db/apply.py

# 2. seed data — minimal / fast:
python backend/db/seed_minimal.py
#    OR full production volume:
python backend/db/generate_data.py

# 3. backend -> :8050
cd backend && uvicorn main:app --reload --port 8050

# 4. frontend -> :3000
cd ../frontend && npm install && npm run dev
```

Health: `curl localhost:8050/health`. KPIs: `curl localhost:8050/api/overview/kpis`.
Customer intelligence: `curl localhost:8050/api/cip/at_risk`.

The frontend expects the backend at `http://localhost:8050` (see `lib/api.ts` /
`NEXT_PUBLIC_BACKEND_URL`).

## Aura Analyst setup (one-time, in the Portal — the app can't do this)

> **Status:** wired & verified — the `meridian_intel` domain is crawled and the
> endpoint + key are in `.env`, so `/health` reports `analyst_configured: true`.
> The steps below are how it was done (and how to re-point it to a new domain).

`analyst_configured` is `false` until you wire a crawled domain:

1. SingleStore Portal → **Analyst** → create/select a domain pointed at the
   workspace + `meridian_intel` database → **Crawl**.
2. Domain settings → **API Keys** → **Copy Endpoint** (ends `/analyst/chat`) and
   **Create API Key** (shown once).
3. Put them in `.env` (`ANALYST_API_URL`, `ANALYST_API_KEY`). Watch for JWT
   homoglyph corruption when pasting the key (a non-ASCII char in the
   `validForPortal` claim can cause a 401 — scan with `grep -P '[^\x00-\x7F]'`).
4. Re-crawl whenever the schema changes.

## Verification oracle

`generate_data.py` / `seed_minimal.py` print the oracle after loading — the six
money moments (Home claim slowdown ~66h vs ~33h; Commercial-Property backlog
~142h; CardGateway failures ~22%; fraud up ~1.7×; PaymentFriction top at-risk
signal + PaymentAssist top action by LTV; Claims lowest VoC sentiment). These are
what Aura's answers should match.
