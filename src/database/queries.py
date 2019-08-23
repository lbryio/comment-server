import atexit
import logging
import sqlite3
import time
import typing

import math
import nacl.hash

from src.database.schema import CREATE_TABLES_QUERY

logger = logging.getLogger(__name__)


SELECT_COMMENTS_ON_CLAIMS = """
    SELECT comment, comment_id, channel_name, channel_id, channel_url,
        timestamp, signature, signing_ts, parent_id, is_hidden
    FROM COMMENTS_ON_CLAIMS 
"""

SELECT_COMMENTS_ON_CLAIMS_CLAIMID = """
    SELECT comment, comment_id, claim_id, channel_name, channel_id, channel_url,
        timestamp, signature, signing_ts, parent_id, is_hidden
    FROM COMMENTS_ON_CLAIMS 
"""


def clean(thing: dict) -> dict:
    if 'is_hidden' in thing:
        thing.update({'is_hidden': bool(thing['is_hidden'])})
    return {k: v for k, v in thing.items() if v is not None}


def obtain_connection(filepath: str = None, row_factory: bool = True):
    connection = sqlite3.connect(filepath)
    if row_factory:
        connection.row_factory = sqlite3.Row
    return connection


def get_claim_comments(conn: sqlite3.Connection, claim_id: str, parent_id: str = None,
                       page: int = 1, page_size: int = 50, top_level=False):
    with conn:
        if top_level:
            results = [clean(dict(row)) for row in conn.execute(
                SELECT_COMMENTS_ON_CLAIMS + " WHERE claim_id = ? AND parent_id IS NULL LIMIT ? OFFSET ?",
                (claim_id, page_size, page_size * (page - 1))
            )]
            count = conn.execute(
                "SELECT COUNT(*) FROM COMMENTS_ON_CLAIMS WHERE claim_id = ? AND parent_id IS NULL",
                (claim_id,)
            )
        elif parent_id is None:
            results = [clean(dict(row)) for row in conn.execute(
                SELECT_COMMENTS_ON_CLAIMS + "WHERE claim_id = ? LIMIT ? OFFSET ? ",
                (claim_id, page_size, page_size * (page - 1))
            )]
            count = conn.execute(
                "SELECT COUNT(*) FROM COMMENTS_ON_CLAIMS WHERE claim_id = ?",
                (claim_id,)
            )
        else:
            results = [clean(dict(row)) for row in conn.execute(
                SELECT_COMMENTS_ON_CLAIMS + "WHERE claim_id = ? AND parent_id = ? LIMIT ? OFFSET ? ",
                (claim_id, parent_id, page_size, page_size * (page - 1))
            )]
            count = conn.execute(
                "SELECT COUNT(*) FROM COMMENTS_ON_CLAIMS WHERE claim_id = ? AND parent_id = ?",
                (claim_id, parent_id)
            )
        count = tuple(count.fetchone())[0]
        return {
            'items': results,
            'page': page,
            'page_size': page_size,
            'total_pages': math.ceil(count / page_size),
            'total_items': count,
            'has_hidden_comments': claim_has_hidden_comments(conn, claim_id)
        }


def get_claim_hidden_comments(conn: sqlite3.Connection, claim_id: str, hidden=True, page=1, page_size=50):
    with conn:
        results = conn.execute(
            SELECT_COMMENTS_ON_CLAIMS + "WHERE claim_id = ? AND is_hidden IS ? LIMIT ? OFFSET ?",
            (claim_id, hidden, page_size, page_size * (page - 1))
        )
        count = conn.execute(
            "SELECT COUNT(*) FROM COMMENTS_ON_CLAIMS WHERE claim_id = ? AND is_hidden IS ?", (claim_id, hidden)
        )
    results = [clean(dict(row)) for row in results.fetchall()]
    count = tuple(count.fetchone())[0]

    return {
        'items': results,
        'page': page,
        'page_size': page_size,
        'total_pages': math.ceil(count/page_size),
        'total_items': count,
        'has_hidden_comments': claim_has_hidden_comments(conn, claim_id)
    }


def claim_has_hidden_comments(conn, claim_id):
    with conn:
        result = conn.execute(
            "SELECT COUNT(DISTINCT is_hidden) FROM COMMENTS_ON_CLAIMS WHERE claim_id = ? AND is_hidden IS 1",
            (claim_id,)
        )
        return bool(tuple(result.fetchone())[0])


def insert_comment(conn: sqlite3.Connection, claim_id: str, comment: str, parent_id: str = None,
                   channel_id: str = None, signature: str = None, signing_ts: str = None) -> str:
    timestamp = int(time.time())
    prehash = b':'.join((claim_id.encode(), comment.encode(), str(timestamp).encode(),))
    comment_id = nacl.hash.sha256(prehash).decode()
    with conn:
        conn.execute(
            """
            INSERT INTO COMMENT(CommentId, LbryClaimId, ChannelId, Body, ParentId, Timestamp, Signature, SigningTs) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?) 
            """,
            (comment_id, claim_id, channel_id, comment, parent_id, timestamp, signature, signing_ts)
        )
    logger.info('Inserted Comment into DB, `comment_id`: %s', comment_id)
    return comment_id


def get_comment_or_none(conn: sqlite3.Connection, comment_id: str) -> dict:
    with conn:
        curry = conn.execute(SELECT_COMMENTS_ON_CLAIMS_CLAIMID + "WHERE comment_id = ?", (comment_id,))
        thing = curry.fetchone()
        return clean(dict(thing)) if thing else None


def get_comment_ids(conn: sqlite3.Connection, claim_id: str, parent_id: str = None, page=1, page_size=50):
    """ Just return a list of the comment IDs that are associated with the given claim_id.
    If get_all is specified then it returns all the IDs, otherwise only the IDs at that level.
    if parent_id is left null then it only returns the top level comments.

    For pagination the parameters are:
        get_all XOR (page_size + page)
    """
    with conn:
        if parent_id is None:
            curs = conn.execute("""
                    SELECT comment_id FROM COMMENTS_ON_CLAIMS
                    WHERE claim_id = ? AND parent_id IS NULL LIMIT ? OFFSET ?
                """, (claim_id, page_size, page_size*abs(page - 1),)
                                           )
        else:
            curs = conn.execute("""
                    SELECT comment_id FROM COMMENTS_ON_CLAIMS
                    WHERE claim_id = ? AND parent_id = ? LIMIT ? OFFSET ?
                """, (claim_id, parent_id, page_size, page_size * abs(page - 1),)
                                           )
    return [tuple(row)[0] for row in curs.fetchall()]


def get_comments_by_id(conn, comment_ids: typing.Union[list, tuple]) -> typing.Union[list, None]:
    """ Returns a list containing the comment data associated with each ID within the list"""
    # format the input, under the assumption that the
    placeholders = ', '.join('?' for _ in comment_ids)
    with conn:
        return [clean(dict(row)) for row in conn.execute(
            SELECT_COMMENTS_ON_CLAIMS_CLAIMID + f'WHERE comment_id IN ({placeholders})',
            tuple(comment_ids)
        )]


def delete_comment_by_id(conn: sqlite3.Connection, comment_id: str):
    with conn:
        curs = conn.execute("DELETE FROM COMMENT WHERE CommentId = ?", (comment_id,))
        return bool(curs.rowcount)


def insert_channel(conn: sqlite3.Connection, channel_name: str, channel_id: str):
    with conn:
        curs = conn.execute('INSERT INTO CHANNEL(ClaimId, Name)  VALUES (?, ?)', (channel_id, channel_name))
        return bool(curs.rowcount)


def get_channel_id_from_comment_id(conn: sqlite3.Connection, comment_id: str):
    with conn:
        channel = conn.execute(
            "SELECT channel_id, channel_name FROM COMMENTS_ON_CLAIMS WHERE comment_id = ?", (comment_id,)
        ).fetchone()
        return dict(channel) if channel else {}


def get_claim_ids_from_comment_ids(conn: sqlite3.Connection, comment_ids: list):
    with conn:
        cids = conn.execute(
            f""" SELECT  CommentId as comment_id, LbryClaimId AS claim_id FROM COMMENT 
            WHERE CommentId IN ({', '.join('?' for _ in comment_ids)}) """,
            tuple(comment_ids)
        )
        return {row['comment_id']: row['claim_id'] for row in cids.fetchall()}


def hide_comments_by_id(conn: sqlite3.Connection, comment_ids: list):
    with conn:
        curs = conn.cursor()
        curs.executemany(
            "UPDATE COMMENT SET IsHidden = 1 WHERE CommentId = ?",
            [[c] for c in comment_ids]
        )
        return bool(curs.rowcount)


class DatabaseWriter(object):
    _writer = None

    def __init__(self, db_file):
        if not DatabaseWriter._writer:
            self.conn = obtain_connection(db_file)
            DatabaseWriter._writer = self
            atexit.register(self.cleanup)
            logging.info('Database writer has been created at %s', repr(self))
        else:
            logging.warning('Someone attempted to insantiate DatabaseWriter')
            raise TypeError('Database Writer already exists!')

    def cleanup(self):
        logging.info('Cleaning up database writer')
        self.conn.close()
        DatabaseWriter._writer = None

    @property
    def connection(self):
        return self.conn


def setup_database(db_path):
    with sqlite3.connect(db_path) as conn:
        conn.executescript(CREATE_TABLES_QUERY)


def backup_database(conn: sqlite3.Connection, back_fp):
    with sqlite3.connect(back_fp) as back:
        conn.backup(back)
