from __future__ import annotations

import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from server.storage import Store


def test_migrates_020_database_without_losing_paired_terminal(tmp_path: Path):
    database = tmp_path / "legacy.db"
    terminal_id = "12345678-1234-4123-8123-123456789abc"
    now = int(time.time())
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE terminals (
                terminal_id TEXT PRIMARY KEY, pair_code TEXT NOT NULL UNIQUE,
                pair_expires_at INTEGER NOT NULL, target_user_id INTEGER,
                target_name TEXT, target_email TEXT, operator_name TEXT,
                pending_asset_json TEXT, pending_scan TEXT,
                pending_match_fields TEXT, pending_target_user_id INTEGER,
                created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, created_at INTEGER NOT NULL,
                terminal_id TEXT, operator_name TEXT, target_user_id INTEGER,
                target_name TEXT, scan_value TEXT, match_fields TEXT,
                asset_id INTEGER, asset_tag TEXT, action TEXT NOT NULL,
                result TEXT NOT NULL, message TEXT
            )
            """
        )
        connection.execute(
            """
            INSERT INTO terminals (
                terminal_id, pair_code, pair_expires_at, target_user_id,
                target_name, target_email, operator_name, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                terminal_id,
                "654321",
                0,
                42,
                "Jan Kowalski",
                "jan@example.org",
                "admin",
                now,
                now,
            ),
        )

    store = Store(str(database))
    terminal = store.get_terminal(terminal_id)

    assert terminal is not None
    assert terminal["target_user_id"] == 42
    assert terminal["is_paired"] == 1
    assert terminal["operation_mode"] == "checkout"
    assert terminal["batch_mode"] == 0
    assert terminal["last_activity_at"] == now
    store.log_event(
        terminal_id=terminal_id,
        operator_name="Operator Meteor",
        operator_user_id=99,
        operator_email="operator@example.org",
        action="migration-test",
        result="success",
    )
    assert store.recent_logs()[0]["operator_user_id"] == 99


def test_concurrent_workers_migrate_the_same_database_once(tmp_path: Path):
    database = tmp_path / "concurrent-legacy.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE terminals (
                terminal_id TEXT PRIMARY KEY, pair_code TEXT NOT NULL UNIQUE,
                pair_expires_at INTEGER NOT NULL, target_user_id INTEGER,
                target_name TEXT, target_email TEXT, operator_name TEXT,
                pending_asset_json TEXT, pending_scan TEXT,
                pending_match_fields TEXT, pending_target_user_id INTEGER,
                created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, created_at INTEGER NOT NULL,
                terminal_id TEXT, operator_name TEXT, target_user_id INTEGER,
                target_name TEXT, scan_value TEXT, match_fields TEXT,
                asset_id INTEGER, asset_tag TEXT, action TEXT NOT NULL,
                result TEXT NOT NULL, message TEXT
            )
            """
        )

    with ThreadPoolExecutor(max_workers=6) as executor:
        stores = list(executor.map(lambda _: Store(str(database)), range(12)))

    assert len(stores) == 12
    with sqlite3.connect(database) as connection:
        terminal_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(terminals)")
        }
        audit_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(audit_log)")
        }
        pair_request_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(pair_requests)")
        }
    assert "operator_user_id" in terminal_columns
    assert "batch_mode" in terminal_columns
    assert "batch_assets_json" in terminal_columns
    assert "last_activity_at" in terminal_columns
    assert "operator_user_id" in audit_columns
    assert "token_hash" in pair_request_columns
    assert "claimed_terminal_id" in pair_request_columns


def test_qr_pair_request_expires_and_cannot_be_claimed(tmp_path: Path):
    database = tmp_path / "qr-expiry.db"
    store = Store(str(database), qr_pair_ttl_minutes=1)
    terminal = store.create_terminal()
    token = store.create_pair_request(
        "setup",
        False,
        "Operator Meteor",
        99,
        "operator@example.org",
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE pair_requests SET expires_at = ?",
            (int(time.time()) - 1,),
        )

    assert store.claim_pair_request(token, terminal["terminal_id"]) is None
    assert store.get_terminal(terminal["terminal_id"])["is_paired"] == 0
