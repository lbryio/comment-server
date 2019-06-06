import logging
import re
import sqlite3
import time
import typing

import math
import nacl.hash

logger = logging.getLogger(__name__)


def clean(thing: dict) -> dict:
    return {k: v for k, v in thing.items() if v}


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
                """ SELECT comment, comment_id, channel_name, channel_id, 
                        channel_url, timestamp, signature, signing_ts, parent_id
                    FROM COMMENTS_ON_CLAIMS 
                    WHERE claim_id LIKE ? AND parent_id IS NULL
                    LIMIT ? OFFSET ? """,
                (claim_id, page_size, page_size*(page - 1))
            )]
            count = conn.execute(
                """
                SELECT COUNT(*)
                FROM COMMENTS_ON_CLAIMS
                WHERE claim_id LIKE ? AND parent_id IS NULL
                """, (claim_id, )
            )
        elif parent_id is None:
            results = [clean(dict(row)) for row in conn.execute(
                """ SELECT comment, comment_id, channel_name, channel_id, 
                        channel_url, timestamp, signature, signing_ts, parent_id
                    FROM COMMENTS_ON_CLAIMS 
                    WHERE claim_id LIKE ? 
                    LIMIT ? OFFSET ? """,
                (claim_id, page_size, page_size*(page - 1))
            )]
            count = conn.execute(
                """
                    SELECT COUNT(*) 
                    FROM COMMENTS_ON_CLAIMS 
                    WHERE claim_id LIKE ? 
                """, (claim_id,)
            )
        else:
            results = [clean(dict(row)) for row in conn.execute(
                """ SELECT comment, comment_id, channel_name, channel_id, 
                        channel_url, timestamp, signature, signing_ts, parent_id
                    FROM COMMENTS_ON_CLAIMS 
                    WHERE claim_id LIKE ? AND parent_id = ?
                    LIMIT ? OFFSET ? """,
                (claim_id, parent_id, page_size, page_size*(page - 1))
            )]
            count = conn.execute(
                """
                    SELECT COUNT(*) 
                    FROM COMMENTS_ON_CLAIMS 
                    WHERE claim_id LIKE ? AND parent_id = ?
                """, (claim_id, parent_id)
            )
        count = tuple(count.fetchone())[0]
        return {
            'items': results,
            'page': page,
            'page_size': page_size,
            'total_pages': math.ceil(count/page_size),
            'total_items': count
        }


def validate_channel(channel_id: str, channel_name: str):
    assert channel_id and channel_name
    assert type(channel_id) is str and type(channel_name) is str
    assert re.fullmatch(
        '^@(?:(?![\x00-\x08\x0b\x0c\x0e-\x1f\x23-\x26'
        '\x2f\x3a\x3d\x3f-\x40\uFFFE-\U0000FFFF]).){1,255}$',
        channel_name
    )
    assert re.fullmatch('[a-z0-9]{40}', channel_id)


def validate_input(comment: str, claim_id: str, **kwargs):
    assert 0 < len(comment) <= 2000
    assert re.fullmatch('[a-z0-9]{40}', claim_id)


def _insert_channel(conn: sqlite3.Connection, channel_name: str, channel_id: str):
    with conn:
        conn.execute(
            'INSERT INTO CHANNEL(ClaimId, Name)  VALUES (?, ?)',
            (channel_id, channel_name)
        )


def insert_channel_or_error(conn: sqlite3.Connection, channel_name: str, channel_id: str):
    try:
        validate_channel(channel_id, channel_name)
        _insert_channel(conn, channel_name, channel_id)
    except AssertionError as ae:
        logger.exception('Invalid channel values given: %s', ae)
        raise ValueError('Received invalid values for channel_id or channel_name')


def _insert_comment(conn: sqlite3.Connection, claim_id: str = None, comment: str = None,
                    channel_id: str = None, signature: str = None, signing_ts: str = None,
                    parent_id: str = None) -> str:
    timestamp = int(time.time())
    prehash = ':'.join((claim_id, comment, str(timestamp),))
    prehash = bytes(prehash.encode('utf-8'))
    comment_id = nacl.hash.sha256(prehash).decode('utf-8')
    with conn:
        conn.execute(
            """
            INSERT INTO COMMENT(CommentId, LbryClaimId, ChannelId, Body, ParentId, Timestamp, Signature, SigningTs) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?) 
            """,
            (comment_id, claim_id, channel_id, comment, parent_id, timestamp, signature, signing_ts)
        )
    logger.debug('Inserted Comment into DB, `comment_id`: %s', comment_id)
    return comment_id


def get_comment_or_none(conn: sqlite3.Connection, comment_id: str) -> dict:
    with conn:
        curry = conn.execute(
            """
            SELECT comment, comment_id, channel_name, channel_id, channel_url, timestamp, signature, signing_ts, parent_id
            FROM COMMENTS_ON_CLAIMS WHERE comment_id = ?
            """,
            (comment_id,)
        )
        thing = curry.fetchone()
        return clean(dict(thing)) if thing else None


def validate_signature(*args, **kwargs):
    pass


def create_comment(conn: sqlite3.Connection, comment: str, claim_id: str, channel_id: str = None,
                   channel_name: str = None, signature: str = None, signing_ts: str = None, parent_id: str = None):
    if channel_id or channel_name or signature or signing_ts:
        validate_signature(signature, signing_ts, comment, channel_name, channel_id)
        insert_channel_or_error(conn, channel_name, channel_id)
    try:
        comment_id = _insert_comment(
            conn=conn, comment=comment, claim_id=claim_id, channel_id=channel_id,
            signature=signature, parent_id=parent_id
        )
        return get_comment_or_none(conn, comment_id)
    except sqlite3.IntegrityError as ie:
        logger.exception(ie)


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
                    WHERE claim_id LIKE ? AND parent_id IS NULL LIMIT ? OFFSET ?
                """, (claim_id, page_size, page_size*abs(page - 1),)
                                           )
        else:
            curs = conn.execute("""
                    SELECT comment_id FROM COMMENTS_ON_CLAIMS
                    WHERE claim_id LIKE ? AND parent_id LIKE ? LIMIT ? OFFSET ?
                """, (claim_id, parent_id, page_size, page_size * abs(page - 1),)
                                           )
    return [tuple(row)[0] for row in curs.fetchall()]


def get_comments_by_id(conn, comment_ids: list) -> typing.Union[list, None]:
    """ Returns a list containing the comment data associated with each ID within the list"""
    # format the input, under the assumption that the
    placeholders = ', '.join('?' for _ in comment_ids)
    with conn:
        return [clean(dict(row)) for row in conn.execute(
            f'SELECT * FROM COMMENTS_ON_CLAIMS WHERE comment_id IN ({placeholders})',
            tuple(comment_ids)
        )]
