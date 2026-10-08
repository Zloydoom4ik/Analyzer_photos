"""Postgres access: the scanned pictures and the duplicate groups found among them."""
import psycopg
from psycopg.rows import dict_row

from . import config


def connect():
    return psycopg.connect(**config.DB, autocommit=True, row_factory=dict_row)


def ensure_schema(conn):
    conn.execute(config.SCHEMA_FILE.read_text(encoding="utf-8"))


def known_files(conn):
    """Per file path: its size, modification time and sha256 as stored at the last scan."""
    rows = conn.execute("SELECT path, bytes, modified_at, sha256 FROM images").fetchall()
    return {row["path"]: row for row in rows}


def upsert_image(conn, path, place, name, modified_at, fingerprint):
    conn.execute(
        """
        INSERT INTO images (path, place, name, modified_at, bytes, width, height, sha256, phash)
        VALUES (%(path)s, %(place)s, %(name)s, %(modified_at)s, %(bytes)s, %(width)s, %(height)s,
                %(sha256)s, %(phash)s)
        ON CONFLICT (path) DO UPDATE SET
            place = EXCLUDED.place, name = EXCLUDED.name, modified_at = EXCLUDED.modified_at,
            bytes = EXCLUDED.bytes, width = EXCLUDED.width, height = EXCLUDED.height,
            sha256 = EXCLUDED.sha256, phash = EXCLUDED.phash, scanned_at = now()
        """,
        {"path": path, "place": place, "name": name, "modified_at": modified_at, **fingerprint},
    )


def delete_images_except(conn, paths):
    """Forget every file that is not in the folder being scanned now; return how many were forgotten."""
    return conn.execute("DELETE FROM images WHERE NOT (path = ANY(%s))", (paths,)).rowcount


def all_images(conn):
    return conn.execute("SELECT * FROM images ORDER BY place, name").fetchall()


def save_groups(conn, groups):
    """Replace the stored duplicate groups. `groups` is a list of {"level", "members"}; ids are 1, 2, 3..."""
    with conn.transaction():
        conn.execute("UPDATE images SET group_id = NULL WHERE group_id IS NOT NULL")
        conn.execute("DELETE FROM duplicate_groups")
        for group_id, group in enumerate(groups, 1):
            members = group["members"]
            conn.execute(
                "INSERT INTO duplicate_groups (id, level, images, places) VALUES (%s, %s, %s, %s)",
                (group_id, group["level"], len(members), len({m["place"] for m in members})),
            )
            conn.execute("UPDATE images SET group_id = %s WHERE id = ANY(%s)",
                         (group_id, [m["id"] for m in members]))
