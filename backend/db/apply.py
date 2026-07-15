#!/usr/bin/env python3
"""Apply the Meridian × SingleStore insurance schema to the live SingleStore workspace.

Reads credentials from ../../.env (repo root of the demo), creates the
`meridian_intel` database, then executes schema.sql statement-by-statement.
Re-runnable (DDL is idempotent). Prints a summary of tables + views.

Usage:
    source /Users/billscolinos/Documents/code_factory/.venv/bin/activate
    python backend/db/apply.py
"""
import os

import singlestoredb as s2

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.abspath(os.path.join(HERE, "..", "..", ".env"))
DB_NAME = "meridian_intel"


def load_env(path):
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def split_statements(sql):
    """Split into statements, honoring `DELIMITER //` blocks (stored procs).

    Ignores '--' comment lines. Outside a custom delimiter, statements end at a
    line-terminating ';'. Inside a `DELIMITER X` block, statements end at X.
    """
    stmts = []
    buf = []
    delim = ";"
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--") or not stripped:
            continue
        if stripped.upper().startswith("DELIMITER "):
            delim = stripped.split(None, 1)[1].strip()
            continue
        buf.append(line)
        joined = "\n".join(buf).rstrip()
        if joined.endswith(delim):
            stmt = joined[: -len(delim)].strip()
            if stmt:
                stmts.append(stmt)
            buf = []
            if delim != ";":
                delim = ";"
    tail = "\n".join(buf).strip().rstrip(";").strip()
    if tail:
        stmts.append(tail)
    return stmts


def run_file(cur, path):
    with open(path) as f:
        sql = f.read()
    for stmt in split_statements(sql):
        cur.execute(stmt)
        first = stmt.split("\n", 1)[0][:70]
        print(f"  ok: {first}")


def main():
    env = load_env(ENV_PATH)
    conn = s2.connect(
        host=env["SINGLESTORE_HOST"],
        port=int(env.get("SINGLESTORE_PORT", 3306)),
        user=env["SINGLESTORE_USER"],
        password=env["SINGLESTORE_PASSWORD"],
    )
    try:
        cur = conn.cursor()

        print("Applying schema.sql ...")
        run_file(cur, os.path.join(HERE, "schema.sql"))

        # Summary
        cur.execute(f"USE {DB_NAME}")
        cur.execute("SHOW FULL TABLES")
        rows = cur.fetchall()
        tables, views = [], []
        for name, ttype in rows:
            (views if str(ttype).upper() == "VIEW" else tables).append(name)

        print(f"\n=== Summary (database: {DB_NAME}) ===")
        print(f"Tables ({len(tables)}): {', '.join(sorted(tables))}")
        print(f"Views  ({len(views)}): {', '.join(sorted(views))}")
        conn.commit()
        print("\nDone.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
