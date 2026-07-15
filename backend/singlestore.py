from __future__ import annotations
import os
from contextlib import contextmanager
import singlestoredb as s2

# The demo's dedicated database. It is NOT set as SINGLESTORE_DATABASE in .env,
# so we pin it explicitly on every connection here.
DB_NAME = "meridian_intel"


def _conn_kwargs(database: str | None = DB_NAME) -> dict:
    return {
        "host": os.environ["SINGLESTORE_HOST"],
        "port": int(os.environ.get("SINGLESTORE_PORT", "3306")),
        "user": os.environ.get("SINGLESTORE_USER", "admin"),
        "password": os.environ.get("SINGLESTORE_PASSWORD", ""),
        "database": database,
    }


def connect(database: str | None = DB_NAME):
    kw = _conn_kwargs(database)
    if kw["database"] is None:
        kw.pop("database")
    return s2.connect(**kw)


@contextmanager
def cursor():
    conn = connect()
    try:
        cur = conn.cursor()
        try:
            yield cur
        finally:
            cur.close()
    finally:
        conn.close()


def ping() -> dict:
    with cursor() as cur:
        cur.execute("SELECT @@version")
        row = cur.fetchone()
        return {"ok": True, "version": row[0] if row else None}


def table_counts() -> dict:
    """Best-effort row counts for the demo's core tables; None on any error.

    Covers the full Meridian schema — the operational-intelligence facts
    (Pillar 1) and the customer-intelligence signals (Pillar 2) all live in this
    one database, which is the whole point of the demo.
    """
    out: dict = {}
    tables = ["customers", "policies", "claims", "underwriting_queue",
              "payment_transactions", "fraud_investigations", "interactions",
              "web_events", "voc_feedback", "customer_signals"]
    with cursor() as cur:
        for t in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                row = cur.fetchone()
                out[t] = int(row[0]) if row else 0
            except Exception:  # noqa: BLE001
                out[t] = None
    return out
