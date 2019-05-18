import sqlite3
import typing
import re
import nacl.hash
import time

__CONNECTION = sqlite3.connect('example.db')
__CONNECTION.row_factory = sqlite3.Row
# __CONNECTION.execute("""
#    CREATE TABLE IF NOT EXISTS TEST(
#        NAME TEXT  NOT NULL,
#        CONSTRAINT TEST_PK PRIMARY KEY(NAME)
#            ON CONFLICT IGNORE
#    )
#""")


def __generate_database_from_ddl(cursor: sqlite3.Connection, filepath: str):
    with open(filepath, 'r') as ddl_file:
        cursor.executescript(ddl_file.read())
        cursor.close()


def get_claim_comments(claim_id: str, parent_id: str = None,
                       page: int = 1, page_size: int = 50, top_level: bool = False):
    if top_level:
        curs = __CONNECTION.execute(
            """ SELECT * 
                FROM COMMENTS_ON_CLAIMS 
                WHERE claim_id LIKE ? AND parent_id IS NULL
                LIMIT ? OFFSET ? """,
            (claim_id, page_size, page_size*(page - 1))
        )
    elif parent_id is None:
        curs = __CONNECTION.execute(
            """ SELECT * 
                FROM COMMENTS_ON_CLAIMS WHERE claim_id LIKE ? 
                LIMIT ? OFFSET ? """,
            (claim_id, page_size, page_size*(page - 1))
        )
    else:
        curs = __CONNECTION.execute(
            """ SELECT *
                FROM COMMENTS_ON_CLAIMS 
                WHERE claim_id LIKE ? AND parent_id = ?
                LIMIT ? OFFSET ? """,
            (claim_id, parent_id, page_size, page_size*(page - 1))
        )
    return [dict(row) for row in curs.fetchall()]


def _insert_channel(channel_name, channel_id):
    with __CONNECTION:
        __CONNECTION.execute(
            'INSERT INTO CHANNEL(ClaimId, Name)  VALUES (?, ?)',
            (channel_id, channel_name)
        )


def _insert_comment(claim_id: str, message: str, channel_id: str = None,
                    sig: str = None, parent_id: str = None):

    # ensure that we'claim_id and channel_id are the correct format

    timestamp = time.time_ns()
    comment_prehash = bytes(':'.join((claim_id, message, str(timestamp),)))
    comment_id = nacl.hash.sha256(comment_prehash).decode('utf-8')
    with __CONNECTION:
        __CONNECTION.execute(
            """
            INSERT INTO COMMENT(CommentId, LbryClaimId, ChannelId, Body, 
                                            ParentId, Signature, Timestamp) 
            VALUES (?, ?, ?, ?, ?, ?, ?) 
            """,
            (comment_id, claim_id, channel_id, message, parent_id, sig, timestamp)
        )
    return comment_id


def _validate_input(**kwargs):
    assert 0 < len(kwargs.pop('message')) <= 2000
    claim_id = kwargs.pop('claim_id')
    channel_id = kwargs.get('channel_id', '')
    assert re.fullmatch('[a-z0-9]{40}:([a-z0-9]{40})?', claim_id + ':' + channel_id)
    if 'channel_name' in kwargs:
        assert 0 < len(kwargs.pop('channel_name')) < 256


def create_comment(claim_id: str, message: str, channel_name: str = None,
                   channel_id: str = None, reply_to: str = None, sig: str = None) -> dict:
    if channel_id:
        _insert_channel(channel_name, channel_id)
    _validate_input(
        claim_id=claim_id,
        message=message,
        channel_id=channel_id,
        channel_name=channel_name,
    )
    comcast_id = _insert_comment(claim_id, message, channel_id, sig, reply_to)
    curry = __CONNECTION.execute('SELECT * COMMENTS_ON_CLAIMS WHERE comment_id = ?', (comcast_id,))
    thing = curry.fetchone()
    return dict(thing) if thing else None


def get_comment_ids(claim_id: str, parent_id: str = None, page=1, page_size=50):
    """ Just return a list of the comment IDs that are associated with the given claim_id.
    If get_all is specified then it returns all the IDs, otherwise only the IDs at that level.
    if parent_id is left null then it only returns the top level comments.

    For pagination the parameters are:
        get_all XOR (page_size + page)
    """
    if parent_id is None:
        curs = __CONNECTION.execute("""
                SELECT comment_id FROM COMMENTS_ON_CLAIMS
                WHERE claim_id LIKE ? AND parent_id IS NULL LIMIT ? OFFSET ?
            """, (claim_id, page_size, page_size*abs(page - 1),)
    )
    else:
        curs = __CONNECTION.execute("""
                SELECT comment_id FROM COMMENTS_ON_CLAIMS
                WHERE claim_id LIKE ? AND parent_id LIKE ? LIMIT ? OFFSET ?
            """, (claim_id, parent_id, page_size, page_size * abs(page - 1),)
        )
    return [tuple(row) for row in curs.fetchall()]


def get_comments_by_id(comment_ids: list) -> typing.Union[list, None]:
    """ Returns a list containing the comment data associated with each ID within the list"""
    placeholders = ', '.join('?' for _ in comment_ids)
    curs = __CONNECTION.execute(
        f'SELECT * FROM COMMENTS_ON_CLAIMS WHERE comment_id IN ({placeholders})',
        comment_ids
    )
    return [dict(row) for row in curs.fetchall()]


if __name__ == '__main__':
    __generate_database_from_ddl(__CONNECTION, 'comments_ddl.sql')
