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
_V1_ENTITY_TYPES = (
    "artist", "person", "group", "recording", "work", "release",
    "release_group", "label", "area", "place", "series", "genre",
)
ENTITY_TYPES = _V1_ENTITY_TYPES + ("event",)  # "event" arrives with migration 4
UNRESOLVED_STATUSES = ("open", "user_confirmed", "user_rejected")
JOB_STATES = ("queued", "running", "succeeded", "failed", "cancelled")


class MigrationError(RuntimeError):
    """The database cannot be brought to the version this code expects."""


class Migration(NamedTuple):
    version: int
    name: str
    statements: tuple[str, ...]
    # Rebuilds a table other tables point at (SQLite's documented 12-step change): foreign keys are
    # switched off around the transaction so dropping the old table cascades nothing, and the
    # result is checked with ``foreign_key_check`` before it commits.
    rebuilds_tables: bool = False


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
        type TEXT NOT NULL CHECK (type IN ({_in(_V1_ENTITY_TYPES)})),
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

# Facts the MusicBrainz dump states about one entity, kept beside it rather than in ``edges``.
# Dates are ``YYYY[-MM[-DD]]``; a missing date stays NULL. Re-importing the slice overwrites them.
_V2 = (
    """
    CREATE TABLE artist_life_span (
        entity_id INTEGER PRIMARY KEY REFERENCES entities (id) ON DELETE CASCADE,
        begin_date TEXT,
        end_date TEXT,
        ended INTEGER NOT NULL DEFAULT 0 CHECK (ended IN (0, 1))
    )
    """,
    """
    CREATE TABLE release_facts (
        entity_id INTEGER PRIMARY KEY REFERENCES entities (id) ON DELETE CASCADE,
        date TEXT,
        country TEXT,
        status TEXT
    )
    """,
)

SOURCE_OUTCOMES = ("ok", "not_found", "error", "blocked")

# Freshness ledger (efficiency.md E1 item 3): what the worker last did for one source, operation
# and key, so it can pick what to refresh, back off on failures, and tell "pending" from "absent".
_V3 = (
    f"""
    CREATE TABLE source_state (
        source TEXT NOT NULL,
        operation TEXT NOT NULL,
        key TEXT NOT NULL,
        outcome TEXT NOT NULL CHECK (outcome IN ({_in(SOURCE_OUTCOMES)})),
        observation_id INTEGER REFERENCES observations (id) ON DELETE SET NULL,
        attempts INTEGER NOT NULL DEFAULT 0,
        last_attempt_at REAL NOT NULL,
        next_refresh_at REAL,
        etag TEXT,
        last_modified TEXT,
        PRIMARY KEY (source, operation, key)
    )
    """,
    "CREATE INDEX source_state_due ON source_state (source, operation, next_refresh_at)",
)

# Phase 5 context from the dump (areas, places, events, Wikidata and Discogs ids, aliases, ISRC and ISWC
# codes, release formats and catalogue numbers, artist kind). Which area an entity belongs to, who
# played at an event, and similar relationships are edges, never columns here. Dates are
# ``YYYY[-MM[-DD]]``. Opinions such as community tags are deliberately not stored here.
_V4 = (
    f"""
    CREATE TABLE entities_v4 (
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
    "INSERT INTO entities_v4 SELECT id, type, mbid, navidrome_id, discogs_id, wikidata_id, canonical_name, "
    "sort_name, owned, created_generation FROM entities",
    "DROP TABLE entities",
    "ALTER TABLE entities_v4 RENAME TO entities",
    "CREATE UNIQUE INDEX entities_mbid ON entities (type, mbid) WHERE mbid IS NOT NULL",
    "CREATE UNIQUE INDEX entities_navidrome ON entities (type, navidrome_id) WHERE navidrome_id IS NOT NULL",
    "CREATE INDEX entities_name ON entities (type, canonical_name)",
    """
    CREATE TABLE area_facts (
        entity_id INTEGER PRIMARY KEY REFERENCES entities (id) ON DELETE CASCADE,
        kind TEXT,
        iso_code TEXT
    )
    """,
    """
    CREATE TABLE place_facts (
        entity_id INTEGER PRIMARY KEY REFERENCES entities (id) ON DELETE CASCADE,
        kind TEXT,
        latitude REAL,
        longitude REAL,
        begin_date TEXT,
        end_date TEXT
    )
    """,
    """
    CREATE TABLE event_facts (
        entity_id INTEGER PRIMARY KEY REFERENCES entities (id) ON DELETE CASCADE,
        kind TEXT,
        begin_date TEXT,
        end_date TEXT,
        cancelled INTEGER NOT NULL DEFAULT 0 CHECK (cancelled IN (0, 1))
    )
    """,
    """
    CREATE TABLE artist_facts (
        entity_id INTEGER PRIMARY KEY REFERENCES entities (id) ON DELETE CASCADE,
        kind TEXT
    )
    """,
    """
    CREATE TABLE release_labels (
        release_id INTEGER NOT NULL REFERENCES entities (id) ON DELETE CASCADE,
        label_id INTEGER REFERENCES entities (id) ON DELETE CASCADE,
        catalogue_number TEXT
    )
    """,
    "CREATE UNIQUE INDEX release_labels_unique ON release_labels "
    "(release_id, COALESCE(label_id, 0), COALESCE(catalogue_number, ''))",
    "ALTER TABLE release_facts ADD COLUMN formats TEXT",
    """
    CREATE TABLE entity_identifiers (
        entity_id INTEGER NOT NULL REFERENCES entities (id) ON DELETE CASCADE,
        scheme TEXT NOT NULL CHECK (scheme IN ('isrc', 'iswc')),
        value TEXT NOT NULL,
        PRIMARY KEY (entity_id, scheme, value)
    )
    """,
    "CREATE INDEX entity_identifiers_value ON entity_identifiers (scheme, value)",
)

# Release group type (timeline studio-album filter): MusicBrainz's primary type ("Album", "Single", "EP"...) and secondary
# types ("Live", "Compilation"...), JSON list text, from the dump or from a release lookup.
_V5 = (
    """
    CREATE TABLE release_group_facts (
        entity_id INTEGER PRIMARY KEY REFERENCES entities (id) ON DELETE CASCADE,
        primary_type TEXT,
        secondary_types TEXT NOT NULL DEFAULT '[]'
    )
    """,
)

_V6 = (
    """
    CREATE TABLE update_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL CHECK (subject IN ('artist', 'album')),
        navidrome_id TEXT NOT NULL,
        state TEXT NOT NULL CHECK (state IN ('queued', 'running', 'done', 'failed')),
        requested_at REAL NOT NULL,
        finished_at REAL,
        message TEXT,
        UNIQUE (subject, navidrome_id)
    )
    """,
)

MIGRATIONS: tuple[Migration, ...] = (
    Migration(1, "initial schema", _V1),
    Migration(2, "artist life span and release facts", _V2),
    Migration(3, "source freshness ledger", _V3),
    Migration(4, "context facts and the event entity type", _V4, rebuilds_tables=True),
    Migration(5, "release group types", _V5),
    Migration(6, "manual update requests", _V6),
)
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
    if migration.rebuilds_tables:
        db.execute("PRAGMA foreign_keys = OFF")  # a no-op inside a transaction, so it is set first
    try:
        db.execute("BEGIN IMMEDIATE")
        try:
            # Another process may have migrated while this one waited for the lock.
            if current_version(db) >= migration.version:
                db.execute("ROLLBACK")
                return
            for statement in migration.statements:
                db.execute(statement)
            if migration.rebuilds_tables:
                broken = db.execute("PRAGMA foreign_key_check").fetchall()
                if broken:
                    raise MigrationError(f"migration {migration.version} left {len(broken)} broken references")
            db.execute(f"PRAGMA user_version = {int(migration.version)}")
            db.execute("COMMIT")
        except BaseException as exc:
            if db.in_transaction:
                db.execute("ROLLBACK")
            if isinstance(exc, sqlite3.Error):
                raise MigrationError(f"migration {migration.version} ({migration.name}) failed: {exc}") from exc
            raise
    finally:
        if migration.rebuilds_tables:
            db.execute("PRAGMA foreign_keys = ON")
        db.isolation_level = previous_isolation
