#!/usr/bin/env python
"""Execute BRCA schema SQL file using psycopg2.

PowerShell:
  python .\scripts\db\run_sql_file.py
"""

from __future__ import annotations

import os
import traceback
from pathlib import Path

import psycopg2
from psycopg2 import OperationalError


DEFAULTS = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5443",
    "POSTGRES_DB": "Drug",
    "POSTGRES_USER": "Drug",
    "POSTGRES_PASSWORD": "1234",
}


def env_or_default(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return DEFAULTS[name]
    return value


def main() -> int:
    host = env_or_default("POSTGRES_HOST")
    port = env_or_default("POSTGRES_PORT")
    dbname = env_or_default("POSTGRES_DB")
    user = env_or_default("POSTGRES_USER")
    password = env_or_default("POSTGRES_PASSWORD")

    script_dir = Path(__file__).resolve().parent
    sql_path = (script_dir / "001_create_brca_tables.sql").resolve()

    if not sql_path.exists():
        print("[error] SQL file not found.")
        print(f"[error] Checked absolute path: {sql_path}")
        return 1

    try:
        sql_text = sql_path.read_text(encoding="utf-8-sig")
    except Exception as exc:  # noqa: BLE001
        print(f"[error] Failed to read SQL file: {exc}")
        print(f"[error] Checked absolute path: {sql_path}")
        return 1

    if not sql_text.strip():
        print("[error] SQL file is empty.")
        print(f"[error] Checked absolute path: {sql_path}")
        return 1

    print("[info] Starting SQL execution...")
    print(f"[info] SQL file: {sql_path}")
    print(f"[info] Target DB: host={host} port={port} db={dbname} user={user}")

    conn = None
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
        )
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(sql_text)
        conn.commit()
        print("[ok] SQL executed successfully.")
        return 0
    except OperationalError as exc:
        print("[error] PostgreSQL connection failed.")
        print(f"[error] host={host} port={port} db={dbname} user={user}")
        print(f"[error] Exception type: {type(exc).__name__}")
        print(f"[error] Details: {exc!r}")
        if getattr(exc, "pgerror", None):
            print(f"[error] pgerror: {exc.pgerror}")
        if getattr(exc, "diag", None):
            diag = exc.diag
            if getattr(diag, "message_primary", None):
                print(f"[error] diag.message_primary: {diag.message_primary}")
            if getattr(diag, "message_detail", None):
                print(f"[error] diag.message_detail: {diag.message_detail}")
            if getattr(diag, "message_hint", None):
                print(f"[error] diag.message_hint: {diag.message_hint}")
        print("[error] Traceback:")
        print(traceback.format_exc())
        if conn is not None:
            conn.rollback()
        return 2
    except Exception as exc:  # noqa: BLE001
        print("[error] SQL execution failed.")
        print(f"[error] Exception type: {type(exc).__name__}")
        print(f"[error] Details: {exc!r}")
        print("[error] Traceback:")
        print(traceback.format_exc())
        if conn is not None:
            conn.rollback()
        return 3
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
