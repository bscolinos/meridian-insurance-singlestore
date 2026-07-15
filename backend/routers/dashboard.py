"""Dashboard router — the supporting-evidence metrics for the Meridian hero.

Two small endpoints, one per pillar. Aura Analyst carries the actual money
moments; these KPIs are the always-on headline that visually asserts the whole
business lives in ONE engine:

  * /overview/kpis (Pillar 1 — Real-Time Operational Intelligence): claims,
    underwriting, and payments sitting next to each other, all computed on LIVE
    operational data — the open-claims backlog, how long approvals are taking
    right now, whether payments are failing right now, and the active book.

  * /cip/at_risk (Pillar 2 — AI Customer Intelligence Platform): the "predict &
    prevent" scoreboard read straight off customer_signals — how many customers
    carry an active risk signal, how much lifetime value that puts at risk, the
    dominant signal, and the single next-best-action that recovers the most
    value. This is the surface that turns behavioral signals into action while
    the customer is still engaged.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

import singlestore

router = APIRouter(tags=["dashboard"])


@router.get("/overview/kpis")
def overview_kpis() -> dict:
    """Pillar-1 operational KPI row — all from the one unified database.

    * open_claims — claims still in flight (not Paid / Closed / Denied). The
      live claims backlog an ops leader watches.
    * avg_approval_hours_24h — average approval turnaround for claims decided in
      the last 24 hours. This is the metric behind "why did approvals slow down
      yesterday?"; it moves in real time as adjusters clear the queue.
    * payment_failure_rate_24h — % of payment attempts that failed in the last
      24 hours. Surfaces a live billing/gateway incident the instant it starts.
    * active_policies — the in-force book (status = 'Active').
    """
    try:
        with singlestore.cursor() as cur:
            def scalar(sql: str) -> int:
                cur.execute(sql)
                row = cur.fetchone()
                return int(row[0]) if row and row[0] is not None else 0

            open_claims = scalar(
                "SELECT COUNT(*) FROM claims "
                "WHERE status NOT IN ('Paid', 'Closed', 'Denied')")

            active_policies = scalar(
                "SELECT COUNT(*) FROM policies WHERE status = 'Active'")

            # Avg approval turnaround for claims DECIDED in the last 24h — a
            # float (hours), so it can't ride the integer scalar() helper.
            cur.execute(
                "SELECT AVG(approval_hours) FROM claims "
                "WHERE decision_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)")
            row = cur.fetchone()
            avg_approval_hours_24h = round(float(row[0]), 1) if row and row[0] is not None else 0.0

            # Payment failure rate over the last 24h — % failed of total. A
            # float percentage, computed as failed/total over the same window.
            failed_24h = scalar(
                "SELECT COUNT(*) FROM payment_transactions "
                "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR) "
                "AND status = 'Failed'")
            total_24h = scalar(
                "SELECT COUNT(*) FROM payment_transactions "
                "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)")
            payment_failure_rate_24h = round(100.0 * failed_24h / total_24h, 1) if total_24h else 0.0
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"database error: {e}")

    return {
        "open_claims": open_claims,
        "avg_approval_hours_24h": avg_approval_hours_24h,
        "payment_failure_rate_24h": payment_failure_rate_24h,
        "active_policies": active_policies,
    }


@router.get("/cip/at_risk")
def cip_at_risk() -> dict:
    """Pillar-2 Customer-Intelligence "predict & prevent" scoreboard.

    Read straight off customer_signals (one row per active customer), counting
    only customers who actually carry a risk signal (risk_signal <> 'None'):

    * at_risk_customers — how many customers are flagged at risk right now.
    * at_risk_ltv — total lifetime value those flagged customers represent, i.e.
      the revenue in play if the platform does nothing.
    * top_signal — the risk_signal flagging the most customers (the dominant
      failure mode; the demo plants PaymentFriction as #1).
    * top_action — the recommended_action that, if executed, addresses the most
      lifetime value (greatest summed LTV across its customers) — the single
      best next-best-action to take right now.
    * by_signal — per-signal breakdown (customers + LTV), ordered by customer
      count, for the strip's small chart.
    """
    try:
        with singlestore.cursor() as cur:
            def scalar(sql: str) -> int:
                cur.execute(sql)
                row = cur.fetchone()
                return int(row[0]) if row and row[0] is not None else 0

            at_risk_customers = scalar(
                "SELECT COUNT(*) FROM customer_signals "
                "WHERE risk_signal <> 'None'")

            # Total lifetime value in play across flagged customers.
            cur.execute(
                "SELECT COALESCE(SUM(lifetime_value), 0) FROM customer_signals "
                "WHERE risk_signal <> 'None'")
            row = cur.fetchone()
            at_risk_ltv = float(row[0]) if row and row[0] is not None else 0.0

            # Per-signal breakdown, ordered by customer count desc. The first
            # row's risk_signal is the top signal by count.
            cur.execute(
                "SELECT risk_signal, COUNT(*) AS customers, "
                "COALESCE(SUM(lifetime_value), 0) AS ltv "
                "FROM customer_signals WHERE risk_signal <> 'None' "
                "GROUP BY risk_signal ORDER BY customers DESC")
            by_signal = [
                {"risk_signal": r[0], "customers": int(r[1]), "ltv": float(r[2])}
                for r in cur.fetchall()
            ]
            top_signal = by_signal[0]["risk_signal"] if by_signal else "None"

            # Best next-best-action = recommended_action with the greatest
            # summed lifetime value at risk.
            cur.execute(
                "SELECT recommended_action FROM customer_signals "
                "WHERE risk_signal <> 'None' AND recommended_action <> 'None' "
                "GROUP BY recommended_action "
                "ORDER BY SUM(lifetime_value) DESC LIMIT 1")
            row = cur.fetchone()
            top_action = row[0] if row and row[0] is not None else "None"
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"database error: {e}")

    return {
        "at_risk_customers": at_risk_customers,
        "at_risk_ltv": at_risk_ltv,
        "top_signal": top_signal,
        "top_action": top_action,
        "by_signal": by_signal,
    }
