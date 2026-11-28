"""Immutable radio previews and durable one-time playlist save intents."""

import json
from uuid import uuid4


def create_preview(db, target_key, payload, now):
    preview_id = uuid4().hex
    with db:
        # Bound unused previews; retain all uncertain and completed save intents.
        db.execute(
            "DELETE FROM radio_mix_previews WHERE id IN ("
            "SELECT id FROM radio_mix_previews WHERE target_key = ? AND save_songs IS NULL "
            "ORDER BY created_at DESC, rowid DESC LIMIT -1 OFFSET 49)", (target_key,),
        )
        db.execute(
            "INSERT INTO radio_mix_previews (id, target_key, created_at, payload) VALUES (?, ?, ?, ?)",
            (preview_id, target_key, now, json.dumps(payload, allow_nan=False)),
        )
    return preview_id


def get_preview(db, preview_id, target_key):
    row = db.execute("SELECT * FROM radio_mix_previews WHERE id = ? AND target_key = ?",
                     (preview_id, target_key)).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["payload"] = json.loads(result["payload"])
    selection = None if result["save_songs"] is None else json.loads(result["save_songs"])
    result["save_songs"] = tuple(selection["song_ids"]) if selection is not None else None
    result["save_positions"] = tuple(selection["positions"]) if selection is not None else None
    return result


def record_save(db, preview_id, *, songs=None, positions=None, playlist_id=None, saved=False):
    with db:
        if songs is not None:
            db.execute("UPDATE radio_mix_previews SET save_songs = ? WHERE id = ?",
                       (json.dumps({"song_ids": songs, "positions": positions}), preview_id))
        if playlist_id is not None:
            db.execute("UPDATE radio_mix_previews SET playlist_id = ?, saved = ? WHERE id = ?",
                       (playlist_id, int(saved), preview_id))
