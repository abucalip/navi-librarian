"""Versioned schema migrations driven by ``PRAGMA user_version``.

Each migration is applied in its own transaction together with its version bump, so
a failure leaves the database at the previous version. A database written by a newer
server is refused rather than guessed at. Migrations are append-only: never edit a
released one, add the next version.
"""
from __future__ import annotations

import sqlite3
from typing import NamedTuple

EVIDENCE_CLASSES = ("source_explicit", "library_tag", "user_confirmed", "derived", "inferred")
MATCH_QUALITIES = ("exact_mbid", "isrc", "fuzzy_confirmed", "fuzzy_unconfirmed", "unresolved")
ENTITY_TYPES = (
    "artist", "person", "group", "recording", "work", "release",
    "release_group", "label", "area", "place", "series", "genre",
)
UNRESOLVED_STATUSES = ("open", "user_confirmed", "user_rejected")
JOB_STATES = ("queued", "running", "succeeded", "failed", "cancelled")


class MigrationError(RuntimeError):
    """The database cannot be brought to the version this code expects."""


class Migration(NamedTuple):
    version: int
    name: str
    statements: tuple[str, ...]


def _in(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


_V1 = (
    f"""
    CREATE TABLE observations (
        id INTEGER PRIMARY KEY,
        source TEXT NOT NULL,
        entity_hint TEXT,
        payload_hash TEXT NOT NULL,
        payload TEXT NOT NULL,
        fetched_at REAL NOT NULL,
        expires_at REAL,
        generation INTEGER NOT NULL DEFAULT 1,
        UNIQUE (source, payload_hash)
    )
    """,
    # Observations are append-only: rows are never edited (docs/ServerV2.md 6.2).
    """
    CREATE TRIGGER observations_no_update BEFORE UPDATE ON observations
    BEGIN SELECT RAISE(ABORT, 'observations are append-only'); END
    """,
    f"""
    CREATE TABLE entities (
        id INTEGER PRIMARY KEY,
        type TEXT NOT NULL CHECK (type IN ({_in(ENTITY_TYPES)})),
        mbid TEXT,
        navidrome_id TEXT,
        discogs_id TEXT,
        wikidata_id TEXT,
        canonical_name TEXT NOT NULL,
        sort_name TEXT,
        owned INTEGER NOT NULL DEFAULT 0 CHECK (owned IN (0, 1)),
        created_generation INTEGER NOT NULL DEFAULT 1
    )
    """,
    "CREATE UNIQUE INDEX entities_mbid ON entities (type, mbid) WHERE mbid IS NOT NULL",
    "CREATE UNIQUE INDEX entities_navidrome ON entities (type, navidrome_id) WHERE navidrome_id IS NOT NULL",
    "CREATE INDEX entities_name ON entities (type, canonical_name)",
    """
    CREATE TABLE entity_aliases (
        entity_id INTEGER NOT NULL REFERENCES entities (id) ON DELETE CASCADE,
        alias TEXT NOT NULL,
        kind TEXT NOT NULL DEFAULT 'alias',
        PRIMARY KEY (entity_id, alias, kind)
    )
    """,
    "CREATE INDEX entity_aliases_alias ON entity_aliases (alias)",
    f"""
    CREATE TABLE edges (
        id INTEGER PRIMARY KEY,
        from_id INTEGER NOT NULL REFERENCES entities (id) ON DELETE CASCADE,
        to_id INTEGER NOT NULL REFERENCES entities (id) ON DELETE CASCADE,
        relation TEXT NOT NULL,
        role TEXT,
        evidence_class TEXT NOT NULL CHECK (evidence_class IN ({_in(EVIDENCE_CLASSES)})),
        match_quality TEXT NOT NULL CHECK (match_quality IN ({_in(MATCH_QUALITIES)})),
        source TEXT NOT NULL,
        source_url TEXT,
        observation_id INTEGER REFERENCES observations (id),
        valid_from TEXT,
        valid_to TEXT,
        generation INTEGER NOT NULL DEFAULT 1
    )
    """,
    # One edge per (endpoints, relation, role, source, generation); role NULL counts as one value.
    """
    CREATE UNIQUE INDEX edges_unique ON edges
        (from_id, to_id, relation, COALESCE(role, ''), source, generation)
    """,
    "CREATE INDEX edges_from ON edges (from_id, relation)",
    "CREATE INDEX edges_to ON edges (to_id, relation)",
    f"""
    CREATE TABLE unresolved (
        id INTEGER PRIMARY KEY,
        kind TEXT NOT NULL,
        navidrome_ref TEXT NOT NULL,
        candidates_json TEXT NOT NULL DEFAULT '[]',
        reason TEXT NOT NULL,
        first_seen REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ({_in(UNRESOLVED_STATUSES)})),
        UNIQUE (kind, navidrome_ref)
    )
    """,
    """
    CREATE TABLE insights (
        id INTEGER PRIMARY KEY,
        kind TEXT NOT NULL,
        subject_id INTEGER REFERENCES entities (id) ON DELETE CASCADE,
        payload TEXT NOT NULL,
        reasons_json TEXT NOT NULL DEFAULT '[]',
        generation INTEGER NOT NULL,
        computed_at REAL NOT NULL,
        dismissed_state TEXT
    )
    """,
    "CREATE INDEX insights_kind ON insights (kind, generation)",
    """
    CREATE TABLE snapshots (
        period TEXT PRIMARY KEY,
        taken_at REAL NOT NULL,
        metrics_json TEXT NOT NULL
    )
    """,
    f"""
    CREATE TABLE job_runs (
        id INTEGER PRIMARY KEY,
        job TEXT NOT NULL,
        entity_scope TEXT NOT NULL DEFAULT '',
        generation INTEGER NOT NULL DEFAULT 1,
        state TEXT NOT NULL CHECK (state IN ({_in(JOB_STATES)})),
        progress TEXT,
        started_at REAL,
        finished_at REAL,
        error TEXT
    )
    """,
    # Duplicate prevention: at most one queued or running run per job and scope.
    """
    CREATE UNIQUE INDEX job_runs_active ON job_runs (job, entity_scope)
        WHERE state IN ('queued', 'running')
    """,
    # Key/value for data_version counters and the current derivation generation.
    """
    CREATE TABLE meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """,
    "INSERT INTO meta (key, value) VALUES ('generation', '1')",
)

MIGRATIONS: tuple[Migration, ...] = (Migration(1, "initial schema", _V1),)
LATEST_VERSION = MIGRATIONS[-1].version

assert [m.version for m in MIGRATIONS] == list(range(1, LATEST_VERSION + 1)), "versions must be contiguous"


def current_version(db: sqlite3.Connection) -> int:
    return int(db.execute("PRAGMA user_version").fetchone()[0])


def migrate(db: sqlite3.Connection) -> int:
    """Apply pending migrations in order and return the resulting version."""
    version = current_version(db)
    if version > LATEST_VERSION:
        raise MigrationError(
            f"database is at version {version}, newer than this server supports ({LATEST_VERSION})"
        )
    for migration in MIGRATIONS[version:]:
        _apply(db, migration)
    return current_version(db)


def _apply(db: sqlite3.Connection, migration: Migration) -> None:
    # Python's sqlite3 does not open transactions before DDL, so manage one explicitly.
    previous_isolation = db.isolation_level
    db.isolation_level = None
    try:
        db.execute("BEGIN IMMEDIATE")
        try:
            # Another process may have migrated while this one waited for the lock.
            if current_version(db) >= migration.version:
                db.execute("ROLLBACK")
                return
            for statement in migration.statements:
                db.execute(statement)
            db.execute(f"PRAGMA user_version = {int(migration.version)}")
            db.execute("COMMIT")
        except BaseException as exc:
            if db.in_transaction:
                db.execute("ROLLBACK")
            if isinstance(exc, sqlite3.Error):
                raise MigrationError(f"migration {migration.version} ({migration.name}) failed: {exc}") from exc
            raise
    finally:
        db.isolation_level = previous_isolation
