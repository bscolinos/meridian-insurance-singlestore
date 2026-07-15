-- Meridian × SingleStore — Aura Analyst demo schema DDL (idempotent, re-runnable)
-- SingleStore (MySQL-wire, reports 5.7.32). No FK constraints (not enforced).
-- Data-gen agent supplies explicit ids, so no AUTO_INCREMENT.
--
-- The demo unifies Meridian Mutual Insurance's operational + customer-intelligence
-- lifecycle — today split across transactional DBs, streaming platforms, data
-- lakes, and warehouses — into one live transactional+analytical layer that Aura
-- Analyst can query in plain English:
--   * Identity spine (dimensions):              customers, policies
--   * Real-time operations (Pillar 1):          claims, underwriting_queue,
--                                                payment_transactions,
--                                                fraud_investigations
--   * Customer intelligence (Pillar 2):         interactions, web_events,
--                                                voc_feedback, customer_signals
-- The customer is the join spine: every customer-scoped high-volume fact carries
-- SHARD KEY (customer_id) so the identity -> policy -> claim -> payment ->
-- interaction join is local to each partition. Rowstore dims (customers/policies/
-- customer_signals) allow a PRIMARY KEY distinct from (or equal to) the shard key.
--
-- Columnstore PK gotcha (learned the hard way): a columnstore table can't have a
-- PRIMARY KEY that isn't the shard key. Columnstore facts therefore use
-- KEY (id) USING HASH (a secondary hash index), NOT PRIMARY KEY, plus a SORT KEY
-- on the time column for fast recent-window scans.

CREATE DATABASE IF NOT EXISTS meridian_intel;
USE meridian_intel;

-- ===========================================================================
-- Dimensions (rowstore)
-- ===========================================================================

-- customers: the policyholder identity spine. Modest dimension -> rowstore.
-- churn_risk_score (0..1) mirrors customer_signals for the same customer.
-- Sharded by customer_id so the whole lifecycle co-locates per partition.
DROP TABLE IF EXISTS customers;
CREATE TABLE customers (
  customer_id         BIGINT NOT NULL,
  segment             VARCHAR(12),        -- Personal / Commercial / Specialty
  tenure_years        INT,                -- years as a customer
  home_state          CHAR(2),            -- US 2-letter
  region              VARCHAR(12),        -- West / Midwest / South / Northeast
  lifetime_value      DECIMAL(12,2),      -- total premiums paid to date
  risk_tier           VARCHAR(10),        -- Preferred / Standard / Elevated
  acquisition_channel VARCHAR(16),        -- Agent / Direct / Aggregator / Partner / Renewal
  signup_date         DATE,
  churn_risk_score    DECIMAL(6,4),       -- 0..1, higher = more likely to lapse
  is_active           BOOLEAN,
  PRIMARY KEY (customer_id),
  SHARD KEY (customer_id)
);

-- policies: issued policies. Rowstore; PRIMARY KEY on policy_id but SHARD KEY on
-- customer_id (rowstore allows a PK distinct from the shard key) so policies
-- co-locate with their customer + downstream facts.
DROP TABLE IF EXISTS policies;
CREATE TABLE policies (
  policy_id      BIGINT NOT NULL,
  customer_id    BIGINT,
  segment        VARCHAR(12),        -- denormalized from customer
  product_line   VARCHAR(20),        -- Auto / Home / Renters / BOP / CommercialAuto / WorkersComp / Umbrella / Cyber / Marine
  status         VARCHAR(14),        -- Active / Lapsed / Cancelled / PendingRenewal
  annual_premium DECIMAL(12,2),
  coverage_limit DECIMAL(14,2),
  deductible     DECIMAL(10,2),
  effective_date DATE,
  renewal_date   DATE,
  state          CHAR(2),
  -- A rowstore PRIMARY KEY must contain all shard-key columns, so the PK is
  -- composite (policy_id, customer_id). policy_id is still globally unique in
  -- the generated data; this just satisfies SingleStore's unique-key rule.
  PRIMARY KEY (policy_id, customer_id),
  SHARD KEY (customer_id)
);

-- ===========================================================================
-- Operational facts (columnstore) — Pillar 1: Real-Time Operational Intelligence
-- ===========================================================================

-- claims: the claims lifecycle fact. High-volume -> columnstore.
-- approval_hours = hours(decision_at - fnol_at), NULL until decided.
-- approved_amount <= claim_amount (0 if denied). Sharded by customer_id;
-- SORT KEY (fnol_at) keeps the dense recent-submission window fast to scan.
DROP TABLE IF EXISTS claims;
CREATE TABLE claims (
  claim_id            BIGINT NOT NULL,
  policy_id           BIGINT,
  customer_id         BIGINT,
  segment             VARCHAR(12),
  product_line        VARCHAR(20),
  claim_type          VARCHAR(20),    -- Collision / Property / Liability / Theft / Injury / BusinessInterruption / Cyber
  status              VARCHAR(14),    -- Submitted / InReview / Approved / Denied / Paid / Closed
  fnol_at             DATETIME,       -- first notice of loss (submission time)
  decision_at         DATETIME,       -- NULL until decided
  approval_hours      DECIMAL(8,2),   -- NULL until decided; hours(decision_at - fnol_at)
  claim_amount        DECIMAL(12,2),  -- claimed
  approved_amount     DECIMAL(12,2),  -- paid/approved (<= claim_amount; 0 if denied)
  adjuster_id         BIGINT,
  fraud_investigation BOOLEAN,        -- referred to SIU
  KEY (claim_id) USING HASH,
  SHARD KEY (customer_id),
  SORT KEY (fnol_at)
);

-- underwriting_queue: new-business & renewal submissions in the funnel. Drives
-- the "backlogged queues" money moment. Columnstore; age_hours measured to
-- decided_at (or NOW if still open). Sharded by customer_id, SORT KEY on submit.
DROP TABLE IF EXISTS underwriting_queue;
CREATE TABLE underwriting_queue (
  submission_id       BIGINT NOT NULL,
  customer_id         BIGINT,
  segment             VARCHAR(12),
  product_line        VARCHAR(20),
  queue_name          VARCHAR(24),    -- Personal-Auto / Commercial-Property / Specialty-Cyber / Workers-Comp / Home / Umbrella
  status              VARCHAR(14),    -- Received / InReview / PendingInfo / Approved / Declined
  priority            VARCHAR(8),     -- Low / Medium / High
  submitted_at        DATETIME,
  decided_at          DATETIME,       -- NULL if still open
  age_hours           DECIMAL(8,2),   -- hours in queue (to decided_at or NOW)
  assigned_underwriter BIGINT,
  KEY (submission_id) USING HASH,
  SHARD KEY (customer_id),
  SORT KEY (submitted_at)
);

-- payment_transactions: billing/payment attempts across payment systems. Drives
-- the "elevated failure rates" money moment. Highest-volume operational fact ->
-- columnstore. failure_reason NULL if success; attempt_no is the retry index.
-- Sharded by customer_id, SORT KEY (created_at) for the live-incident window.
DROP TABLE IF EXISTS payment_transactions;
CREATE TABLE payment_transactions (
  txn_id         BIGINT NOT NULL,
  customer_id    BIGINT,
  policy_id      BIGINT,
  payment_system VARCHAR(16),        -- ACH / CardGateway / Lockbox / Wallet / AgentPortal
  amount         DECIMAL(12,2),
  status         VARCHAR(10),        -- Success / Failed / Pending
  failure_reason VARCHAR(20),        -- NULL if success; Insufficient / Gateway / Expired / Timeout / Fraud
  attempt_no     INT,                -- 1..N retries for the same bill
  created_at     DATETIME,
  KEY (txn_id) USING HASH,
  SHARD KEY (customer_id),
  SORT KEY (created_at)
);

-- fraud_investigations: SIU cases opened on suspicious claims. Columnstore;
-- SORT KEY (opened_at) for the last-30d-vs-prior-30d trend. Sharded by customer.
DROP TABLE IF EXISTS fraud_investigations;
CREATE TABLE fraud_investigations (
  case_id          BIGINT NOT NULL,
  claim_id         BIGINT,
  customer_id      BIGINT,
  segment          VARCHAR(12),
  product_line     VARCHAR(20),
  fraud_type       VARCHAR(16),       -- Staged / Exaggerated / Identity / Premium / Provider
  status           VARCHAR(14),       -- Open / Investigating / Confirmed / Cleared
  suspected_amount DECIMAL(12,2),
  opened_at        DATETIME,
  KEY (case_id) USING HASH,
  SHARD KEY (customer_id),
  SORT KEY (opened_at)
);

-- ===========================================================================
-- Customer-Intelligence signals (columnstore) — Pillar 2: predict & prevent
-- ===========================================================================

-- interactions: omnichannel touch log — calls, chats, portal & mobile sessions.
-- sentiment is -1..1 (NULL for pure page views). Columnstore, SORT KEY on time.
DROP TABLE IF EXISTS interactions;
CREATE TABLE interactions (
  interaction_id BIGINT NOT NULL,
  customer_id    BIGINT,
  channel        VARCHAR(12),        -- CallCenter / Chat / Web / Mobile / Email
  intent         VARCHAR(20),        -- Billing / Claim / Quote / Coverage / Complaint / TechSupport
  sentiment      DECIMAL(5,3),       -- -1..1 (NULL for pure page views)
  duration_sec   INT,
  resolved       BOOLEAN,
  escalated      BOOLEAN,            -- handed to a supervisor / retention
  occurred_at    DATETIME,
  KEY (interaction_id) USING HASH,
  SHARD KEY (customer_id),
  SORT KEY (occurred_at)
);

-- web_events: digital clickstream / page visits / app telemetry. Drives
-- "abandoned quotes / excessive refreshes / repeated auth failures". Highest
-- volume -> columnstore. customer_id may repeat (some events pre-identity).
DROP TABLE IF EXISTS web_events;
CREATE TABLE web_events (
  event_id    BIGINT NOT NULL,
  customer_id BIGINT,               -- some events pre-identity -> id may repeat
  session_id  BIGINT,
  event_type  VARCHAR(20),          -- PageView / QuoteStart / QuoteAbandon / PaymentRetry / AuthFailure / PageRefresh / ClaimFileStart / AppError
  page        VARCHAR(24),          -- Home / Quote / Billing / Claims / Policy / Login / Dashboard
  device      VARCHAR(8),           -- Web / iOS / Android
  occurred_at DATETIME,
  KEY (event_id) USING HASH,
  SHARD KEY (customer_id),
  SORT KEY (occurred_at)
);

-- voc_feedback: Voice-of-Customer — surveys, NPS, app-store reviews. nps is
-- 0..10 (NULL if not an NPS response). sentiment -1..1. Columnstore, SORT KEY
-- (submitted_at) for the last-30d sentiment trend.
DROP TABLE IF EXISTS voc_feedback;
CREATE TABLE voc_feedback (
  feedback_id  BIGINT NOT NULL,
  customer_id  BIGINT,
  source       VARCHAR(12),         -- Survey / NPS / AppStore / Email / SocialMedia
  nps          INT,                 -- 0..10 (NULL if not NPS)
  sentiment    DECIMAL(5,3),        -- -1..1
  topic        VARCHAR(20),         -- Claims / Billing / Pricing / Service / Digital / Coverage
  comment      VARCHAR(280),        -- short free-text
  submitted_at DATETIME,
  KEY (feedback_id) USING HASH,
  SHARD KEY (customer_id),
  SORT KEY (submitted_at)
);

-- customer_signals: the at-risk scoreboard — one row per active customer, the
-- "predict & prevent" surface. Rowstore; PRIMARY KEY (customer_id) == SHARD KEY.
-- churn_risk_score mirrors the customers table for the same customer.
DROP TABLE IF EXISTS customer_signals;
CREATE TABLE customer_signals (
  customer_id        BIGINT NOT NULL,
  segment            VARCHAR(12),
  risk_signal        VARCHAR(20),    -- PaymentFriction / QuoteAbandon / AuthFriction / SentimentDrop / ClaimFriction / None
  signal_strength    DECIMAL(5,3),   -- 0..1
  churn_risk_score   DECIMAL(6,4),   -- 0..1 (mirrors customers)
  recommended_action VARCHAR(28),    -- RetentionOutreach / PaymentAssist / AgentCallback / ExpediteClaim / WaiveFee / None
  lifetime_value     DECIMAL(12,2),
  last_updated       DATETIME,
  PRIMARY KEY (customer_id),
  SHARD KEY (customer_id)
);

-- ===========================================================================
-- v_customer_360 — the unified customer view. One row per customer fusing
-- identity + policy portfolio + claims + payment health (last 30d) + engagement
-- (last 30d) + risk signal. Makes "who is at risk and why" a single SELECT while
-- keeping the join live across the operational + intelligence facts.
-- ===========================================================================
DROP VIEW IF EXISTS v_customer_360;
CREATE VIEW v_customer_360 AS
SELECT
  c.customer_id,
  c.segment,
  c.region,
  c.risk_tier,
  c.lifetime_value,
  c.churn_risk_score,
  -- policy portfolio
  COALESCE(p.active_policies, 0)      AS active_policies,
  -- claims health
  COALESCE(cl.open_claims, 0)         AS open_claims,
  -- payment health (last 30 days)
  COALESCE(pt.failed_payments_30d, 0) AS failed_payments_30d,
  -- engagement (last 30 days)
  ix.avg_sentiment_30d,
  -- customer-intelligence signal
  COALESCE(s.risk_signal, 'None')     AS risk_signal,
  COALESCE(s.recommended_action, 'None') AS recommended_action
FROM customers c
LEFT JOIN (
  SELECT customer_id,
         SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) AS active_policies
  FROM policies
  GROUP BY customer_id
) p ON p.customer_id = c.customer_id
LEFT JOIN (
  SELECT customer_id,
         SUM(CASE WHEN status NOT IN ('Paid','Closed','Denied') THEN 1 ELSE 0 END) AS open_claims
  FROM claims
  GROUP BY customer_id
) cl ON cl.customer_id = c.customer_id
LEFT JOIN (
  SELECT customer_id,
         SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END) AS failed_payments_30d
  FROM payment_transactions
  WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
  GROUP BY customer_id
) pt ON pt.customer_id = c.customer_id
LEFT JOIN (
  SELECT customer_id, AVG(sentiment) AS avg_sentiment_30d
  FROM interactions
  WHERE occurred_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    AND sentiment IS NOT NULL
  GROUP BY customer_id
) ix ON ix.customer_id = c.customer_id
LEFT JOIN customer_signals s ON s.customer_id = c.customer_id;
