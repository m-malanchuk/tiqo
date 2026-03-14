"""Apply numbered SQL migrations from the migrations/ directory."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

_MIGRATION_NAME = re.compile(r"^(\d+)_.*\.sql$")


def default_migrations_dir() -> Path:
    packaged = Path(__file__).resolve().parents[1] / "migrations"
    if packaged.is_dir():
        return packaged
    # Editable source tree fallback.
    return Path(__file__).resolve().parents[2] / "migrations"


def current_version(conn: sqlite3.Connection) -> int:
    _ensure_version_table(conn)
    row = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()
    return int(row[0])


def apply_migrations(
    conn: sqlite3.Connection,
    migrations_dir: Path | None = None,
) -> int:
    """Apply pending `NNN_name.sql` files. Returns the resulting schema version."""
    directory = migrations_dir or default_migrations_dir()
    _ensure_version_table(conn)
    applied = current_version(conn)

    for version, path in _discover_migrations(directory):
        if version <= applied:
            continue
        sql = path.read_text(encoding="utf-8")
        script = (
            "BEGIN IMMEDIATE;\n"
            f"{sql}\n"
            f"INSERT INTO schema_version (version) VALUES ({version});\n"
            "COMMIT;"
        )
        try:
            conn.executescript(script)
        except BaseException:
            conn.rollback()
            raise
        applied = version

    return applied


def _ensure_version_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY
        )
        """
    )


def _discover_migrations(directory: Path) -> list[tuple[int, Path]]:
    found: list[tuple[int, Path]] = []
    if not directory.is_dir():
        raise FileNotFoundError(f"Migrations directory not found: {directory}")

    for path in sorted(directory.iterdir()):
        match = _MIGRATION_NAME.match(path.name)
        if match is None:
            continue
        found.append((int(match.group(1)), path))

    versions = [version for version, _ in found]
    if len(versions) != len(set(versions)):
        raise ValueError(f"Duplicate migration versions in {directory}")
    return found
