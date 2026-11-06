"""Column layouts of the dump tables the slice reads.

The dump's tab-separated files carry no header, so the column order must be pinned here.
It was taken from ``admin/sql/CreateTables.sql`` in musicbrainz-server for schema
sequence 31. A dump with another sequence is refused (see ``dump.check_schema``), because
a silently shifted column would put wrong credits in front of the owner.
"""
from __future__ import annotations

EXPECTED_SCHEMA_SEQUENCE = 31

_LINK = ("id", "link", "entity0", "entity1", "edits_pending", "last_updated",
         "link_order", "entity0_credit", "entity1_credit")

TABLES: dict[str, tuple[str, ...]] = {
    "area": ("id", "gid", "name", "type", "edits_pending", "last_updated",
             "begin_date_year", "begin_date_month", "begin_date_day",
             "end_date_year", "end_date_month", "end_date_day", "ended", "comment"),
    "artist": ("id", "gid", "name", "sort_name",
               "begin_date_year", "begin_date_month", "begin_date_day",
               "end_date_year", "end_date_month", "end_date_day",
               "type", "area", "gender", "comment", "edits_pending", "last_updated",
               "ended", "begin_area", "end_area"),
    "artist_credit": ("id", "name", "artist_count", "ref_count", "created", "edits_pending", "gid"),
    "artist_credit_name": ("artist_credit", "position", "artist", "name", "join_phrase"),
    "label": ("id", "gid", "name",
              "begin_date_year", "begin_date_month", "begin_date_day",
              "end_date_year", "end_date_month", "end_date_day",
              "label_code", "type", "area", "comment", "edits_pending", "last_updated", "ended"),
    "link": ("id", "link_type",
             "begin_date_year", "begin_date_month", "begin_date_day",
             "end_date_year", "end_date_month", "end_date_day",
             "attribute_count", "created", "ended"),
    "link_attribute": ("link", "attribute_type", "created"),
    "link_attribute_credit": ("link", "attribute_type", "credited_as"),
    "link_attribute_type": ("id", "parent", "root", "child_order", "gid", "name",
                            "description", "last_updated"),
    "link_type": ("id", "parent", "child_order", "gid", "entity_type0", "entity_type1", "name",
                  "description", "link_phrase", "reverse_link_phrase", "long_link_phrase",
                  "last_updated", "is_deprecated", "has_dates", "entity0_cardinality",
                  "entity1_cardinality"),
    "recording": ("id", "gid", "name", "artist_credit", "length", "comment",
                  "edits_pending", "last_updated", "video"),
    "release": ("id", "gid", "name", "artist_credit", "release_group", "status", "packaging",
                "language", "script", "barcode", "comment", "edits_pending", "quality",
                "last_updated"),
    "release_group": ("id", "gid", "name", "artist_credit", "type", "comment",
                      "edits_pending", "last_updated"),
    "release_label": ("id", "release", "label", "catalog_number", "last_updated"),
    "work": ("id", "gid", "name", "type", "comment", "edits_pending", "last_updated"),
    # Relationship tables: entity0/entity1 are internal ids of the two named entity types.
    "l_artist_artist": _LINK,
    "l_artist_label": _LINK,
    "l_artist_recording": _LINK,
    "l_artist_release": _LINK,
    "l_artist_release_group": _LINK,
    "l_artist_work": _LINK,
    "l_label_release": _LINK,
    "l_recording_work": _LINK,
    "l_work_work": _LINK,
}
