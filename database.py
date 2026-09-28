"""SQLite storage for the QC Cross-Check System.

Creates the database file on first run and exposes small helper functions
for users, inspections and per-test results.
"""

import json
import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "qc_system.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    salt          TEXT    NOT NULL,
    full_name     TEXT    NOT NULL DEFAULT '',
    role          TEXT    NOT NULL DEFAULT 'inspector',
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS inspections (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    checksheet_key   TEXT NOT NULL,
    checksheet_name  TEXT NOT NULL,
    serial_number    TEXT NOT NULL,
    main_board_no    TEXT NOT NULL DEFAULT '',
    unit_fields_json TEXT NOT NULL DEFAULT '{}',
    operator_id      INTEGER,
    operator_name    TEXT NOT NULL DEFAULT '',
    overall_result   TEXT NOT NULL DEFAULT '',
    total_tests      INTEGER NOT NULL DEFAULT 0,
    ok_count         INTEGER NOT NULL DEFAULT 0,
    ng_count         INTEGER NOT NULL DEFAULT 0,
    rw_count         INTEGER NOT NULL DEFAULT 0,
    saved_at         TEXT NOT NULL,
    FOREIGN KEY (operator_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS test_results (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    inspection_id INTEGER NOT NULL,
    test_order    INTEGER NOT NULL,
    test_name     TEXT    NOT NULL,
    result        TEXT    NOT NULL,
    reason        TEXT    NOT NULL DEFAULT '',
    photo_path    TEXT    NOT NULL DEFAULT '',
    recorded_at   TEXT    NOT NULL,
    FOREIGN KEY (inspection_id) REFERENCES inspections (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_insp_serial ON inspections (serial_number);
CREATE INDEX IF NOT EXISTS idx_results_insp ON test_results (inspection_id);
"""


def get_conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables if missing and seed the first admin account."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        row = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()
        if row["n"] == 0:
            from auth import hash_password
            pw_hash, salt = hash_password("admin123")
            conn.execute(
                "INSERT INTO users (username, password_hash, salt, full_name,"
                " role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("admin", pw_hash, salt, "Default Administrator", "admin",
                 datetime.now().isoformat(timespec="seconds")),
            )


# --- Users ---------------------------------------------------------------

def get_user_by_username(username):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username = ? AND active = 1",
            (username.strip(),),
        ).fetchone()


def create_user(username, password, full_name="", role="inspector"):
    from auth import hash_password
    pw_hash, salt = hash_password(password)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, full_name,"
            " role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (username.strip(), pw_hash, salt, full_name, role,
             datetime.now().isoformat(timespec="seconds")),
        )


def set_password(username, new_password):
    from auth import hash_password
    pw_hash, salt = hash_password(new_password)
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, salt = ? WHERE username = ?",
            (pw_hash, salt, username.strip()),
        )


# --- Inspections ---------------------------------------------------------

def save_inspection(checksheet_key, checksheet_name, unit_fields, rows,
                    operator_id, operator_name):
    """Persist one completed checksheet.

    rows: list of dicts with keys test_order, test_name, result, reason,
          photo_path.
    Returns the new inspection id.
    """
    now = datetime.now().isoformat(timespec="seconds")
    counts = {"OK": 0, "NG": 0, "RW": 0}
    for r in rows:
        counts[r["result"]] = counts.get(r["result"], 0) + 1

    if counts["NG"]:
        overall = "NG"
    elif counts["RW"]:
        overall = "RW"
    else:
        overall = "OK"

    serial = unit_fields.get("serial_number", "")
    board = unit_fields.get("main_board_no", "")

    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO inspections (checksheet_key, checksheet_name,"
            " serial_number, main_board_no, unit_fields_json, operator_id,"
            " operator_name, overall_result, total_tests, ok_count, ng_count,"
            " rw_count, saved_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (checksheet_key, checksheet_name, serial, board,
             json.dumps(unit_fields, ensure_ascii=False), operator_id,
             operator_name, overall, len(rows), counts["OK"], counts["NG"],
             counts["RW"], now),
        )
        insp_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO test_results (inspection_id, test_order, test_name,"
            " result, reason, photo_path, recorded_at)"
            " VALUES (?,?,?,?,?,?,?)",
            [(insp_id, r["test_order"], r["test_name"], r["result"],
              r.get("reason", ""), r.get("photo_path", ""), now)
             for r in rows],
        )
    return insp_id, overall


def list_inspections(search="", checksheet_key="", limit=500):
    sql = ("SELECT id, saved_at, checksheet_name, serial_number,"
           " main_board_no, operator_name, overall_result, total_tests,"
           " ok_count, ng_count, rw_count FROM inspections WHERE 1=1")
    params = []
    if search:
        sql += (" AND (serial_number LIKE ? OR main_board_no LIKE ?"
                " OR operator_name LIKE ?)")
        like = f"%{search.strip()}%"
        params += [like, like, like]
    if checksheet_key:
        sql += " AND checksheet_key = ?"
        params.append(checksheet_key)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        return conn.execute(sql, params).fetchall()


def get_inspection(insp_id):
    with get_conn() as conn:
        head = conn.execute("SELECT * FROM inspections WHERE id = ?",
                            (insp_id,)).fetchone()
        rows = conn.execute(
            "SELECT * FROM test_results WHERE inspection_id = ?"
            " ORDER BY test_order", (insp_id,)).fetchall()
    return head, rows


def find_duplicate(checksheet_key, serial_number):
    """Cross-check helper: has this unit already been run on this sheet?"""
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, saved_at, overall_result, operator_name"
            " FROM inspections WHERE checksheet_key = ? AND serial_number = ?"
            " ORDER BY id DESC LIMIT 1",
            (checksheet_key, serial_number.strip()),
        ).fetchone()
