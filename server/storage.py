from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


class Store:
    def __init__(
        self,
        database_path: str,
        pair_ttl_minutes: int = 15,
        terminal_idle_minutes: int = 15,
        qr_pair_ttl_minutes: int = 2,
        busy_timeout_seconds: int = 10,
        wal_enabled: bool = True,
        audit_retention_days: int = 365,
        terminal_retention_days: int = 90,
        backup_dir: str = "",
        backup_interval_hours: int = 24,
        backup_keep: int = 7,
        operation_lock_seconds: int = 120,
    ) -> None:
        self.database_path = database_path
        self.pair_ttl_seconds = pair_ttl_minutes * 60
        self.terminal_idle_seconds = max(0, terminal_idle_minutes * 60)
        self.qr_pair_ttl_seconds = max(60, qr_pair_ttl_minutes * 60)
        self.busy_timeout_seconds = max(1, int(busy_timeout_seconds))
        self.wal_enabled = bool(wal_enabled)
        self.audit_retention_seconds = max(0, int(audit_retention_days) * 86400)
        self.terminal_retention_seconds = max(
            0, int(terminal_retention_days) * 86400
        )
        self.backup_dir = str(backup_dir or "").strip()
        self.backup_interval_seconds = max(
            0, int(backup_interval_hours) * 3600
        )
        self.backup_keep = max(1, int(backup_keep))
        self.operation_lock_seconds = max(30, int(operation_lock_seconds))
        self.maintenance_error = ""
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()
        self._maybe_backup()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path, timeout=self.busy_timeout_seconds
        )
        connection.row_factory = sqlite3.Row
        connection.execute(f"PRAGMA busy_timeout={self.busy_timeout_seconds * 1000}")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            if self.wal_enabled:
                # Several Gunicorn workers may open a fresh database together.
                # Changing journal mode briefly needs an exclusive lock, so
                # retry that one bootstrap operation instead of failing a worker.
                for attempt in range(20):
                    try:
                        connection.execute("PRAGMA journal_mode=WAL")
                        break
                    except sqlite3.OperationalError as exc:
                        if "locked" not in str(exc).lower() or attempt == 19:
                            raise
                        time.sleep(0.05)
            # Gunicorn uruchamia kilka workerów jednocześnie. Blokada zapisu
            # sprawia, że tylko jeden z nich wykonuje migrację schematu naraz.
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS terminals (
                    terminal_id TEXT PRIMARY KEY,
                    pair_code TEXT NOT NULL UNIQUE,
                    pair_expires_at INTEGER NOT NULL,
                    target_user_id INTEGER,
                    target_name TEXT,
                    target_email TEXT,
                    operator_name TEXT,
                    operator_user_id INTEGER,
                    operator_email TEXT,
                    language TEXT,
                    is_paired INTEGER NOT NULL DEFAULT 0,
                    operation_mode TEXT NOT NULL DEFAULT 'checkout',
                    batch_mode INTEGER NOT NULL DEFAULT 0,
                    return_choice TEXT,
                    batch_assets_json TEXT,
                    last_activity_at INTEGER,
                    pending_asset_json TEXT,
                    pending_scan TEXT,
                    pending_match_fields TEXT,
                    pending_target_user_id INTEGER,
                    access_token_hash TEXT,
                    operation_lock_token TEXT,
                    operation_lock_at INTEGER,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at INTEGER NOT NULL,
                    terminal_id TEXT,
                    operator_name TEXT,
                    operator_user_id INTEGER,
                    operator_email TEXT,
                    target_user_id INTEGER,
                    target_name TEXT,
                    scan_value TEXT,
                    match_fields TEXT,
                    asset_id INTEGER,
                    asset_tag TEXT,
                    action TEXT NOT NULL,
                    result TEXT NOT NULL,
                    message TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pair_requests (
                    token_hash TEXT PRIMARY KEY,
                    operator_name TEXT NOT NULL,
                    operator_user_id INTEGER,
                    operator_email TEXT,
                    language TEXT,
                    operation_mode TEXT NOT NULL,
                    batch_mode INTEGER NOT NULL DEFAULT 0,
                    target_user_id INTEGER,
                    target_name TEXT,
                    target_email TEXT,
                    return_choice TEXT,
                    replace_terminal_id TEXT,
                    expires_at INTEGER NOT NULL,
                    claimed_terminal_id TEXT,
                    claimed_at INTEGER,
                    cancelled_at INTEGER,
                    created_at INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS rate_limits (
                    rate_key TEXT PRIMARY KEY,
                    window_started_at INTEGER NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    blocked_until INTEGER NOT NULL DEFAULT 0,
                    updated_at INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS maintenance_state (
                    state_key TEXT PRIMARY KEY,
                    state_value INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )
            self._migrate_columns(
                connection,
                "terminals",
                {
                    "operator_user_id": "INTEGER",
                    "operator_email": "TEXT",
                    "language": "TEXT",
                    "is_paired": "INTEGER NOT NULL DEFAULT 0",
                    "operation_mode": "TEXT NOT NULL DEFAULT 'checkout'",
                    "batch_mode": "INTEGER NOT NULL DEFAULT 0",
                    "return_choice": "TEXT",
                    "batch_assets_json": "TEXT",
                    "last_activity_at": "INTEGER",
                    "access_token_hash": "TEXT",
                    "operation_lock_token": "TEXT",
                    "operation_lock_at": "INTEGER",
                },
            )
            self._migrate_columns(
                connection,
                "audit_log",
                {
                    "operator_user_id": "INTEGER",
                    "operator_email": "TEXT",
                },
            )
            self._migrate_columns(
                connection,
                "pair_requests",
                {"replace_terminal_id": "TEXT", "language": "TEXT"},
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_log_created_at "
                "ON audit_log(created_at DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_log_operator_user "
                "ON audit_log(operator_user_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_log_operator_email "
                "ON audit_log(operator_email)"
            )
            # Wersje <= 0.2 rozpoznawały sparowanie po obecności odbiorcy.
            connection.execute(
                """
                UPDATE terminals
                SET is_paired = 1
                WHERE target_user_id IS NOT NULL AND is_paired = 0
                """
            )
            connection.execute(
                """
                UPDATE terminals SET last_activity_at = updated_at
                WHERE is_paired = 1
                  AND (last_activity_at IS NULL OR last_activity_at = 0)
                """
            )
            self._cleanup_old_records(connection)

    def get_settings(self) -> dict[str, str]:
        """Return administrator-managed application settings."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT setting_key, setting_value FROM app_settings"
            ).fetchall()
        return {str(row["setting_key"]): str(row["setting_value"]) for row in rows}

    def set_settings(self, settings: dict[str, str]) -> None:
        """Atomically update administrator-managed application settings."""
        now = int(time.time())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            for key, value in settings.items():
                connection.execute(
                    """
                    INSERT INTO app_settings(setting_key, setting_value, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(setting_key) DO UPDATE SET
                        setting_value = excluded.setting_value,
                        updated_at = excluded.updated_at
                    """,
                    (str(key), str(value), now),
                )

    @staticmethod
    def _migrate_columns(
        connection: sqlite3.Connection,
        table: str,
        columns: dict[str, str],
    ) -> None:
        existing = {
            str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")
        }
        for name, declaration in columns.items():
            if name not in existing:
                connection.execute(
                    f"ALTER TABLE {table} ADD COLUMN {name} {declaration}"
                )

    def _cleanup_old_records(self, connection: sqlite3.Connection) -> None:
        now = int(time.time())
        connection.execute(
            "DELETE FROM pair_requests WHERE expires_at < ?",
            (now - 86400,),
        )
        connection.execute(
            "DELETE FROM rate_limits WHERE updated_at < ? AND blocked_until < ?",
            (now - 86400, now),
        )
        if self.audit_retention_seconds > 0:
            connection.execute(
                "DELETE FROM audit_log WHERE created_at < ?",
                (now - self.audit_retention_seconds,),
            )
        if self.terminal_retention_seconds > 0:
            connection.execute(
                """
                DELETE FROM terminals
                WHERE is_paired = 0 AND updated_at < ?
                """,
                (now - self.terminal_retention_seconds,),
            )

    def _maybe_backup(self) -> None:
        if self.backup_interval_seconds <= 0:
            return
        now = int(time.time())
        claimed = False
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT state_value FROM maintenance_state WHERE state_key = ?",
                    ("last_backup_at",),
                ).fetchone()
                last_backup_at = int(row[0]) if row else 0
                if now - last_backup_at >= self.backup_interval_seconds:
                    connection.execute(
                        """
                        INSERT INTO maintenance_state (state_key, state_value, updated_at)
                        VALUES (?, ?, ?)
                        ON CONFLICT(state_key) DO UPDATE SET
                            state_value = excluded.state_value,
                            updated_at = excluded.updated_at
                        """,
                        ("last_backup_at", now, now),
                    )
                    claimed = True
            if not claimed:
                return

            backup_directory = Path(
                self.backup_dir
                or str(Path(self.database_path).resolve().parent / "backups")
            )
            backup_directory.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.fromtimestamp(now).strftime("%Y%m%d-%H%M%S")
            destination = backup_directory / f"bridge-{timestamp}.db"
            temporary = backup_directory / f".{destination.name}.tmp"
            with self._connect() as source, sqlite3.connect(temporary) as target:
                source.backup(target)
            os.replace(temporary, destination)
            backups = sorted(backup_directory.glob("bridge-*.db"), reverse=True)
            for stale_backup in backups[self.backup_keep :]:
                stale_backup.unlink(missing_ok=True)
            self.maintenance_error = ""
        except (OSError, sqlite3.Error) as exc:
            self.maintenance_error = str(exc)
            if claimed:
                try:
                    with self._connect() as connection:
                        connection.execute(
                            "DELETE FROM maintenance_state WHERE state_key = ?",
                            ("last_backup_at",),
                        )
                except sqlite3.Error:
                    pass

    def readiness(self) -> dict[str, Any]:
        with self._connect() as connection:
            quick_check = str(connection.execute("PRAGMA quick_check").fetchone()[0])
            journal_mode = str(
                connection.execute("PRAGMA journal_mode").fetchone()[0]
            ).casefold()
            connection.execute("SELECT 1 FROM terminals LIMIT 1").fetchone()
        return {
            "database": "ok" if quick_check.casefold() == "ok" else quick_check,
            "journal_mode": journal_mode,
            "maintenance_error": self.maintenance_error,
        }

    def rate_limit_retry_after(self, rate_key: str) -> int:
        now = int(time.time())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT blocked_until FROM rate_limits WHERE rate_key = ?",
                (rate_key,),
            ).fetchone()
        return max(0, int(row[0]) - now) if row else 0

    def register_rate_limit_failure(
        self,
        rate_key: str,
        *,
        max_attempts: int,
        window_seconds: int,
        block_seconds: int,
    ) -> int:
        now = int(time.time())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM rate_limits WHERE rate_key = ?",
                (rate_key,),
            ).fetchone()
            if row and int(row["blocked_until"] or 0) > now:
                return int(row["blocked_until"]) - now
            if not row or int(row["window_started_at"]) + window_seconds <= now:
                attempts = 1
                window_started_at = now
            else:
                attempts = int(row["attempts"]) + 1
                window_started_at = int(row["window_started_at"])
            blocked_until = now + block_seconds if attempts >= max_attempts else 0
            cursor = connection.execute(
                """
                INSERT INTO rate_limits (
                    rate_key, window_started_at, attempts, blocked_until, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(rate_key) DO UPDATE SET
                    window_started_at = excluded.window_started_at,
                    attempts = excluded.attempts,
                    blocked_until = excluded.blocked_until,
                    updated_at = excluded.updated_at
                """,
                (rate_key, window_started_at, attempts, blocked_until, now),
            )
        return max(0, blocked_until - now)

    def clear_rate_limit(self, rate_key: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM rate_limits WHERE rate_key = ?", (rate_key,)
            )

    def _new_pair_code(self, connection: sqlite3.Connection) -> str:
        for _ in range(20):
            code = f"{secrets.randbelow(1_000_000):06d}"
            exists = connection.execute(
                "SELECT 1 FROM terminals WHERE pair_code = ?", (code,)
            ).fetchone()
            if not exists:
                return code
        raise RuntimeError("Nie udało się wygenerować kodu parowania.")

    @staticmethod
    def _pair_token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("ascii")).hexdigest()

    def create_pair_request(
        self,
        operation_mode: str,
        batch_mode: bool,
        operator_name: str,
        operator_user_id: int | None,
        operator_email: str,
        target_user_id: int | None = None,
        target_name: str = "",
        target_email: str = "",
        return_choice: str | None = None,
        replace_terminal_id: str | None = None,
        language: str = "",
    ) -> str:
        if operation_mode not in {"setup", "checkout", "checkin"}:
            raise ValueError("Nieprawidłowa operacja terminala.")
        if operation_mode == "checkout" and target_user_id is None:
            raise ValueError("Wydanie wymaga wskazania odbiorcy.")
        if operation_mode == "checkin" and return_choice not in {
            "ready",
            "service",
        }:
            raise ValueError("Nieprawidłowy tryb przyjęcia sprzętu.")

        token = secrets.token_urlsafe(18)
        now = int(time.time())
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM pair_requests WHERE expires_at < ?",
                (now - 86400,),
            )
            connection.execute(
                """
                INSERT INTO pair_requests (
                    token_hash, operator_name, operator_user_id, operator_email, language,
                    operation_mode, batch_mode, target_user_id, target_name,
                    target_email, return_choice, replace_terminal_id,
                    expires_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self._pair_token_hash(token),
                    operator_name,
                    operator_user_id,
                    operator_email,
                    language if language in {"pl", "en"} else "",
                    operation_mode,
                    int(batch_mode),
                    target_user_id,
                    target_name,
                    target_email,
                    return_choice,
                    replace_terminal_id,
                    now + self.qr_pair_ttl_seconds,
                    now,
                ),
            )
        return token

    def pair_terminal_setup(
        self,
        pair_code: str,
        operator_name: str,
        operator_user_id: int | None = None,
        operator_email: str = "",
        language: str = "",
    ) -> dict[str, Any] | None:
        now = int(time.time())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT * FROM terminals
                WHERE pair_code = ? AND pair_expires_at >= ? AND is_paired = 0
                """,
                (pair_code, now),
            ).fetchone()
            if not row:
                return None
            cursor = connection.execute(
                """
                UPDATE terminals
                SET target_user_id = NULL, target_name = NULL,
                    target_email = NULL, operator_name = ?,
                    operator_user_id = ?, operator_email = ?, language = ?, is_paired = 1,
                    operation_mode = 'setup', batch_mode = 0,
                    return_choice = NULL, batch_assets_json = NULL,
                    pending_asset_json = NULL, pending_scan = NULL,
                    pending_match_fields = NULL,
                    pending_target_user_id = NULL, pair_expires_at = 0,
                    operation_lock_token = NULL, operation_lock_at = NULL,
                    last_activity_at = ?, updated_at = ?
                WHERE terminal_id = ? AND is_paired = 0
                """,
                (
                    operator_name,
                    operator_user_id,
                    operator_email,
                    language if language in {"pl", "en"} else "",
                    now,
                    now,
                    row["terminal_id"],
                ),
            )
        return self.get_terminal(row["terminal_id"]) if cursor.rowcount else None

    def get_pair_request(self, token: str) -> dict[str, Any] | None:
        try:
            token_hash = self._pair_token_hash(token)
        except UnicodeEncodeError:
            return None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM pair_requests WHERE token_hash = ?",
                (token_hash,),
            ).fetchone()
        return dict(row) if row else None

    def claim_pair_request(
        self, token: str, terminal_id: str
    ) -> dict[str, Any] | None:
        try:
            token_hash = self._pair_token_hash(token)
        except UnicodeEncodeError:
            return None
        now = int(time.time())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            pair_request = connection.execute(
                """
                SELECT * FROM pair_requests
                WHERE token_hash = ? AND expires_at >= ?
                  AND claimed_at IS NULL AND cancelled_at IS NULL
                """,
                (token_hash, now),
            ).fetchone()
            terminal = connection.execute(
                "SELECT * FROM terminals WHERE terminal_id = ? AND is_paired = 0",
                (terminal_id,),
            ).fetchone()
            if not pair_request or not terminal:
                return None

            connection.execute(
                """
                UPDATE terminals
                SET target_user_id = ?, target_name = ?, target_email = ?,
                    operator_name = ?, operator_user_id = ?, operator_email = ?, language = ?,
                    is_paired = 1, operation_mode = ?, batch_mode = ?,
                    return_choice = ?, batch_assets_json = NULL,
                    pending_asset_json = NULL, pending_scan = NULL,
                    pending_match_fields = NULL, pending_target_user_id = NULL,
                    pair_expires_at = 0, operation_lock_token = NULL,
                    operation_lock_at = NULL, last_activity_at = ?, updated_at = ?
                WHERE terminal_id = ? AND is_paired = 0
                """,
                (
                    pair_request["target_user_id"],
                    pair_request["target_name"],
                    pair_request["target_email"],
                    pair_request["operator_name"],
                    pair_request["operator_user_id"],
                    pair_request["operator_email"],
                    pair_request["language"],
                    pair_request["operation_mode"],
                    pair_request["batch_mode"],
                    pair_request["return_choice"],
                    now,
                    now,
                    terminal_id,
                ),
            )
            connection.execute(
                """
                UPDATE pair_requests
                SET claimed_terminal_id = ?, claimed_at = ?
                WHERE token_hash = ? AND claimed_at IS NULL
                """,
                (terminal_id, now, token_hash),
            )
            replace_terminal_id = str(
                pair_request["replace_terminal_id"] or ""
            ).strip()
            if replace_terminal_id and replace_terminal_id != terminal_id:
                replacement_pair_code = self._new_pair_code(connection)
                connection.execute(
                    """
                    UPDATE terminals
                    SET pair_code = ?, pair_expires_at = ?,
                        target_user_id = NULL, target_name = NULL,
                        target_email = NULL, operator_name = NULL,
                        operator_user_id = NULL, operator_email = NULL,
                        is_paired = 0, operation_mode = 'checkout', batch_mode = 0,
                        return_choice = NULL, batch_assets_json = NULL,
                        pending_asset_json = NULL, pending_scan = NULL,
                        pending_match_fields = NULL,
                        pending_target_user_id = NULL, last_activity_at = 0,
                        operation_lock_token = NULL, operation_lock_at = NULL,
                        updated_at = ?
                    WHERE terminal_id = ? AND is_paired = 1
                    """,
                    (
                        replacement_pair_code,
                        now + self.pair_ttl_seconds,
                        now,
                        replace_terminal_id,
                    ),
                )
        return self.get_terminal(terminal_id)

    def cancel_pair_request(self, token: str) -> bool:
        try:
            token_hash = self._pair_token_hash(token)
        except UnicodeEncodeError:
            return False
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE pair_requests SET cancelled_at = ?
                WHERE token_hash = ? AND claimed_at IS NULL
                  AND cancelled_at IS NULL
                """,
                (int(time.time()), token_hash),
            )
        return bool(cursor.rowcount)

    def create_terminal(self) -> dict[str, Any]:
        terminal_id = str(uuid.uuid4())
        access_token = secrets.token_urlsafe(24)
        now = int(time.time())
        with self._connect() as connection:
            pair_code = self._new_pair_code(connection)
            connection.execute(
                """
                INSERT INTO terminals (
                    terminal_id, pair_code, pair_expires_at, access_token_hash,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    terminal_id,
                    pair_code,
                    now + self.pair_ttl_seconds,
                    self._pair_token_hash(access_token),
                    now,
                    now,
                ),
            )
        terminal = self.get_terminal(terminal_id)
        if not terminal:
            raise RuntimeError("Nie udało się utworzyć terminala.")
        terminal["_access_token"] = access_token
        return terminal

    def provision_terminal_access(self, terminal_id: str) -> str | None:
        access_token = secrets.token_urlsafe(24)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT access_token_hash FROM terminals WHERE terminal_id = ?",
                (terminal_id,),
            ).fetchone()
            if not row or row["access_token_hash"]:
                return None
            cursor = connection.execute(
                """
                UPDATE terminals SET access_token_hash = ?, updated_at = ?
                WHERE terminal_id = ? AND access_token_hash IS NULL
                """,
                (
                    self._pair_token_hash(access_token),
                    int(time.time()),
                    terminal_id,
                ),
            )
        return access_token if cursor.rowcount else None

    def verify_terminal_access(self, terminal_id: str, access_token: str) -> bool:
        if not access_token:
            return False
        try:
            wanted_hash = self._pair_token_hash(access_token)
        except UnicodeEncodeError:
            return False
        with self._connect() as connection:
            row = connection.execute(
                "SELECT access_token_hash FROM terminals WHERE terminal_id = ?",
                (terminal_id,),
            ).fetchone()
        stored_hash = str(row["access_token_hash"] or "") if row else ""
        return bool(stored_hash) and secrets.compare_digest(stored_hash, wanted_hash)

    def acquire_operation_lock(self, terminal_id: str) -> str | None:
        now = int(time.time())
        lock_token = secrets.token_urlsafe(18)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT operation_lock_token, operation_lock_at
                FROM terminals WHERE terminal_id = ? AND is_paired = 1
                """,
                (terminal_id,),
            ).fetchone()
            if not row:
                return None
            current_token = str(row["operation_lock_token"] or "")
            current_at = int(row["operation_lock_at"] or 0)
            if current_token and current_at + self.operation_lock_seconds > now:
                return None
            cursor = connection.execute(
                """
                UPDATE terminals
                SET operation_lock_token = ?, operation_lock_at = ?
                WHERE terminal_id = ? AND is_paired = 1
                """,
                (lock_token, now, terminal_id),
            )
        return lock_token if cursor.rowcount else None

    def release_operation_lock(self, terminal_id: str, lock_token: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE terminals
                SET operation_lock_token = NULL, operation_lock_at = NULL
                WHERE terminal_id = ? AND operation_lock_token = ?
                """,
                (terminal_id, lock_token),
            )

    def get_terminal(self, terminal_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM terminals WHERE terminal_id = ?", (terminal_id,)
            ).fetchone()
            if not row:
                return None

            terminal = dict(row)
            now = int(time.time())
            last_activity = int(terminal.get("last_activity_at") or 0)
            if (
                terminal["is_paired"]
                and self.terminal_idle_seconds > 0
                and last_activity > 0
                and last_activity + self.terminal_idle_seconds < now
            ):
                pair_code = self._new_pair_code(connection)
                expires = now + self.pair_ttl_seconds
                connection.execute(
                    """
                    UPDATE terminals
                    SET pair_code = ?, pair_expires_at = ?,
                        target_user_id = NULL, target_name = NULL,
                        target_email = NULL, operator_name = NULL,
                        operator_user_id = NULL, operator_email = NULL,
                        is_paired = 0, operation_mode = 'checkout', batch_mode = 0,
                        return_choice = NULL, batch_assets_json = NULL,
                        pending_asset_json = NULL, pending_scan = NULL,
                        pending_match_fields = NULL,
                        pending_target_user_id = NULL, last_activity_at = 0,
                        operation_lock_token = NULL, operation_lock_at = NULL,
                        updated_at = ?
                    WHERE terminal_id = ?
                    """,
                    (pair_code, expires, now, terminal_id),
                )
                row = connection.execute(
                    "SELECT * FROM terminals WHERE terminal_id = ?", (terminal_id,)
                ).fetchone()
                terminal = dict(row)
            if not terminal["is_paired"] and terminal["pair_expires_at"] < now:
                pair_code = self._new_pair_code(connection)
                expires = now + self.pair_ttl_seconds
                connection.execute(
                    """
                    UPDATE terminals
                    SET pair_code = ?, pair_expires_at = ?, updated_at = ?
                    WHERE terminal_id = ?
                    """,
                    (pair_code, expires, now, terminal_id),
                )
                terminal["pair_code"] = pair_code
                terminal["pair_expires_at"] = expires
            return terminal

    def get_pairable_terminal(self, pair_code: str) -> dict[str, Any] | None:
        """Return an unpaired terminal only while its code is still valid."""
        now = int(time.time())
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM terminals
                WHERE pair_code = ? AND pair_expires_at >= ? AND is_paired = 0
                """,
                (pair_code, now),
            ).fetchone()
        return dict(row) if row else None

    def pair_terminal(
        self,
        pair_code: str,
        user_id: int,
        user_name: str,
        user_email: str,
        operator_name: str,
        operator_user_id: int | None = None,
        operator_email: str = "",
        batch_mode: bool = False,
        language: str = "",
    ) -> dict[str, Any] | None:
        now = int(time.time())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT * FROM terminals
                WHERE pair_code = ? AND pair_expires_at >= ?
                """,
                (pair_code, now),
            ).fetchone()
            if not row:
                return None
            cursor = connection.execute(
                """
                UPDATE terminals
                SET target_user_id = ?, target_name = ?, target_email = ?,
                    operator_name = ?, operator_user_id = ?, operator_email = ?, language = ?,
                    is_paired = 1, operation_mode = 'checkout', batch_mode = ?,
                    return_choice = NULL, batch_assets_json = NULL,
                    pending_asset_json = NULL,
                    pending_scan = NULL, pending_match_fields = NULL,
                    pending_target_user_id = NULL, pair_expires_at = 0,
                    operation_lock_token = NULL, operation_lock_at = NULL,
                    last_activity_at = ?, updated_at = ?
                WHERE terminal_id = ? AND is_paired = 0
                """,
                (
                    user_id,
                    user_name,
                    user_email,
                    operator_name,
                    operator_user_id,
                    operator_email,
                    language if language in {"pl", "en"} else "",
                    int(batch_mode),
                    now,
                    now,
                    row["terminal_id"],
                ),
            )
        return self.get_terminal(row["terminal_id"]) if cursor.rowcount else None

    def pair_terminal_return(
        self,
        pair_code: str,
        return_choice: str,
        operator_name: str,
        operator_user_id: int | None = None,
        operator_email: str = "",
        batch_mode: bool = False,
        language: str = "",
    ) -> dict[str, Any] | None:
        if return_choice not in {"ready", "service"}:
            raise ValueError("Nieprawidłowy tryb przyjęcia sprzętu.")
        now = int(time.time())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT * FROM terminals
                WHERE pair_code = ? AND pair_expires_at >= ?
                """,
                (pair_code, now),
            ).fetchone()
            if not row:
                return None
            cursor = connection.execute(
                """
                UPDATE terminals
                SET target_user_id = NULL, target_name = NULL, target_email = NULL,
                    operator_name = ?, operator_user_id = ?, operator_email = ?, language = ?,
                    is_paired = 1, operation_mode = 'checkin', batch_mode = ?,
                    return_choice = ?, batch_assets_json = NULL,
                    pending_asset_json = NULL, pending_scan = NULL,
                    pending_match_fields = NULL, pending_target_user_id = NULL,
                    pair_expires_at = 0, operation_lock_token = NULL,
                    operation_lock_at = NULL, last_activity_at = ?, updated_at = ?
                WHERE terminal_id = ? AND is_paired = 0
                """,
                (
                    operator_name,
                    operator_user_id,
                    operator_email,
                    language if language in {"pl", "en"} else "",
                    int(batch_mode),
                    return_choice,
                    now,
                    now,
                    row["terminal_id"],
                ),
            )
        return self.get_terminal(row["terminal_id"]) if cursor.rowcount else None

    def clear_target(self, terminal_id: str) -> None:
        now = int(time.time())
        with self._connect() as connection:
            pair_code = self._new_pair_code(connection)
            connection.execute(
                """
                UPDATE terminals
                SET pair_code = ?, pair_expires_at = ?,
                    target_user_id = NULL, target_name = NULL,
                    target_email = NULL, operator_name = NULL,
                    operator_user_id = NULL, operator_email = NULL,
                    is_paired = 0, operation_mode = 'checkout', batch_mode = 0,
                    return_choice = NULL, batch_assets_json = NULL,
                    pending_asset_json = NULL, pending_scan = NULL,
                    pending_match_fields = NULL,
                    pending_target_user_id = NULL, last_activity_at = 0,
                    operation_lock_token = NULL, operation_lock_at = NULL,
                    updated_at = ?
                WHERE terminal_id = ?
                """,
                (pair_code, now + self.pair_ttl_seconds, now, terminal_id),
            )

    def reconfigure_terminal_checkout(
        self,
        terminal_id: str,
        user_id: int,
        user_name: str,
        user_email: str,
        operator_name: str,
        operator_user_id: int | None = None,
        operator_email: str = "",
        batch_mode: bool = False,
    ) -> dict[str, Any] | None:
        now = int(time.time())
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE terminals
                SET target_user_id = ?, target_name = ?, target_email = ?,
                    operator_name = ?, operator_user_id = ?, operator_email = ?,
                    operation_mode = 'checkout', batch_mode = ?, return_choice = NULL,
                    pending_asset_json = NULL, pending_scan = NULL,
                    pending_match_fields = NULL, pending_target_user_id = NULL,
                    batch_assets_json = NULL, last_activity_at = ?, updated_at = ?
                WHERE terminal_id = ? AND is_paired = 1
                  AND operation_lock_token IS NULL
                """,
                (
                    user_id,
                    user_name,
                    user_email,
                    operator_name,
                    operator_user_id,
                    operator_email,
                    int(batch_mode),
                    now,
                    now,
                    terminal_id,
                ),
            )
        return self.get_terminal(terminal_id) if cursor.rowcount else None

    def reconfigure_terminal_return(
        self,
        terminal_id: str,
        return_choice: str,
        operator_name: str,
        operator_user_id: int | None = None,
        operator_email: str = "",
        batch_mode: bool = False,
    ) -> dict[str, Any] | None:
        if return_choice not in {"ready", "service"}:
            raise ValueError("Nieprawidłowy tryb przyjęcia sprzętu.")
        now = int(time.time())
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE terminals
                SET target_user_id = NULL, target_name = NULL, target_email = NULL,
                    operator_name = ?, operator_user_id = ?, operator_email = ?,
                    operation_mode = 'checkin', batch_mode = ?, return_choice = ?,
                    pending_asset_json = NULL, pending_scan = NULL,
                    pending_match_fields = NULL, pending_target_user_id = NULL,
                    batch_assets_json = NULL, last_activity_at = ?, updated_at = ?
                WHERE terminal_id = ? AND is_paired = 1
                  AND operation_lock_token IS NULL
                """,
                (
                    operator_name,
                    operator_user_id,
                    operator_email,
                    int(batch_mode),
                    return_choice,
                    now,
                    now,
                    terminal_id,
                ),
            )
        return self.get_terminal(terminal_id) if cursor.rowcount else None

    def get_batch_items(self, terminal_id: str) -> list[dict[str, Any]]:
        terminal = self.get_terminal(terminal_id)
        if not terminal or not terminal["batch_assets_json"]:
            return []
        try:
            items = json.loads(terminal["batch_assets_json"])
        except (TypeError, ValueError):
            return []
        if not isinstance(items, list):
            return []
        return [item for item in items if isinstance(item, dict)]

    def add_batch_item(self, terminal_id: str, item: dict[str, Any]) -> bool:
        now = int(time.time())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT batch_assets_json FROM terminals WHERE terminal_id = ?",
                (terminal_id,),
            ).fetchone()
            if not row:
                return False
            try:
                items = json.loads(row["batch_assets_json"] or "[]")
            except (TypeError, ValueError):
                items = []
            asset_id = int(item["asset"]["id"])
            if any(int(existing["asset"]["id"]) == asset_id for existing in items):
                return False
            items.append(item)
            connection.execute(
                """
                UPDATE terminals SET batch_assets_json = ?, last_activity_at = ?,
                    updated_at = ?
                WHERE terminal_id = ?
                """,
                (json.dumps(items, ensure_ascii=False), now, now, terminal_id),
            )
        return True

    def replace_batch_items(
        self, terminal_id: str, items: list[dict[str, Any]]
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE terminals SET batch_assets_json = ?, last_activity_at = ?,
                    updated_at = ?
                WHERE terminal_id = ?
                """,
                (
                    json.dumps(items, ensure_ascii=False) if items else None,
                    int(time.time()),
                    int(time.time()),
                    terminal_id,
                ),
            )

    def remove_batch_item(
        self, terminal_id: str, asset_id: int
    ) -> dict[str, Any] | None:
        now = int(time.time())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT batch_assets_json FROM terminals WHERE terminal_id = ?",
                (terminal_id,),
            ).fetchone()
            if not row:
                return None
            try:
                items = json.loads(row["batch_assets_json"] or "[]")
            except (TypeError, ValueError):
                items = []
            removed = None
            remaining = []
            for item in items:
                try:
                    matches = int(item["asset"]["id"]) == int(asset_id)
                except (TypeError, ValueError, KeyError):
                    matches = False
                if removed is None and matches:
                    removed = item
                else:
                    remaining.append(item)
            if removed is None:
                return None
            connection.execute(
                """
                UPDATE terminals SET batch_assets_json = ?, last_activity_at = ?,
                    updated_at = ?
                WHERE terminal_id = ?
                """,
                (
                    json.dumps(remaining, ensure_ascii=False) if remaining else None,
                    now,
                    now,
                    terminal_id,
                ),
            )
        return removed

    def clear_batch_items(self, terminal_id: str) -> None:
        self.replace_batch_items(terminal_id, [])

    def set_pending(
        self,
        terminal_id: str,
        asset: dict[str, Any],
        scan_value: str,
        match_fields: list[str],
        target_user_id: int | None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE terminals
                SET pending_asset_json = ?, pending_scan = ?,
                    pending_match_fields = ?, pending_target_user_id = ?,
                    last_activity_at = ?, updated_at = ?
                WHERE terminal_id = ?
                """,
                (
                    json.dumps(asset, ensure_ascii=False),
                    scan_value,
                    ", ".join(match_fields),
                    target_user_id,
                    int(time.time()),
                    int(time.time()),
                    terminal_id,
                ),
            )

    def get_pending(self, terminal_id: str) -> dict[str, Any] | None:
        terminal = self.get_terminal(terminal_id)
        if not terminal or not terminal["pending_asset_json"]:
            return None
        return {
            "asset": json.loads(terminal["pending_asset_json"]),
            "scan_value": terminal["pending_scan"],
            "match_fields": terminal["pending_match_fields"],
            "target_user_id": terminal["pending_target_user_id"],
        }

    def clear_pending(self, terminal_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE terminals
                SET pending_asset_json = NULL, pending_scan = NULL,
                    pending_match_fields = NULL,
                    pending_target_user_id = NULL, last_activity_at = ?,
                    updated_at = ?
                WHERE terminal_id = ?
                """,
                (int(time.time()), int(time.time()), terminal_id),
            )

    def touch_terminal(self, terminal_id: str) -> None:
        now = int(time.time())
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE terminals SET last_activity_at = ?
                WHERE terminal_id = ? AND is_paired = 1
                """,
                (now, terminal_id),
            )

    def log_event(self, **event: Any) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_log (
                    created_at, terminal_id, operator_name, operator_user_id,
                    operator_email, target_user_id,
                    target_name, scan_value, match_fields, asset_id,
                    asset_tag, action, result, message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(time.time()),
                    event.get("terminal_id"),
                    event.get("operator_name"),
                    event.get("operator_user_id"),
                    event.get("operator_email"),
                    event.get("target_user_id"),
                    event.get("target_name"),
                    event.get("scan_value"),
                    event.get("match_fields"),
                    event.get("asset_id"),
                    event.get("asset_tag"),
                    event.get("action", "unknown"),
                    event.get("result", "unknown"),
                    event.get("message"),
                ),
            )

    @staticmethod
    def _audit_where(
        *,
        operator_user_id: int | None = None,
        operator_email: str = "",
        filters: dict[str, Any] | None = None,
    ) -> tuple[str, list[Any]]:
        conditions: list[str] = []
        parameters: list[Any] = []
        normalized_email = operator_email.strip().casefold()
        if operator_user_id is not None and normalized_email:
            conditions.append(
                "(operator_user_id = ? OR "
                "(operator_user_id IS NULL AND "
                "LOWER(COALESCE(operator_email, '')) = ?))"
            )
            parameters.extend((int(operator_user_id), normalized_email))
        elif operator_user_id is not None:
            conditions.append("operator_user_id = ?")
            parameters.append(int(operator_user_id))
        elif normalized_email:
            conditions.append("LOWER(COALESCE(operator_email, '')) = ?")
            parameters.append(normalized_email)

        active_filters = filters or {}
        if active_filters.get("created_from") is not None:
            conditions.append("created_at >= ?")
            parameters.append(int(active_filters["created_from"]))
        if active_filters.get("created_to") is not None:
            conditions.append("created_at < ?")
            parameters.append(int(active_filters["created_to"]))
        for field in ("result", "action"):
            value = str(active_filters.get(field) or "").strip()
            if value:
                conditions.append(f"{field} = ?")
                parameters.append(value)

        def add_text_filter(value_key: str, columns: tuple[str, ...]) -> None:
            value = str(active_filters.get(value_key) or "").strip().casefold()
            if not value:
                return
            escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            expressions = [
                f"LOWER(COALESCE({column}, '')) LIKE ? ESCAPE '\\'"
                for column in columns
            ]
            conditions.append("(" + " OR ".join(expressions) + ")")
            parameters.extend([f"%{escaped}%"] * len(columns))

        add_text_filter("asset", ("asset_tag", "scan_value"))
        add_text_filter("target", ("target_name",))
        add_text_filter("operator", ("operator_name", "operator_email"))
        add_text_filter("message", ("message",))
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        return where, parameters

    def list_audit_logs(
        self,
        *,
        limit: int | None = 25,
        offset: int = 0,
        operator_user_id: int | None = None,
        operator_email: str = "",
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        where, parameters = self._audit_where(
            operator_user_id=operator_user_id,
            operator_email=operator_email,
            filters=filters,
        )
        with self._connect() as connection:
            total = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM audit_log{where}", parameters
                ).fetchone()[0]
            )
            query = f"SELECT * FROM audit_log{where} ORDER BY id DESC"
            query_parameters = list(parameters)
            if limit is not None:
                query += " LIMIT ? OFFSET ?"
                query_parameters.extend((max(1, int(limit)), max(0, int(offset))))
            rows = connection.execute(
                query, query_parameters
            ).fetchall()
        return [dict(row) for row in rows], total

    def audit_filter_options(
        self,
        *,
        operator_user_id: int | None = None,
        operator_email: str = "",
    ) -> dict[str, list[str]]:
        where, parameters = self._audit_where(
            operator_user_id=operator_user_id,
            operator_email=operator_email,
        )
        output: dict[str, list[str]] = {}
        with self._connect() as connection:
            for field in ("result", "action"):
                rows = connection.execute(
                    f"SELECT DISTINCT {field} FROM audit_log{where} "
                    f"AND {field} IS NOT NULL "
                    if where
                    else f"SELECT DISTINCT {field} FROM audit_log "
                    f"WHERE {field} IS NOT NULL ",
                    parameters,
                ).fetchall()
                output[field] = sorted(
                    str(row[0]) for row in rows if str(row[0] or "").strip()
                )
        return output

    def recent_logs(self, limit: int = 100) -> list[dict[str, Any]]:
        rows, _ = self.list_audit_logs(limit=limit)
        return rows
