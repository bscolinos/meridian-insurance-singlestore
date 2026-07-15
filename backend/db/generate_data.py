#!/usr/bin/env python3
"""Synthetic data generator for the `meridian_intel` SingleStore demo.

Deterministic (seed=42), re-runnable: clears the data tables then regenerates
everything. Unifies Meridian Mutual Insurance's operational + customer-
intelligence lifecycle — identity (customers/policies), real-time operations
(claims/underwriting_queue/payment_transactions/fraud_investigations), and
customer-intelligence signals (interactions/web_events/voc_feedback/
customer_signals) — and plants "money-moment" cohorts so specific natural-
language questions return crisp, reproducible answers. `print_summary()` reports
each cohort's live value — that is the verification oracle.

Usage:
    source /Users/billscolinos/Documents/code_factory/.venv/bin/activate
    python backend/db/generate_data.py            # clear + load (default)
    python backend/db/generate_data.py --no-clear # append (not recommended)

Planted cohorts (see print_summary for live values; design targets in ()):
    A. Claim approvals slowed in last 24h vs 7d, concentrated in Property (~1.7x)
    B. Underwriting backlog: Commercial-Property most open + oldest (avg age)
    C. Payment failure spike: CardGateway ~22% vs ~8% book, Gateway/Timeout
    D. Fraud investigations up last-30d vs prior-30d (Commercial Auto / Injury)
    E. At-risk customers: PaymentFriction top signal; PaymentAssist top action $
    F. VoC sentiment: Claims topic lowest sentiment + NPS
"""
import os
import sys
import math
import random
import datetime as dt
from pathlib import Path

import singlestoredb as s2

SEED = 42
rng = random.Random(SEED)

# "Today" for the demo — matches the repo's currentDate. All "last N days/hours"
# windows are measured back from here so planted cohorts land in-window.
TODAY = dt.datetime(2026, 7, 15, 12, 0, 0)
DB_NAME = "meridian_intel"

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------
SEGMENTS = ["Personal", "Commercial", "Specialty"]
SEGMENT_WEIGHTS = [0.62, 0.28, 0.10]

# product lines by segment (a policy/claim/submission inherits a line valid for
# the customer's segment).
SEGMENT_LINES = {
    "Personal":   ["Auto", "Home", "Renters"],
    "Commercial": ["BOP", "CommercialAuto", "WorkersComp"],
    "Specialty":  ["Umbrella", "Cyber", "Marine"],
}

REGIONS = ["West", "Midwest", "South", "Northeast"]
REGION_WEIGHTS = [0.30, 0.24, 0.30, 0.16]
REGION_STATES = {
    "West":      ["CA", "WA", "OR", "AZ", "NV", "CO", "UT", "NM", "ID"],
    "Midwest":   ["IL", "OH", "MI", "IN", "WI", "MN", "MO", "KS", "IA"],
    "South":     ["TX", "FL", "GA", "NC", "VA", "TN", "SC", "AL", "LA"],
    "Northeast": ["NY", "NJ", "PA", "MA", "CT", "MD", "RI", "NH", "ME"],
}

RISK_TIERS = ["Preferred", "Standard", "Elevated"]
RISK_TIER_WEIGHTS = [0.34, 0.46, 0.20]

ACQ_CHANNELS = ["Agent", "Direct", "Aggregator", "Partner", "Renewal"]
ACQ_CHANNEL_WEIGHTS = [0.34, 0.24, 0.16, 0.12, 0.14]

POLICY_STATUSES = ["Active", "Lapsed", "Cancelled", "PendingRenewal"]
POLICY_STATUS_WEIGHTS = [0.80, 0.07, 0.05, 0.08]

# claim_type valid per product line (loose mapping; keeps types plausible).
LINE_CLAIM_TYPES = {
    "Auto": ["Collision", "Theft", "Liability"],
    "Home": ["Property", "Liability", "Theft"],
    "Renters": ["Property", "Theft"],
    "BOP": ["Property", "Liability", "BusinessInterruption"],
    "CommercialAuto": ["Collision", "Liability", "Injury"],
    "WorkersComp": ["Injury", "Liability"],
    "Umbrella": ["Liability", "Injury"],
    "Cyber": ["Cyber", "BusinessInterruption"],
    "Marine": ["Property", "Liability"],
}
CLAIM_STATUSES = ["Submitted", "InReview", "Approved", "Denied", "Paid", "Closed"]

# underwriting queues + the product lines that feed them.
QUEUES = ["Personal-Auto", "Commercial-Property", "Specialty-Cyber",
          "Workers-Comp", "Home", "Umbrella"]
LINE_QUEUE = {
    "Auto": "Personal-Auto", "Home": "Home", "Renters": "Home",
    "BOP": "Commercial-Property", "CommercialAuto": "Commercial-Property",
    "WorkersComp": "Workers-Comp", "Umbrella": "Umbrella",
    "Cyber": "Specialty-Cyber", "Marine": "Commercial-Property",
}
UW_OPEN_STATUSES = ["Received", "InReview", "PendingInfo"]
UW_CLOSED_STATUSES = ["Approved", "Declined"]
PRIORITIES = ["Low", "Medium", "High"]
PRIORITY_WEIGHTS = [0.34, 0.44, 0.22]

PAYMENT_SYSTEMS = ["ACH", "CardGateway", "Lockbox", "Wallet", "AgentPortal"]
PAYMENT_SYSTEM_WEIGHTS = [0.30, 0.32, 0.12, 0.16, 0.10]
FAILURE_REASONS = ["Insufficient", "Gateway", "Expired", "Timeout", "Fraud"]

FRAUD_TYPES = ["Staged", "Exaggerated", "Identity", "Premium", "Provider"]
FRAUD_TYPE_WEIGHTS = [0.24, 0.28, 0.18, 0.14, 0.16]
FRAUD_STATUSES = ["Open", "Investigating", "Confirmed", "Cleared"]
FRAUD_STATUS_WEIGHTS = [0.24, 0.30, 0.26, 0.20]

CHANNELS = ["CallCenter", "Chat", "Web", "Mobile", "Email"]
CHANNEL_WEIGHTS = [0.24, 0.18, 0.26, 0.22, 0.10]
INTENTS = ["Billing", "Claim", "Quote", "Coverage", "Complaint", "TechSupport"]
INTENT_WEIGHTS = [0.26, 0.22, 0.16, 0.14, 0.12, 0.10]

WEB_EVENT_TYPES = ["PageView", "QuoteStart", "QuoteAbandon", "PaymentRetry",
                   "AuthFailure", "PageRefresh", "ClaimFileStart", "AppError"]
WEB_EVENT_WEIGHTS = [0.42, 0.10, 0.07, 0.09, 0.08, 0.12, 0.07, 0.05]
PAGES = ["Home", "Quote", "Billing", "Claims", "Policy", "Login", "Dashboard"]
DEVICES = ["Web", "iOS", "Android"]
DEVICE_WEIGHTS = [0.46, 0.30, 0.24]

VOC_SOURCES = ["Survey", "NPS", "AppStore", "Email", "SocialMedia"]
VOC_SOURCE_WEIGHTS = [0.30, 0.26, 0.16, 0.16, 0.12]
VOC_TOPICS = ["Claims", "Billing", "Pricing", "Service", "Digital", "Coverage"]
VOC_TOPIC_WEIGHTS = [0.24, 0.20, 0.16, 0.16, 0.14, 0.10]

RISK_SIGNALS = ["PaymentFriction", "QuoteAbandon", "AuthFriction",
                "SentimentDrop", "ClaimFriction", "None"]
RECOMMENDED_ACTIONS = ["RetentionOutreach", "PaymentAssist", "AgentCallback",
                       "ExpediteClaim", "WaiveFee", "None"]
# maps an active risk signal -> its canonical next-best action.
SIGNAL_ACTION = {
    "PaymentFriction": "PaymentAssist",
    "QuoteAbandon": "AgentCallback",
    "AuthFriction": "AgentCallback",
    "SentimentDrop": "RetentionOutreach",
    "ClaimFriction": "ExpediteClaim",
}

# --- probability levers behind the oracle ---
COHORT_A_LINE = "Home"               # slow recent product line (Property claims)
COHORT_B_QUEUE = "Commercial-Property"
COHORT_C_SYSTEM = "CardGateway"
FAIL_PROB = {"ACH": 0.06, "CardGateway": 0.15, "Lockbox": 0.03,
             "Wallet": 0.09, "AgentPortal": 0.05}
COHORT_D_LINES = ["CommercialAuto"]  # + Injury claim types


def rand_dt(start: dt.datetime, end: dt.datetime) -> dt.datetime:
    span = int((end - start).total_seconds())
    if span <= 0:
        return start
    return start + dt.timedelta(seconds=rng.randint(0, span))


def connect():
    return s2.connect(
        host=os.environ["SINGLESTORE_HOST"],
        port=int(os.environ.get("SINGLESTORE_PORT", 3306)),
        user=os.environ["SINGLESTORE_USER"],
        password=os.environ["SINGLESTORE_PASSWORD"],
        database=DB_NAME,
    )


def load_env():
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def _recency_days(max_days=365):
    """Recency-weighted age in days (bias to recent)."""
    u = rng.random() ** 1.6
    return int(u * max_days)


# ---------------------------------------------------------------------------
# Dimensions: customers, policies
# ---------------------------------------------------------------------------
def gen_customers(n=4000):
    """Policyholder identity spine. segment drives product lines; churn_risk_score
    is filled later by gen_customer_signals (correlated with friction signals)."""
    customers = []
    for cid in range(1, n + 1):
        segment = rng.choices(SEGMENTS, weights=SEGMENT_WEIGHTS)[0]
        region = rng.choices(REGIONS, weights=REGION_WEIGHTS)[0]
        state = rng.choice(REGION_STATES[region])
        tier = rng.choices(RISK_TIERS, weights=RISK_TIER_WEIGHTS)[0]
        tenure = rng.randint(0, 22)
        seg_mult = {"Personal": 1.0, "Commercial": 3.2, "Specialty": 2.4}[segment]
        ltv = round(math.exp(rng.gauss(8.6, 0.5)) * seg_mult * (0.5 + tenure / 12.0), 2)
        customers.append({
            "customer_id": cid, "segment": segment, "tenure_years": tenure,
            "home_state": state, "region": region,
            "lifetime_value": min(ltv, 2_000_000),
            "risk_tier": tier,
            "acquisition_channel": rng.choices(ACQ_CHANNELS,
                                               weights=ACQ_CHANNEL_WEIGHTS)[0],
            "signup_date": (TODAY - dt.timedelta(days=365 * tenure
                                                 + rng.randint(0, 364))).date(),
            "churn_risk_score": 0.0,   # filled in gen_customer_signals
            "is_active": rng.random() > 0.08,
        })
    return customers


def gen_policies(customers, target=7500):
    """Issued policies — 1-3 per customer, lines valid for the segment."""
    policies = []
    pid = 500_000
    for c in customers:
        k = 1 + int(rng.random() ** 1.5 * 3)
        lines = SEGMENT_LINES[c["segment"]]
        for _ in range(k):
            if len(policies) >= target:
                break
            line = rng.choice(lines)
            status = rng.choices(POLICY_STATUSES, weights=POLICY_STATUS_WEIGHTS)[0]
            premium = round(math.exp(rng.gauss(7.4, 0.55))
                            * (2.6 if c["segment"] != "Personal" else 1.0), 2)
            limit = round(premium * rng.uniform(20, 120), 2)
            eff = (TODAY - dt.timedelta(days=rng.randint(30, 3 * 365))).date()
            renewal = (dt.datetime.combine(eff, dt.time())
                       + dt.timedelta(days=365)).date()
            policies.append({
                "policy_id": pid, "customer_id": c["customer_id"],
                "segment": c["segment"], "product_line": line, "status": status,
                "annual_premium": min(premium, 500_000),
                "coverage_limit": min(limit, 50_000_000),
                "deductible": round(rng.choice([250, 500, 1000, 2500, 5000, 10000]) * 1.0, 2),
                "effective_date": eff, "renewal_date": renewal,
                "state": c["home_state"],
            })
            pid += 1
    return policies


# ---------------------------------------------------------------------------
# Operational facts
# ---------------------------------------------------------------------------
def gen_claims(customers, policies, target=12000):
    """Claims lifecycle. Cohort A: claims DECIDED in the last 24h whose
    claim_type is Property get ~1.7x the normal approval latency, so 'why did
    approvals slow down yesterday' resolves to Property."""
    by_cust = {}
    for p in policies:
        by_cust.setdefault(p["customer_id"], []).append(p)
    claim_customers = [c for c in customers if c["customer_id"] in by_cust]
    claims = []
    clid = 700_000
    while len(claims) < target and claim_customers:
        c = rng.choice(claim_customers)
        pol = rng.choice(by_cust[c["customer_id"]])
        line = pol["product_line"]
        ctype = rng.choice(LINE_CLAIM_TYPES.get(line, ["Liability"]))
        amount = min(round(math.exp(rng.gauss(8.2, 0.7))
                     * (2.5 if c["segment"] != "Personal" else 1.0), 2), 400_000)
        decision_at = approval_hours = approved_amount = None

        # ~9% of claims are "decided in the last 24h" — the live window the
        # 'why did approvals slow down yesterday' question scans. We build these
        # BACKWARD (decision first, then fnol = decision - latency) so a slow
        # claim can carry a large approval_hours while still being decided today.
        recent_decided = rng.random() < 0.09
        if recent_decided:
            decision_at = TODAY - dt.timedelta(hours=rng.randint(0, 23),
                                               minutes=rng.randint(0, 59))
            # Cohort A: recent Home (Property) decisions are slow (~1.9x the
            # ~36h norm), so the by-product-line answer for 'why did approvals
            # slow down yesterday' points unmistakably at Home.
            if line == COHORT_A_LINE:
                lat = max(2.0, rng.gauss(72.0, 9.0))
            else:
                lat = max(1.0, rng.gauss(33.0, 10.0))
            fnol = decision_at - dt.timedelta(hours=lat)
            approval_hours = round(lat, 2)
            if rng.random() < 0.16:
                status, approved_amount = "Denied", 0.0
            else:
                status = rng.choice(["Approved", "Paid", "Closed"])
                approved_amount = round(amount * rng.uniform(0.55, 1.0), 2)
        else:
            fnol = TODAY - dt.timedelta(days=1 + _recency_days(300),
                                        hours=rng.randint(0, 23),
                                        minutes=rng.randint(0, 59))
            age_days = (TODAY - fnol).days
            still_open = age_days < 3 and rng.random() < 0.5
            if still_open:
                status = rng.choice(["Submitted", "InReview"])
            else:
                lat = max(1.0, rng.gauss(36.0, 14.0))
                decision_at = min(fnol + dt.timedelta(hours=lat), TODAY)
                approval_hours = round((decision_at - fnol).total_seconds() / 3600.0, 2)
                if rng.random() < 0.16:
                    status, approved_amount = "Denied", 0.0
                else:
                    status = rng.choice(["Approved", "Paid", "Closed"])
                    approved_amount = round(amount * rng.uniform(0.55, 1.0), 2)
        claims.append({
            "claim_id": clid, "policy_id": pol["policy_id"],
            "customer_id": c["customer_id"], "segment": c["segment"],
            "product_line": line, "claim_type": ctype, "status": status,
            "fnol_at": fnol, "decision_at": decision_at,
            "approval_hours": approval_hours, "claim_amount": amount,
            "approved_amount": approved_amount,
            "adjuster_id": 9000 + rng.randint(0, 60),
            "fraud_investigation": rng.random() < 0.055,
            "_ctype": ctype,
        })
        clid += 1
    return claims


def gen_underwriting(customers, target=3500):
    """Underwriting funnel. Cohort B: Commercial-Property is backlogged — more
    submissions still open AND much older than other queues."""
    subs = []
    sid = 800_000
    while len(subs) < target:
        c = rng.choice(customers)
        line = rng.choice(SEGMENT_LINES[c["segment"]])
        queue = LINE_QUEUE[line]
        submitted = TODAY - dt.timedelta(hours=rng.randint(1, 24 * 30),
                                         minutes=rng.randint(0, 59))
        backlogged = queue == COHORT_B_QUEUE
        if backlogged:
            open_now = rng.random() < 0.62
            age = rng.uniform(80, 260) if open_now else rng.uniform(40, 120)
        else:
            open_now = rng.random() < 0.28
            age = rng.uniform(20, 90) if open_now else rng.uniform(2, 48)
        max_age = (TODAY - submitted).total_seconds() / 3600.0
        if open_now:
            status, decided_at = rng.choice(UW_OPEN_STATUSES), None
            age_hours = round(min(age, max_age), 2)
        else:
            status = rng.choices(UW_CLOSED_STATUSES, weights=[0.72, 0.28])[0]
            decided_at = min(submitted + dt.timedelta(hours=age), TODAY)
            age_hours = round((decided_at - submitted).total_seconds() / 3600.0, 2)
        subs.append({
            "submission_id": sid, "customer_id": c["customer_id"],
            "segment": c["segment"], "product_line": line, "queue_name": queue,
            "status": status,
            "priority": rng.choices(PRIORITIES, weights=PRIORITY_WEIGHTS)[0],
            "submitted_at": submitted, "decided_at": decided_at,
            "age_hours": age_hours,
            "assigned_underwriter": 7000 + rng.randint(0, 40),
        })
        sid += 1
    return subs


def gen_payments(customers, policies, payment_friction, target=40000):
    """Payment attempts. Cohort C: CardGateway fails ~22% vs ~8% book; failed
    CardGateway txns concentrate in the last 48h (Gateway/Timeout). The planted
    `payment_friction` customers preferentially transact on the failing gateway
    and fail hard/recently — corroborating their PaymentFriction signal — while
    everyone else follows the honest per-system base failure rates."""
    pol_by_cust = {}
    for p in policies:
        pol_by_cust.setdefault(p["customer_id"], []).append(p)
    payers = [c for c in customers if c["customer_id"] in pol_by_cust]
    txns = []
    tid = 1_000_000
    while len(txns) < target and payers:
        c = rng.choice(payers)
        pol = rng.choice(pol_by_cust[c["customer_id"]])
        is_friction = c["customer_id"] in payment_friction
        # friction customers preferentially transact on the failing gateway.
        if is_friction and rng.random() < 0.6:
            system = COHORT_C_SYSTEM
        else:
            system = rng.choices(PAYMENT_SYSTEMS, weights=PAYMENT_SYSTEM_WEIGHTS)[0]
        amount = max(round(pol["annual_premium"] / 12.0 * rng.uniform(0.9, 1.1), 2), 10.0)
        # friction customers on the gateway fail hard + recently; else base rate.
        if is_friction and system == COHORT_C_SYSTEM:
            failed = rng.random() < 0.55
        else:
            failed = rng.random() < FAIL_PROB[system]
        if system == COHORT_C_SYSTEM and failed:
            created = TODAY - dt.timedelta(hours=rng.randint(0, 48),
                                           minutes=rng.randint(0, 59))
        else:
            created = TODAY - dt.timedelta(days=_recency_days(120),
                                           hours=rng.randint(0, 23),
                                           minutes=rng.randint(0, 59))
        if failed:
            status = "Failed"
            if system == COHORT_C_SYSTEM:
                reason = rng.choices(FAILURE_REASONS,
                                     weights=[0.10, 0.42, 0.08, 0.34, 0.06])[0]
            else:
                reason = rng.choices(FAILURE_REASONS,
                                     weights=[0.40, 0.14, 0.22, 0.14, 0.10])[0]
            attempt = rng.randint(2, 4)
        elif rng.random() < 0.03:
            status, reason, attempt = "Pending", None, 1
        else:
            status, reason, attempt = "Success", None, 1
        txns.append({
            "txn_id": tid, "customer_id": c["customer_id"],
            "policy_id": pol["policy_id"], "payment_system": system,
            "amount": amount, "status": status, "failure_reason": reason,
            "attempt_no": attempt, "created_at": created,
        })
        tid += 1
    return txns


def gen_fraud(claims, target=900):
    """SIU cases. Cohort D: openings in the last 30d exceed the prior 30d,
    concentrated in CommercialAuto / Injury."""
    flagged = [c for c in claims if c["fraud_investigation"]]
    pool = flagged + [c for c in claims if not c["fraud_investigation"]]
    cases = []
    caid = 300_000
    win30 = TODAY - dt.timedelta(days=30)
    win60 = TODAY - dt.timedelta(days=60)
    seen = set()
    for c in pool:
        if len(cases) >= target:
            break
        if c["claim_id"] in seen:
            continue
        seen.add(c["claim_id"])
        concentrated = c["product_line"] in COHORT_D_LINES or c["_ctype"] == "Injury"
        if concentrated:
            opened = rand_dt(win30, TODAY) if rng.random() < 0.62 else rand_dt(win60, win30)
        else:
            opened = min(c["fnol_at"] + dt.timedelta(hours=rng.randint(2, 240)), TODAY)
            if (TODAY - opened).days > 120:
                opened = rand_dt(TODAY - dt.timedelta(days=90), TODAY)
        cases.append({
            "case_id": caid, "claim_id": c["claim_id"],
            "customer_id": c["customer_id"], "segment": c["segment"],
            "product_line": c["product_line"],
            "fraud_type": rng.choices(FRAUD_TYPES, weights=FRAUD_TYPE_WEIGHTS)[0],
            "status": rng.choices(FRAUD_STATUSES, weights=FRAUD_STATUS_WEIGHTS)[0],
            "suspected_amount": round(c["claim_amount"] * rng.uniform(0.4, 1.0), 2),
            "opened_at": opened,
        })
        caid += 1
    return cases


# ---------------------------------------------------------------------------
# Cohort planting — assign a bounded, DISJOINT set of at-risk customers exactly
# one risk signal each. The event/payment generators then emit corroborating
# behavior for these sets; gen_customer_signals reads them directly. This keeps
# the at-risk population a crisp minority (~20%) with PaymentFriction on top.
# ---------------------------------------------------------------------------
def plant_cohorts(customers):
    """Return dict of disjoint customer_id sets, one per active risk signal.
    Fractions are of the whole customer base; PaymentFriction is largest so it
    wins cohort E 'top signal by count' and 'top action by LTV' (PaymentAssist)."""
    ids = [c["customer_id"] for c in customers]
    rng.shuffle(ids)
    n = len(ids)
    # disjoint slices (fractions sum to ~0.20 at-risk)
    frac = [("PaymentFriction", 0.090),
            ("ClaimFriction",   0.045),
            ("QuoteAbandon",    0.038),
            ("AuthFriction",    0.020),
            ("SentimentDrop",   0.013)]
    out, i = {}, 0
    for sig, f in frac:
        k = max(1, int(n * f))
        out[sig] = set(ids[i:i + k])
        i += k
    return out


def gen_interactions(customers, low_sentiment_custs, target=30000):
    """Omnichannel touch log. Claim-intent interactions skew negative; customers
    in low_sentiment_custs (poor claims experience) get more escalations."""
    inter = []
    iid = 2_000_000
    while len(inter) < target:
        c = rng.choice(customers)
        channel = rng.choices(CHANNELS, weights=CHANNEL_WEIGHTS)[0]
        intent = rng.choices(INTENTS, weights=INTENT_WEIGHTS)[0]
        occurred = TODAY - dt.timedelta(days=_recency_days(120),
                                        hours=rng.randint(0, 23),
                                        minutes=rng.randint(0, 59))
        # sentiment: pure Web/Mobile page-view style touches carry NULL
        if channel in ("Web", "Mobile") and rng.random() < 0.5:
            sentiment = None
        else:
            base = rng.gauss(0.35, 0.35)
            if intent in ("Complaint", "Claim"):
                base -= 0.45
            if c["customer_id"] in low_sentiment_custs:
                base -= 0.35
            sentiment = round(max(-1.0, min(1.0, base)), 3)
        resolved = rng.random() < (0.55 if intent in ("Complaint", "Claim") else 0.82)
        escalated = (not resolved) and rng.random() < (
            0.6 if c["customer_id"] in low_sentiment_custs else 0.25)
        inter.append({
            "interaction_id": iid, "customer_id": c["customer_id"],
            "channel": channel, "intent": intent, "sentiment": sentiment,
            "duration_sec": rng.randint(20, 1800), "resolved": resolved,
            "escalated": escalated, "occurred_at": occurred,
        })
        iid += 1
    return inter


def gen_web_events(customers, payment_friction, auth_friction, quote_abandon,
                   target=60000):
    """Clickstream / telemetry. The planted friction cohorts emit corroborating
    live-incident events in the last 24h: payment_friction -> PaymentRetry,
    auth_friction -> AuthFailure, quote_abandon -> QuoteAbandon. The rest is
    ordinary background clickstream. (Cohorts are planted, not discovered here.)"""
    events = []
    eid = 4_000_000
    incident = [(cid, "PaymentRetry", "Billing") for cid in payment_friction] \
        + [(cid, "AuthFailure", "Login") for cid in auth_friction] \
        + [(cid, "QuoteAbandon", "Quote") for cid in quote_abandon]
    while len(events) < target:
        # ~28% of events are a planted cohort's live-incident behavior
        if incident and rng.random() < 0.28:
            cid, etype, page = rng.choice(incident)
            occurred = TODAY - dt.timedelta(hours=rng.randint(0, 24),
                                            minutes=rng.randint(0, 59))
            # a couple of extra refreshes accompany the friction event
            if rng.random() < 0.4:
                etype, page = "PageRefresh", page
        else:
            c = rng.choice(customers)
            cid = c["customer_id"]
            etype = rng.choices(WEB_EVENT_TYPES, weights=WEB_EVENT_WEIGHTS)[0]
            page = rng.choice(PAGES)
            occurred = TODAY - dt.timedelta(days=_recency_days(90),
                                            hours=rng.randint(0, 23),
                                            minutes=rng.randint(0, 59))
        events.append({
            "event_id": eid, "customer_id": cid,
            "session_id": 3_000_000 + rng.randint(0, target),
            "event_type": etype, "page": page,
            "device": rng.choices(DEVICES, weights=DEVICE_WEIGHTS)[0],
            "occurred_at": occurred,
        })
        eid += 1
    return events


def gen_voc(customers, claim_friction, target=5000):
    """Voice-of-Customer. Cohort F: the Claims topic carries the lowest
    sentiment + NPS of all topics. The planted `claim_friction` customers each
    leave a strongly-negative Claims comment, corroborating their ClaimFriction
    signal; the topic is planted lowest for everyone else too."""
    fb = []
    fid = 6_000_000
    cust_by_id = {c["customer_id"]: c for c in customers}
    templates = {
        "Claims": ["Claim took forever to get approved.",
                   "No update on my claim for days.",
                   "Adjuster was hard to reach — frustrating."],
        "Billing": ["Payment kept failing on the site.",
                    "Billing was smooth this month.",
                    "Got double charged, had to call in."],
        "Pricing": ["Premium went up at renewal.",
                    "Fair price for the coverage.",
                    "Shopping around, competitors cheaper."],
        "Service": ["Agent was very helpful.",
                    "Long hold time on the phone.",
                    "Great support experience overall."],
        "Digital": ["App crashes when I upload photos.",
                    "Love the mobile app.",
                    "Website is confusing to navigate."],
        "Coverage": ["Wish umbrella coverage was clearer.",
                     "Coverage fit my needs well.",
                     "Didn't understand my deductible."],
    }
    # First, a guaranteed strongly-negative Claims comment per claim_friction
    # customer (corroborates the ClaimFriction signal).
    for cid in claim_friction:
        cust = cust_by_id.get(cid)
        if not cust or len(fb) >= target:
            continue
        fb.append({
            "feedback_id": fid, "customer_id": cid,
            "source": rng.choices(VOC_SOURCES, weights=VOC_SOURCE_WEIGHTS)[0],
            "nps": rng.randint(0, 3), "sentiment": round(rng.uniform(-0.9, -0.5), 3),
            "topic": "Claims", "comment": rng.choice(templates["Claims"]),
            "submitted_at": TODAY - dt.timedelta(days=rng.randint(0, 30),
                                                 hours=rng.randint(0, 23)),
        })
        fid += 1
    while len(fb) < target:
        c = rng.choice(customers)
        topic = rng.choices(VOC_TOPICS, weights=VOC_TOPIC_WEIGHTS)[0]
        source = rng.choices(VOC_SOURCES, weights=VOC_SOURCE_WEIGHTS)[0]
        # Claims topic sentiment is planted lowest
        if topic == "Claims":
            sentiment = round(max(-1.0, rng.gauss(-0.35, 0.30)), 3)
            nps = rng.randint(0, 6) if source == "NPS" else None
        elif topic == "Billing":
            sentiment = round(max(-1.0, min(1.0, rng.gauss(0.10, 0.35))), 3)
            nps = rng.randint(3, 8) if source == "NPS" else None
        else:
            sentiment = round(max(-1.0, min(1.0, rng.gauss(0.42, 0.30))), 3)
            nps = rng.randint(6, 10) if source == "NPS" else None
        fb.append({
            "feedback_id": fid, "customer_id": c["customer_id"],
            "source": source, "nps": nps, "sentiment": sentiment,
            "topic": topic, "comment": rng.choice(templates[topic]),
            "submitted_at": TODAY - dt.timedelta(days=_recency_days(90),
                                                 hours=rng.randint(0, 23)),
        })
        fid += 1
    return fb


def gen_customer_signals(customers, cohorts):
    """The at-risk scoreboard — one row per customer. Reads the planted, disjoint
    `cohorts` dict (signal -> set of customer_ids), assigns each customer its
    signal + canonical recommended_action + an elevated churn_risk_score, and
    writes churn_risk_score back onto the customer dict so the two tables agree.
    Cohort E: PaymentFriction is the largest planted cohort (top signal by count),
    and since PaymentAssist is its action and those customers span the LTV range,
    PaymentAssist is the top action by at-risk LTV."""
    # invert cohorts -> per-customer signal
    sig_of = {}
    for sig, ids in cohorts.items():
        for cid in ids:
            sig_of[cid] = sig
    signals = []
    for c in customers:
        cid = c["customer_id"]
        sig = sig_of.get(cid, "None")
        if sig == "None":
            strength = round(rng.uniform(0.0, 0.25), 3)
            churn = round(min(0.99, max(0.0, rng.gauss(0.18, 0.10))), 4)
            action = "None"
        else:
            strength = round(rng.uniform(0.55, 0.98), 3)
            churn = round(min(0.99, rng.uniform(0.55, 0.92)), 4)
            action = SIGNAL_ACTION[sig]
        c["churn_risk_score"] = churn   # write-back so customers agrees
        signals.append({
            "customer_id": cid, "segment": c["segment"], "risk_signal": sig,
            "signal_strength": strength, "churn_risk_score": churn,
            "recommended_action": action,
            "lifetime_value": c["lifetime_value"],
            "last_updated": TODAY - dt.timedelta(hours=rng.randint(0, 48)),
        })
    return signals


# ---------------------------------------------------------------------------
# Insert helpers
# ---------------------------------------------------------------------------
def _bulk_insert(cur, table, cols, rows, batch=1000):
    if not rows:
        return
    placeholders = ",".join(["%s"] * len(cols))
    sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        cur.executemany(sql, [tuple(r[c] for c in cols) for r in chunk])


# child -> parent order (no FKs, but keeps intent clear).
DATA_TABLES = ["customer_signals", "voc_feedback", "web_events", "interactions",
               "fraud_investigations", "payment_transactions",
               "underwriting_queue", "claims", "policies", "customers"]

# column order MUST match schema.sql exactly, per table.
COLS = {
    "customers": ["customer_id", "segment", "tenure_years", "home_state",
                  "region", "lifetime_value", "risk_tier", "acquisition_channel",
                  "signup_date", "churn_risk_score", "is_active"],
    "policies": ["policy_id", "customer_id", "segment", "product_line", "status",
                 "annual_premium", "coverage_limit", "deductible",
                 "effective_date", "renewal_date", "state"],
    "claims": ["claim_id", "policy_id", "customer_id", "segment", "product_line",
               "claim_type", "status", "fnol_at", "decision_at",
               "approval_hours", "claim_amount", "approved_amount",
               "adjuster_id", "fraud_investigation"],
    "underwriting_queue": ["submission_id", "customer_id", "segment",
                           "product_line", "queue_name", "status", "priority",
                           "submitted_at", "decided_at", "age_hours",
                           "assigned_underwriter"],
    "payment_transactions": ["txn_id", "customer_id", "policy_id",
                             "payment_system", "amount", "status",
                             "failure_reason", "attempt_no", "created_at"],
    "fraud_investigations": ["case_id", "claim_id", "customer_id", "segment",
                             "product_line", "fraud_type", "status",
                             "suspected_amount", "opened_at"],
    "interactions": ["interaction_id", "customer_id", "channel", "intent",
                     "sentiment", "duration_sec", "resolved", "escalated",
                     "occurred_at"],
    "web_events": ["event_id", "customer_id", "session_id", "event_type",
                   "page", "device", "occurred_at"],
    "voc_feedback": ["feedback_id", "customer_id", "source", "nps", "sentiment",
                     "topic", "comment", "submitted_at"],
    "customer_signals": ["customer_id", "segment", "risk_signal",
                         "signal_strength", "churn_risk_score",
                         "recommended_action", "lifetime_value", "last_updated"],
}


def clear_tables(cur):
    for t in DATA_TABLES:
        cur.execute(f"DELETE FROM {t}")


def _scalar(cur, sql):
    cur.execute(sql)
    row = cur.fetchone()
    return row[0] if row and row[0] is not None else 0


def print_summary(cur):
    print("\n=== ROW COUNTS ===")
    for t in DATA_TABLES + ["v_customer_360"]:
        print(f"  {t:24s} {_scalar(cur, f'SELECT COUNT(*) FROM {t}'):>10d}")

    print("\n=== VERIFICATION ORACLE (what Aura should return) ===")

    # A) Claim approval time: last 24h vs trailing 7d, by product line.
    print("  A) Avg claim approval_hours — last 24h vs 7d (by product line):")
    cur.execute("""
        SELECT product_line,
               AVG(CASE WHEN decision_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                        THEN approval_hours END) AS h24,
               AVG(CASE WHEN decision_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                        THEN approval_hours END) AS h7d
        FROM claims
        WHERE decision_at IS NOT NULL
        GROUP BY product_line
        ORDER BY h24 DESC""")
    for line, h24, h7d in cur.fetchall():
        s24 = f"{float(h24):6.1f}h" if h24 is not None else "   n/a"
        s7d = f"{float(h7d):6.1f}h" if h7d is not None else "   n/a"
        print(f"       {line:16s} 24h={s24}  7d={s7d}")
    ov24 = _scalar(cur, """SELECT AVG(approval_hours) FROM claims
                           WHERE decision_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)""")
    ov7d = _scalar(cur, """SELECT AVG(approval_hours) FROM claims
                           WHERE decision_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)""")
    print(f"       {'OVERALL':16s} 24h={float(ov24):6.1f}h  7d={float(ov7d):6.1f}h")

    # B) Underwriting backlog by queue — open count + avg age.
    print("  B) Underwriting queues — open count & avg age_hours:")
    cur.execute("""
        SELECT queue_name,
               SUM(CASE WHEN status IN ('Received','InReview','PendingInfo')
                        THEN 1 ELSE 0 END) AS open_cnt,
               COUNT(*) AS total,
               AVG(CASE WHEN status IN ('Received','InReview','PendingInfo')
                        THEN age_hours END) AS avg_open_age
        FROM underwriting_queue
        GROUP BY queue_name
        ORDER BY avg_open_age DESC""")
    for q, oc, tot, age in cur.fetchall():
        a = f"{float(age):6.1f}h" if age is not None else "   n/a"
        print(f"       {q:20s} open={int(oc):>4d}/{int(tot):<4d}  avg_open_age={a}")

    # C) Payment failure rate by system + top failure reason for the worst.
    print("  C) Payment failure rate by system (all-time) + last-24h:")
    cur.execute("""
        SELECT payment_system,
               SUM(CASE WHEN status='Failed' THEN 1 ELSE 0 END) AS failed,
               COUNT(*) AS total
        FROM payment_transactions
        GROUP BY payment_system
        ORDER BY failed / total DESC""")
    worst = None
    for sysname, failed, total in cur.fetchall():
        rate = (100.0 * int(failed) / int(total)) if int(total) else 0
        if worst is None:
            worst = sysname
        print(f"       {sysname:12s} {int(failed):>5d}/{int(total):<6d}  {rate:5.1f}%")
    r24 = _scalar(cur, """SELECT 100.0*SUM(CASE WHEN status='Failed' THEN 1 ELSE 0 END)/COUNT(*)
                          FROM payment_transactions
                          WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)""")
    print(f"       last-24h overall failure rate: {float(r24):.1f}%")
    if worst:
        cur.execute("""
            SELECT failure_reason, COUNT(*) FROM payment_transactions
            WHERE payment_system=%s AND status='Failed' AND failure_reason IS NOT NULL
            GROUP BY failure_reason ORDER BY COUNT(*) DESC LIMIT 2""", (worst,))
        reasons = ", ".join(f"{r}={int(n)}" for r, n in cur.fetchall())
        print(f"       worst system '{worst}' top reasons: {reasons}")

    # D) Fraud investigations: last-30d vs prior-30d, by product line.
    last30 = _scalar(cur, """SELECT COUNT(*) FROM fraud_investigations
                             WHERE opened_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)""")
    prior30 = _scalar(cur, """SELECT COUNT(*) FROM fraud_investigations
                              WHERE opened_at < DATE_SUB(NOW(), INTERVAL 30 DAY)
                                AND opened_at >= DATE_SUB(NOW(), INTERVAL 60 DAY)""")
    ratio = (float(last30) / prior30) if prior30 else 0
    print(f"  D) Fraud cases opened: last-30d={int(last30)} vs prior-30d={int(prior30)}"
          f"  ({ratio:.2f}x)")
    cur.execute("""
        SELECT product_line, COUNT(*) FROM fraud_investigations
        WHERE opened_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        GROUP BY product_line ORDER BY COUNT(*) DESC LIMIT 4""")
    for line, n in cur.fetchall():
        print(f"       {line:16s} {int(n):>4d}")

    # E) At-risk customers by signal + top action by at-risk LTV.
    print("  E) At-risk customers by risk_signal (count | total LTV):")
    cur.execute("""
        SELECT risk_signal, COUNT(*) AS cust, SUM(lifetime_value) AS ltv
        FROM customer_signals
        WHERE risk_signal <> 'None'
        GROUP BY risk_signal ORDER BY cust DESC""")
    for sig, cnt, ltv in cur.fetchall():
        print(f"       {sig:16s} {int(cnt):>5d}  ${float(ltv):>14,.0f}")
    hi = _scalar(cur, """SELECT COUNT(*) FROM customer_signals
                         WHERE risk_signal <> 'None'
                           AND lifetime_value >= (
                             SELECT AVG(lifetime_value) + STD(lifetime_value)
                             FROM customer_signals)""")
    print(f"       high-value (>= mean+1sd LTV) at-risk customers: {int(hi)}")
    cur.execute("""
        SELECT recommended_action, SUM(lifetime_value) AS ltv
        FROM customer_signals
        WHERE risk_signal <> 'None' AND recommended_action <> 'None'
        GROUP BY recommended_action ORDER BY ltv DESC LIMIT 1""")
    row = cur.fetchone()
    if row:
        print(f"       top action by at-risk LTV: {row[0]} (${float(row[1]):,.0f})")

    # F) VoC sentiment + NPS by topic (Claims should be lowest).
    print("  F) VoC avg sentiment & NPS by topic:")
    cur.execute("""
        SELECT topic, AVG(sentiment) AS s, AVG(nps) AS n, COUNT(*) AS c
        FROM voc_feedback GROUP BY topic ORDER BY s ASC""")
    for topic, s, n, c in cur.fetchall():
        ns = f"{float(n):4.1f}" if n is not None else " n/a"
        print(f"       {topic:10s} sentiment={float(s):+.3f}  nps={ns}  (n={int(c)})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def _generate_all(counts):
    """Build every table's rows in dependency order, wiring the correlated
    cohorts. `counts` overrides default volumes (used by seed_minimal)."""
    customers = gen_customers(n=counts["customers"])
    # Plant the disjoint at-risk cohorts up front; every downstream generator
    # emits behavior corroborating these sets (rather than discovering cohorts,
    # which over-counted the at-risk population).
    cohorts = plant_cohorts(customers)
    payment_friction = cohorts["PaymentFriction"]
    claim_friction = cohorts["ClaimFriction"]
    auth_friction = cohorts["AuthFriction"]
    quote_abandon = cohorts["QuoteAbandon"]

    policies = gen_policies(customers, target=counts["policies"])
    claims = gen_claims(customers, policies, target=counts["claims"])
    underwriting = gen_underwriting(customers, target=counts["underwriting"])
    payments = gen_payments(customers, policies, payment_friction,
                            target=counts["payments"])
    fraud = gen_fraud(claims, target=counts["fraud"])
    voc = gen_voc(customers, claim_friction, target=counts["voc"])
    web = gen_web_events(customers, payment_friction, auth_friction,
                         quote_abandon, target=counts["web_events"])
    interactions = gen_interactions(customers, claim_friction,
                                    target=counts["interactions"])
    # signals last — writes churn_risk_score back onto customers.
    signals = gen_customer_signals(customers, cohorts)
    return {
        "customers": customers, "policies": policies, "claims": claims,
        "underwriting_queue": underwriting, "payment_transactions": payments,
        "fraud_investigations": fraud, "interactions": interactions,
        "web_events": web, "voc_feedback": voc, "customer_signals": signals,
    }


DEFAULT_COUNTS = {
    "customers": 4000, "policies": 7500, "claims": 12000, "underwriting": 3500,
    "payments": 40000, "fraud": 900, "voc": 5000, "web_events": 60000,
    "interactions": 30000,
}

# insert order: parents first (customers/policies) so ids exist conceptually.
INSERT_ORDER = ["customers", "policies", "claims", "underwriting_queue",
                "payment_transactions", "fraud_investigations", "interactions",
                "web_events", "voc_feedback", "customer_signals"]


def load(data, clear=True):
    conn = connect()
    cur = conn.cursor()
    try:
        if clear:
            print("Clearing existing rows...")
            clear_tables(cur)
        for t in INSERT_ORDER:
            _bulk_insert(cur, t, COLS[t], data[t])
        conn.commit()
        print("Insert complete.")
        print_summary(cur)
    finally:
        cur.close()
        conn.close()


def main():
    load_env()
    clear = "--no-clear" not in sys.argv
    print(f"Generating synthetic data (seed={SEED}, today={TODAY.date()})...")
    data = _generate_all(DEFAULT_COUNTS)
    for t in INSERT_ORDER:
        print(f"  {t:24s} {len(data[t]):>8d}")
    load(data, clear=clear)


if __name__ == "__main__":
    main()
