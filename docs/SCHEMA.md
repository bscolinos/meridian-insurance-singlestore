# Meridian Intelligence Platform — schema & design contract

The authoritative schema, table/column definitions, planted-cohort design, and
verification oracle for this demo live in **[`DOMAIN_SPEC.md`](./DOMAIN_SPEC.md)**
(the binding contract every builder followed).

Quick reference — database **`meridian_intel`** (SingleStore), 10 tables + 1 view.
The customer is the join spine: all customer-scoped facts SHARD on `customer_id`
so the identity → policy → claim → payment → interaction join is local.

| Table | Role | Store | Shard key |
| --- | --- | --- | --- |
| `customers` | Policyholder identity spine (Personal/Commercial/Specialty) | rowstore | `customer_id` |
| `policies` | Issued policies (9 product lines) | rowstore | `customer_id` |
| `claims` | Claims lifecycle (FNOL → decision, approval_hours) | columnstore | `customer_id` |
| `underwriting_queue` | New-business/renewal submissions in the funnel | columnstore | `customer_id` |
| `payment_transactions` | Billing/payment attempts across payment systems | columnstore | `customer_id` |
| `fraud_investigations` | SIU cases on suspicious claims | columnstore | `customer_id` |
| `interactions` | Omnichannel touch log (call/chat/web/mobile/email) | columnstore | `customer_id` |
| `web_events` | Clickstream / page visits / app telemetry | columnstore | `customer_id` |
| `voc_feedback` | Voice-of-Customer (survey/NPS/reviews + sentiment) | columnstore | `customer_id` |
| `customer_signals` | At-risk scoreboard (risk_signal + recommended_action) | rowstore | `customer_id` |
| `v_customer_360` | Unified per-customer view (identity + ops + engagement + risk) | view | — |

**Two pillars.** Pillar 1 (real-time operations): claims, underwriting_queue,
payment_transactions, fraud_investigations. Pillar 2 (customer intelligence /
predict & prevent): interactions, web_events, voc_feedback, customer_signals.

**Money-moment cohorts (oracle in `generate_data.py :: print_summary`):**
A. Home/Property claim approvals slow in last 24h (~66h vs ~33h other lines).
B. Commercial-Property underwriting queue backlogged (open count + avg age).
C. CardGateway payment failures ~22% vs single-digit others (Gateway/Timeout).
D. Fraud investigations up ~1.7× last-30d vs prior-30d.
E. At-risk customers by signal — PaymentFriction top; PaymentAssist top action $.
F. Claims the lowest-sentiment VoC topic.
