import logging
import re
import sqlite3
import time
import typing

import aiosqlite
import nacl.hash

from src.settings import config

logger = logging.getLogger(__name__)


def obtain_connection(filepath: str = None, row_factory: bool = True):
    connection = sqlite3.connect(filepath)
    if row_factory:
        connection.row_factory = sqlite3.Row
    return connection


def get_claim_comments(conn: sqlite3.Connection, claim_id: str, parent_id: str = None,
                       page: int = 1, page_size: int = 50, top_level=False):
    if top_level:
        return [dict(row) for row in conn.execute(
            """ SELECT * 
                FROM COMMENTS_ON_CLAIMS 
                WHERE claim_id LIKE ? AND parent_id IS NULL
                LIMIT ? OFFSET ? """,
            (claim_id, page_size, page_size*(page - 1))
        )]
    elif parent_id is None:
        return [dict(row) for row in conn.execute(
            """ SELECT * 
                FROM COMMENTS_ON_CLAIMS WHERE claim_id LIKE ? 
                LIMIT ? OFFSET ? """,
            (claim_id, page_size, page_size*(page - 1))
        )]
    else:
        return [dict(row) for row in conn.execute(
            """ SELECT *
                FROM COMMENTS_ON_CLAIMS 
                WHERE claim_id LIKE ? AND parent_id = ?
                LIMIT ? OFFSET ? """,
            (claim_id, parent_id, page_size, page_size*(page - 1))
        )]


def validate_input(**kwargs):
    assert 0 < len(kwargs['comment']) <= 2000
    assert re.fullmatch(
        '[a-z0-9]{40}:([a-z0-9]{40})?',
        kwargs['claim_id'] + ':' + kwargs.get('channel_id', '')
    )
    if 'channel_name' in kwargs:
        assert re.fullmatch(
            '^@(?:(?![\x00-\x08\x0b\x0c\x0e-\x1f\x23-\x26'
            '\x2f\x3a\x3d\x3f-\x40\uFFFE-\U0000FFFF]).){1,255}$',
            kwargs['channel_name']
        )


def _insert_channel(conn: sqlite3.Connection, channel_name: str, channel_id: str):
    with conn:
        conn.execute(
            'INSERT INTO CHANNEL(ClaimId, Name)  VALUES (?, ?)',
            (channel_id, channel_name)
        )


def _insert_comment(conn: sqlite3.Connection, claim_id: str = None, comment: str = None,
                    channel_id: str = None, signature: str = None, parent_id: str = None) -> str:
    timestamp = time.time_ns()
    comment_prehash = ':'.join((claim_id, comment, str(timestamp),))
    comment_prehash = bytes(comment_prehash.encode('utf-8'))
    comment_id = nacl.hash.sha256(comment_prehash).decode('utf-8')
    with conn:
        conn.execute(
            """
            INSERT INTO COMMENT(CommentId, LbryClaimId, ChannelId, Body, 
                                            ParentId, Signature, Timestamp) 
            VALUES (?, ?, ?, ?, ?, ?, ?) 
            """,
            (comment_id, claim_id, channel_id, comment, parent_id, signature, timestamp)
        )
    logger.debug('Inserted Comment into DB, `comment_id`: %s', comment_id)
    return comment_id


def create_comment(conn: sqlite3.Connection, comment: str, claim_id: str, **kwargs) -> typing.Union[dict, None]:
    channel_id = kwargs.pop('channel_id', '')
    channel_name = kwargs.pop('channel_name', '')
    if channel_id or channel_name:
        try:
            validate_input(
                comment=comment,
                claim_id=claim_id,
                channel_id=channel_id,
                channel_name=channel_name,
            )
            _insert_channel(conn, channel_name, channel_id)
        except AssertionError:
            logger.exception('Received invalid input')
            return None
    else:
        channel_id = config['ANONYMOUS']['CHANNEL_ID']
    comment_id = _insert_comment(
        conn=conn, comment=comment, claim_id=claim_id, channel_id=channel_id, **kwargs
    )
    curry = conn.execute(
        'SELECT * FROM COMMENTS_ON_CLAIMS WHERE comment_id = ?', (comment_id,)
    )
    thing = curry.fetchone()
    return dict(thing) if thing else None


def get_comment_ids(conn: sqlite3.Connection, claim_id: str, parent_id: str = None, page=1, page_size=50):
    """ Just return a list of the comment IDs that are associated with the given claim_id.
    If get_all is specified then it returns all the IDs, otherwise only the IDs at that level.
    if parent_id is left null then it only returns the top level comments.

    For pagination the parameters are:
        get_all XOR (page_size + page)
    """
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
    return [dict(row) for row in conn.execute(
        f'SELECT * FROM COMMENTS_ON_CLAIMS WHERE comment_id IN ({placeholders})',
        tuple(comment_ids)
    )]


async def _insert_channel_async(db_file: str, channel_name: str, channel_id: str):
    async with aiosqlite.connect(db_file) as db:
        await db.execute('INSERT INTO CHANNEL(ClaimId, Name) VALUES (?, ?)',
                         (channel_id, channel_name))
        await db.commit()


async def _insert_comment_async(db_file: str, claim_id: str = None, comment: str = None,
                                channel_id: str = None, signature: str = None, parent_id: str = None) -> str:
    timestamp = time.time_ns()
    comment_prehash = ':'.join((claim_id, comment, str(timestamp),))
    comment_prehash = bytes(comment_prehash.encode('utf-8'))
    comment_id = nacl.hash.sha256(comment_prehash).decode('utf-8')
    async with aiosqlite.connect(db_file) as db:
        await db.execute(
            """
            INSERT INTO COMMENT(CommentId, LbryClaimId, ChannelId, Body, 
                                            ParentId, Signature, Timestamp) 
            VALUES (?, ?, ?, ?, ?, ?, ?) 
            """,
            (comment_id, claim_id, channel_id, comment, parent_id, signature, timestamp)
        )
        await db.commit()
    return comment_id


async def create_comment_async(db_file: str, comment: str, claim_id: str, **kwargs):
    channel_id = kwargs.pop('channel_id', '')
    channel_name = kwargs.pop('channel_name', '')
    if channel_id or channel_name:
        try:
            validate_input(
                comment=comment,
                claim_id=claim_id,
                channel_id=channel_id,
                channel_name=channel_name,
            )
            await _insert_channel_async(db_file, channel_name, channel_id)
        except AssertionError:
            return None
    else:
        channel_id = config['ANONYMOUS']['CHANNEL_ID']
    comment_id = await _insert_comment_async(
        db_file=db_file, comment=comment, claim_id=claim_id, channel_id=channel_id, **kwargs
    )
    async with aiosqlite.connect(db_file) as db:
        db.row_factory = aiosqlite.Row
        curs = await db.execute(
            'SELECT * FROM COMMENTS_ON_CLAIMS WHERE comment_id = ?', (comment_id,)
        )
        thing = await curs.fetchone()
        await curs.close()
        return dict(thing) if thing else None


if __name__ == '__main__':
    pass
    # __generate_database_schema(connection, 'comments_ddl.sql')
