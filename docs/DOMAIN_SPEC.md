# Meridian Insurance × SingleStore — DOMAIN SPEC (binding contract)

> This file is the **single source of truth** for the demo. Every subagent
> building DB / backend / frontend files MUST conform to the names, types,
> counts, cohorts, and contracts below. When in doubt, this document wins.
> Reference demo (same architecture / Aura proxy pattern): `demos/enova-analyst`.

---

## 1. The company & the pitch

**Meridian Mutual Insurance** (fictional) — a large, multiline U.S. insurance
carrier serving **millions of policyholders** across **Personal** (auto, home,
renters), **Commercial** (BOP, commercial auto, workers' comp), and **Specialty**
(umbrella, cyber, marine) lines. The business spans underwriting, claims,
billing & payments, customer service (call center + digital), and the mobile /
web customer experience.

**Audience:** Directors of Data Engineering, VoC Data Engineering, AVPs of
Software Engineering & Infrastructure, VPs of Data & AI, Enterprise Architecture
— technical leaders evaluating the next-gen data platform.

**The problem (today):** data is fragmented across transactional DBs, streaming
platforms, data lakes, and cloud warehouses. Batch ETL shuttles data around all
day, jobs fail and need babysitting, and executives work off **stale** snapshots
— claims / underwriting / payments / reconciliation / exec dashboards lag **30
minutes to overnight**. You can't see current business conditions or react in
real time.

**The SingleStore promise (two pillars — BOTH must land in the demo):**

- **Pillar 1 — Real-Time Operational Intelligence.** Replace the disconnected
  operational + analytical silos with **one engine** that continuously ingests
  streaming events, serves thousands of concurrent users, and delivers
  **millisecond analytics on live business data**. Employees ask in plain
  English — *"Why did claim approvals slow down yesterday?"*, *"Which
  underwriting queues are backlogged?"*, *"What payment systems are failing?"*,
  *"Where are fraud investigations increasing?"* — and get immediate, accurate
  answers on **current operational data**, not delayed warehouse snapshots.

- **Pillar 2 — AI Customer Intelligence Platform.** Unify customer identity,
  policies, claims, payments, **Voice-of-Customer** feedback, **call-center
  transcripts**, **digital clickstream / page visits / journeys**, and
  **application telemetry** into a single operational view. Don't just report
  history — **predict and prevent negative outcomes before they happen**.
  Recognize behavioral signals (repeated payment attempts, excessive page
  refreshes, abandoned quotes, repeated auth failures, declining sentiment,
  unusual claims activity) and **recommend or trigger the next best action** —
  while the customer is still engaged — to improve experience, accelerate
  claims, reduce policy lapse, optimize underwriting, and proactively engage.

**Tagline:** *"Every policyholder signal, in plain English — one live engine
from the first click to the final claim."*

**Aura Analyst is the centerpiece.** NL chat is the dominant surface. A KPI row
+ data-movement strip + governance strip + a **Customer Intelligence "at-risk"
strip** are supporting evidence that the whole business lives in one engine.

---

## 2. Brand

- **Name shown:** `Meridian` (wordmark) + product line `Intelligence Platform`.
- **Co-brand:** `Meridian × SingleStore`.
- **Colors (fictional carrier — trustworthy insurance navy/blue):**
  - `meridian.navy` = `#0A2540` (primary dark ink / hero gradient start)
  - `meridian.blue` = `#1E5EFF` (primary brand blue / hero gradient end)
  - `meridian.teal` = `#0FB5AE` (secondary accent — "healthy"/positive)
  - `meridian.amber` = `#F5A623` (warning / at-risk accent)
  - `meridian.red`  = `#E5484D` (critical / failure accent)
- **SingleStore purple** `#553BCC` (`s2.purple`) for all Aura / "Powered by"
  chrome — DO NOT recolor the Aura chrome to a Meridian color.
- **Logo:** no real logo exists (fictional co.). The logo subagent creates a
  clean inline SVG wordmark ("Meridian" with a small meridian-arc / globe glyph)
  in `frontend/public/brand/meridian-logo.svg` (+ `-white.svg` for dark header).
- Tailwind: define `meridian.*` and `s2.*`. Keep legacy aliases `enova.*`,
  `bm.*`, `rev.*` pointing at Meridian hexes so any un-migrated className still
  renders on-brand (the enova skeleton uses `enova-*`, `rev-*`, `s2-*`).

---

## 3. Database — `meridian_intel`

MySQL-wire SingleStore (reports 5.7.32). **No FK constraints.** Data-gen supplies
explicit ids (no AUTO_INCREMENT). Idempotent, re-runnable DDL.

**Sharding rule (critical for the "one engine, local joins" story):** the
customer is the join spine. All **customer-scoped** high-volume facts SHARD on
`customer_id` so the identity→policy→claim→payment→interaction join is local.

> **Columnstore PK gotcha (from enova):** a columnstore table can't have a
> PRIMARY KEY that isn't the shard key. Use `KEY (id) USING HASH` (a secondary
> hash index), NOT `PRIMARY KEY`, on columnstore facts. Rowstore dims use
> `PRIMARY KEY`. This bit us before — honor it.

### 3.1 Dimensions (rowstore)

**`customers`** — the policyholder identity spine (~4,000 at full volume).
`PRIMARY KEY (customer_id)`, `SHARD KEY (customer_id)`.
| col | type | notes |
|---|---|---|
| customer_id | BIGINT NOT NULL | |
| segment | VARCHAR(12) | Personal / Commercial / Specialty |
| tenure_years | INT | years as a customer |
| home_state | CHAR(2) | US 2-letter |
| region | VARCHAR(12) | West / Midwest / South / Northeast |
| lifetime_value | DECIMAL(12,2) | total premiums paid to date |
| risk_tier | VARCHAR(10) | Preferred / Standard / Elevated |
| acquisition_channel | VARCHAR(16) | Agent / Direct / Aggregator / Partner / Renewal |
| signup_date | DATE | |
| churn_risk_score | DECIMAL(6,4) | 0..1, higher = more likely to lapse |
| is_active | BOOLEAN | |

**`policies`** — issued policies (~7,500). rowstore, `PRIMARY KEY (policy_id)`,
`SHARD KEY (customer_id)` (co-locates with customer + downstream facts;
rowstore allows a PK distinct from the shard key).
| col | type | notes |
|---|---|---|
| policy_id | BIGINT NOT NULL | |
| customer_id | BIGINT | |
| segment | VARCHAR(12) | denormalized |
| product_line | VARCHAR(20) | Auto / Home / Renters / BOP / CommercialAuto / WorkersComp / Umbrella / Cyber / Marine |
| status | VARCHAR(14) | Active / Lapsed / Cancelled / PendingRenewal |
| annual_premium | DECIMAL(12,2) | |
| coverage_limit | DECIMAL(14,2) | |
| deductible | DECIMAL(10,2) | |
| effective_date | DATE | |
| renewal_date | DATE | |
| state | CHAR(2) | |

### 3.2 Operational facts (columnstore) — Pillar 1

**`claims`** (~12,000) — the claims lifecycle fact. `KEY (claim_id) USING HASH`,
`SHARD KEY (customer_id)`, `SORT KEY (fnol_at)`.
| col | type | notes |
|---|---|---|
| claim_id | BIGINT NOT NULL | |
| policy_id | BIGINT | |
| customer_id | BIGINT | |
| segment | VARCHAR(12) | |
| product_line | VARCHAR(20) | |
| claim_type | VARCHAR(20) | Collision / Property / Liability / Theft / Injury / BusinessInterruption / Cyber |
| status | VARCHAR(14) | Submitted / InReview / Approved / Denied / Paid / Closed |
| fnol_at | DATETIME | first notice of loss (submission time) |
| decision_at | DATETIME | NULL until decided |
| approval_hours | DECIMAL(8,2) | NULL until decided; hours(decision_at − fnol_at) |
| claim_amount | DECIMAL(12,2) | claimed |
| approved_amount | DECIMAL(12,2) | paid/approved (≤ claim_amount; 0 if denied) |
| adjuster_id | BIGINT | |
| fraud_investigation | BOOLEAN | referred to SIU |

**`underwriting_queue`** (~3,500) — new-business & renewal submissions in the
funnel. `KEY (submission_id) USING HASH`, `SHARD KEY (customer_id)`,
`SORT KEY (submitted_at)`. Drives the "backlogged queues" money moment.
| col | type | notes |
|---|---|---|
| submission_id | BIGINT NOT NULL | |
| customer_id | BIGINT | |
| segment | VARCHAR(12) | |
| product_line | VARCHAR(20) | |
| queue_name | VARCHAR(24) | Personal-Auto / Commercial-Property / Specialty-Cyber / Workers-Comp / Home / Umbrella |
| status | VARCHAR(14) | Received / InReview / PendingInfo / Approved / Declined |
| priority | VARCHAR(8) | Low / Medium / High |
| submitted_at | DATETIME | |
| decided_at | DATETIME | NULL if still open |
| age_hours | DECIMAL(8,2) | hours in queue (to decided_at or NOW) |
| assigned_underwriter | BIGINT | |

**`payment_transactions`** (~40,000) — billing/payment attempts across payment
systems. `KEY (txn_id) USING HASH`, `SHARD KEY (customer_id)`,
`SORT KEY (created_at)`. Drives the "elevated failure rates" money moment.
| col | type | notes |
|---|---|---|
| txn_id | BIGINT NOT NULL | |
| customer_id | BIGINT | |
| policy_id | BIGINT | |
| payment_system | VARCHAR(16) | ACH / CardGateway / Lockbox / Wallet / AgentPortal |
| amount | DECIMAL(12,2) | |
| status | VARCHAR(10) | Success / Failed / Pending |
| failure_reason | VARCHAR(20) | NULL if success; Insufficient / Gateway / Expired / Timeout / Fraud |
| attempt_no | INT | 1..N retries for the same bill |
| created_at | DATETIME | |

**`fraud_investigations`** (~900) — SIU cases opened on suspicious claims.
`KEY (case_id) USING HASH`, `SHARD KEY (customer_id)`, `SORT KEY (opened_at)`.
| col | type | notes |
|---|---|---|
| case_id | BIGINT NOT NULL | |
| claim_id | BIGINT | |
| customer_id | BIGINT | |
| segment | VARCHAR(12) | |
| product_line | VARCHAR(20) | |
| fraud_type | VARCHAR(16) | Staged / Exaggerated / Identity / Premium / Provider |
| status | VARCHAR(12) | Open / Investigating / Confirmed / Cleared |
| suspected_amount | DECIMAL(12,2) | |
| opened_at | DATETIME | |

### 3.3 Customer-Intelligence signals (columnstore) — Pillar 2

**`interactions`** (~30,000) — omnichannel touch log: calls, chats, portal &
mobile sessions. `KEY (interaction_id) USING HASH`, `SHARD KEY (customer_id)`,
`SORT KEY (occurred_at)`.
| col | type | notes |
|---|---|---|
| interaction_id | BIGINT NOT NULL | |
| customer_id | BIGINT | |
| channel | VARCHAR(12) | CallCenter / Chat / Web / Mobile / Email |
| intent | VARCHAR(20) | Billing / Claim / Quote / Coverage / Complaint / TechSupport |
| sentiment | DECIMAL(5,3) | −1..1 (NULL for pure page views) |
| duration_sec | INT | |
| resolved | BOOLEAN | |
| escalated | BOOLEAN | handed to a supervisor / retention |
| occurred_at | DATETIME | |

**`web_events`** (~60,000) — digital clickstream / page visits / app telemetry.
`KEY (event_id) USING HASH`, `SHARD KEY (customer_id)`, `SORT KEY (occurred_at)`.
Drives "abandoned quotes / excessive refreshes / repeated auth failures".
| col | type | notes |
|---|---|---|
| event_id | BIGINT NOT NULL | |
| customer_id | BIGINT | (some events pre-identity → id may repeat) |
| session_id | BIGINT | |
| event_type | VARCHAR(20) | PageView / QuoteStart / QuoteAbandon / PaymentRetry / AuthFailure / PageRefresh / ClaimFileStart / AppError |
| page | VARCHAR(24) | Home / Quote / Billing / Claims / Policy / Login / Dashboard |
| device | VARCHAR(8) | Web / iOS / Android |
| occurred_at | DATETIME | |

**`voc_feedback`** (~5,000) — Voice-of-Customer: surveys, NPS, app-store reviews.
`KEY (feedback_id) USING HASH`, `SHARD KEY (customer_id)`,
`SORT KEY (submitted_at)`.
| col | type | notes |
|---|---|---|
| feedback_id | BIGINT NOT NULL | |
| customer_id | BIGINT | |
| source | VARCHAR(12) | Survey / NPS / AppStore / Email / SocialMedia |
| nps | INT | 0..10 (NULL if not NPS) |
| sentiment | DECIMAL(5,3) | −1..1 |
| topic | VARCHAR(20) | Claims / Billing / Pricing / Service / Digital / Coverage |
| comment | VARCHAR(280) | short free-text |
| submitted_at | DATETIME | |

**`customer_signals`** (~4,000; one row per active customer) — the **at-risk
scoreboard**, the "predict & prevent" surface. rowstore,
`PRIMARY KEY (customer_id)`, `SHARD KEY (customer_id)`.
| col | type | notes |
|---|---|---|
| customer_id | BIGINT NOT NULL | |
| segment | VARCHAR(12) | |
| risk_signal | VARCHAR(20) | PaymentFriction / QuoteAbandon / AuthFriction / SentimentDrop / ClaimFriction / None |
| signal_strength | DECIMAL(5,3) | 0..1 |
| churn_risk_score | DECIMAL(6,4) | 0..1 (mirrors customers) |
| recommended_action | VARCHAR(28) | RetentionOutreach / PaymentAssist / AgentCallback / ExpediteClaim / WaiveFee / None |
| lifetime_value | DECIMAL(12,2) | |
| last_updated | DATETIME | |

### 3.4 View — `v_customer_360`

One row per customer fusing identity + policy portfolio + claims + payment
health + engagement + risk signal. Makes "who is at risk and why" a single
SELECT. LEFT JOIN customers → aggregates of policies / claims /
payment_transactions (last 30d) / interactions (last 30d) → customer_signals.
Expose at least: customer_id, segment, region, risk_tier, lifetime_value,
active_policies, open_claims, failed_payments_30d, avg_sentiment_30d,
churn_risk_score, risk_signal, recommended_action.

---

## 4. Time anchor & determinism

`TODAY = 2026-07-15 12:00:00` (matches repo currentDate). All "last N days /
hours" windows measured back from here. `SEED = 42`. Deterministic + re-runnable
(clear then regenerate). Full volume above; `seed_minimal.py` runs ~1/6 volume.

---

## 5. Planted "money-moment" cohorts + verification oracle

`generate_data.py :: print_summary()` prints each cohort's LIVE value after load
— that printout IS the acceptance oracle. Design targets in ( ). Cohorts must
survive the minimal seed too (they scale proportionally).

- **A — Claim approvals slowed yesterday (Pillar 1 hero).** Avg `approval_hours`
  for claims decided in the **last 24h** is materially higher than the trailing
  **7-day** average, concentrated in **one product line** (plant **Property**
  home claims: recent avg ~ **1.7×** the 7d avg, e.g. ~62h vs ~36h). Oracle
  prints: approval_hours today-vs-7d overall + by product_line, so the "why"
  resolves to Property.

- **B — Underwriting backlog.** One queue is backlogged: **Commercial-Property**
  has the highest share of `status IN (Received,InReview,PendingInfo)` still open
  AND the highest avg `age_hours` (target open-rate > 55%, avg age > 90h vs a
  book avg ~40h). Oracle prints open count + avg age by queue_name.

- **C — Payment system failure spike.** One payment system has an elevated
  failure rate: **CardGateway** fails at ~**22%** vs a book avg ~**8%**, and the
  dominant `failure_reason` there is **Gateway**/**Timeout**. Also plant that
  failed txns cluster in the **last 24–48h** (a live incident). Oracle prints
  failure rate by payment_system + top failure_reason for the worst system.

- **D — Fraud investigations increasing.** SIU case openings in the **last 30d**
  are up vs the prior 30d, concentrated in **Commercial Auto / Injury**
  (target last-30d ~ **1.6×** prior-30d; ~140 recent). Oracle prints opened
  cases last-30d vs prior-30d + by product_line, plus confirmed $ suspected.

- **E — At-risk customers (Pillar 2 hero — predict & prevent).** A crisp cohort
  of high-value customers carrying an active `risk_signal` with a
  `recommended_action`. Plant so that **PaymentFriction** is the top signal by
  count, and **high-LTV (top quartile) at-risk customers** number a clean,
  quotable figure (~**180–260**). The single largest recoverable-value signal is
  **PaymentFriction + PaymentAssist**. Oracle prints: count + total LTV of
  at-risk customers by risk_signal, and top recommended_action by at-risk LTV.

- **F — Sentiment / VoC decline (Pillar 2 supporting).** Avg VoC `sentiment`
  and NPS for the **Claims** topic is the lowest of all topics and has dropped
  in the last 30d — the CIP ties poor claims sentiment to elevated churn_risk.
  Oracle prints avg sentiment + avg NPS by topic (Claims lowest).

Correlated planting (make the story causal, not just coincidental):
- Customers with recent `AuthFailure`/`PaymentRetry` web_events and failed
  `payment_transactions` should carry `risk_signal='PaymentFriction'` +
  `recommended_action='PaymentAssist'` and an elevated `churn_risk_score`.
- Customers with `QuoteAbandon` web_events map to `risk_signal='QuoteAbandon'`.
- Customers with low claims sentiment + an open/slow claim map to
  `risk_signal='ClaimFriction'` + `recommended_action='ExpediteClaim'`.

---

## 6. Backend contract (FastAPI)

- **DB name** `meridian_intel`, pinned in `singlestore.py` (`DB_NAME`), exactly
  like enova. `cursor()` ctx mgr, `ping()`, `table_counts()` over the 9 tables.
- `main.py`: title "Meridian Intelligence Platform (SingleStore Aura Analyst)".
  `/health` returns row_counts + analyst_configured. Guarded router imports.
- `routers/analyst.py`: **KEEP VERBATIM** from enova (proxy is domain-agnostic).
- `routers/dashboard.py`: **two endpoints.**
  - `GET /api/overview/kpis` → the Pillar-1 KPI row (see §7 KPI contract).
  - `GET /api/cip/at_risk` → the Pillar-2 Customer-Intelligence summary:
    `{ at_risk_customers, at_risk_ltv, top_signal, top_action, by_signal:[{risk_signal,customers,ltv}] }`
    computed from `customer_signals` (risk_signal != 'None'). Wrap in
    try/except → HTTP 503 on db error like enova.
- Backend runs on **port 8050** (8000/8010/8020/8030/8040 are squatted by other
  demos per memory). Set `NEXT_PUBLIC_BACKEND_URL` default accordingly.

---

## 7. KPI contract (frontend `lib/api.ts` must match backend exactly)

`GET /api/overview/kpis` → JSON, all keys present:
```
{
  "open_claims": int,               // claims status NOT IN (Paid,Closed,Denied)
  "avg_approval_hours_24h": float,  // avg approval_hours, claims decided last 24h
  "payment_failure_rate_24h": float,// % failed payment_transactions last 24h
  "active_policies": int            // policies status='Active'
}
```
`GET /api/cip/at_risk` → JSON (see §6). Frontend `fetchAtRisk()` mirrors it.

KPI row cards (Pillar 1): **Open claims**, **Avg approval time · 24h** (hrs),
**Payment failure rate · 24h** (%), **Active policies**. Counts may use a
display-only ×S multiplier (S=100 to imply millions-of-policyholders scale) —
**counts only**; rates/hours stay exact. Document S in the component.

---

## 8. Frontend contract

- Single-page hero (`app/page.tsx`), App Router, TS, Tailwind, recharts.
  Layout order:
  1. Co-branded hero (`Meridian × SingleStore`, tagline, two-pillar subhead).
  2. `DataMovementStrip` (ingest CDC/Kafka/S3 → one engine → egress; any cloud).
  3. KPI row (Pillar 1 operational headline — 4 cards from `/api/overview/kpis`).
  4. **`CustomerIntelStrip`** (NEW, Pillar 2) — at-risk scoreboard from
     `/api/cip/at_risk`: total at-risk customers, at-risk LTV, top signal, top
     recommended action, and a small by-signal breakdown. This is the
     "predict & prevent" evidence. Amber/red accents for at-risk.
  5. `GovernanceReadiness` (RLS, audit/lineage, regulatory readiness, residency
     — reframed for **insurance** compliance: NAIC/state DOI, PII/PCI, SOC 2).
  6. **Ask Aura Analyst** card = the dominant element (`AnalystChat`).
- `AnalystChat.tsx`: reuse enova's streaming logic **verbatim**; only swap the
  `SUGGESTIONS` array + empty-state copy to the Meridian money moments (§9) and
  recolor bubble accents to `meridian.*`/`s2.*`.
- `layout.tsx` metadata + `Header`/`Footer`/`Logo` rebranded to Meridian.
- Keep all `components/ui/*` verbatim. Keep `analystStream.ts` verbatim.

---

## 9. Aura Analyst suggestion prompts (empty-state chips)

Pillar 1 (operational, live):
1. "Why did claim approvals slow down in the last 24 hours? Break down average
   approval time by product line and show a chart."
2. "Which underwriting queues are most backlogged right now — by open count and
   average age in hours?"
3. "Which payment systems have elevated failure rates over the last 24 hours,
   and what's the top failure reason? Show a bar chart."
4. "Where are fraud investigations increasing — compare cases opened in the last
   30 days vs the prior 30 days by product line."

Pillar 2 (customer intelligence, predict & prevent):
5. "How many high-value customers are currently at risk, broken down by risk
   signal? Show a chart."
6. "What's the single best next-best-action to take right now by total customer
   lifetime value at risk?"
7. "Which feedback topic has the lowest customer sentiment, and how does that
   relate to churn risk?"
8. "Show me customers with repeated payment retries and auth failures in the
   last 24 hours who are flagged for retention outreach."

---

## 10. Non-negotiables (learned the hard way)

- **Do NOT re-home** this demo onto another demo's live workspace to dodge the
  cluster cap. If provisioning is blocked (403 firewall / on-demand cap), STOP
  and surface it to the user. (`no-shared-workspace-rehoming`.)
- Columnstore facts: `KEY (...) USING HASH`, never a non-shard PRIMARY KEY.
- The Aura proxy (`routers/analyst.py`) and `analystStream.ts` are
  domain-agnostic — keep them byte-for-byte from enova.
- Dollars honest, rates exact; only integer counts may carry a display ×S.
