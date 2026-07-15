#!/usr/bin/env python3
"""Minimal-volume seed for the meridian_intel demo.

Reuses generate_data.py's deterministic generators at ~1/6 volume so the
workspace is populated quickly for a first end-to-end check. The planted
cohorts (slow Property claims, backlogged Commercial-Property queue, CardGateway
failure spike, rising fraud, PaymentFriction at-risk customers, low Claims
sentiment) scale down proportionally and still fire.

Usage:
    source /Users/billscolinos/Documents/code_factory/.venv/bin/activate
    python backend/db/seed_minimal.py
"""
import generate_data as g

MINIMAL_COUNTS = {
    "customers": 700, "policies": 1300, "claims": 2200, "underwriting": 620,
    "payments": 7000, "fraud": 170, "voc": 900, "web_events": 10000,
    "interactions": 5200,
}


def main():
    g.load_env()
    print(f"Minimal seed (seed={g.SEED}, today={g.TODAY.date()})...")
    data = g._generate_all(MINIMAL_COUNTS)
    for t in g.INSERT_ORDER:
        print(f"  {t:24s} {len(data[t]):>8d}")
    g.load(data, clear=True)


if __name__ == "__main__":
    main()
