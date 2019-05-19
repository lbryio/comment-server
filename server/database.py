import sqlite3
import typing
import re
import nacl.hash
import time
from server.conf import *


def validate_input(**kwargs):
    assert 0 < len(kwargs['comment']) <= 2000
    assert re.fullmatch(
        '[a-z0-9]{40}:([a-z0-9]{40})?',
        kwargs['claim_id'] + ':' + kwargs.get('channel_id', '')
    )
    if 'channel_name' in kwargs:
        assert re.fullmatch(
            '^@{1}(?:(?![\x00-\x08\x0b\x0c\x0e-\x1f\x23-\x26'
            '\x2f\x3a\x3d\x3f-\x40\uFFFE-\U0000FFFF]).){1,255}$',
            kwargs['channel_name']
        )


class DatabaseConnection:

    def obtain_connection(self):
        self.connection = sqlite3.connect(self.filepath)
        if self.row_factory:
            self.connection.row_factory = sqlite3.Row
    
    def __init__(self, filepath: str, row_factory: bool = True):
        self.filepath = filepath
        self.row_factory = row_factory
        self.connection = None

    def generate_schema(self, filepath: str):
        with open(filepath, 'r') as ddl_file:
            self.connection.executescript(ddl_file.read())

    def get_claim_comments(self, claim_id: str,
                           parent_id: str = None,
                           page: int = 1,
                           page_size: int = 50,
                           top_level: bool = False, **kwargs):
        if top_level:
            curs = self.connection.execute(
                """ SELECT * 
                    FROM COMMENTS_ON_CLAIMS 
                    WHERE claim_id LIKE ? AND parent_id IS NULL
                    LIMIT ? OFFSET ? """,
                (claim_id, page_size, page_size*(page - 1))
            )
        elif parent_id is None:
            curs = self.connection.execute(
                """ SELECT * 
                    FROM COMMENTS_ON_CLAIMS WHERE claim_id LIKE ? 
                    LIMIT ? OFFSET ? """,
                (claim_id, page_size, page_size*(page - 1))
            )
        else:
            curs = self.connection.execute(
                """ SELECT *
                    FROM COMMENTS_ON_CLAIMS 
                    WHERE claim_id LIKE ? AND parent_id = ?
                    LIMIT ? OFFSET ? """,
                (claim_id, parent_id, page_size, page_size*(page - 1))
            )
        return [dict(row) for row in curs.fetchall()]

    def _insert_channel(self, channel_name, channel_id, *args, **kwargs):
        with self.connection:
            self.connection.execute(
                'INSERT INTO CHANNEL(ClaimId, Name)  VALUES (?, ?)',
                (channel_id, channel_name)
            )

    def _insert_comment(self, claim_id: str = None, comment: str = None,
                        channel_id: str = None, sig: str = None,
                        parent_id: str = None, **kwargs):
        timestamp = time.time_ns()
        comment_prehash = ':'.join((claim_id, comment, str(timestamp),))
        comment_prehash = bytes(comment_prehash.encode('utf-8'))
        comment_id = nacl.hash.sha256(comment_prehash).decode('utf-8')
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO COMMENT(CommentId, LbryClaimId, ChannelId, Body, 
                                                ParentId, Signature, Timestamp) 
                VALUES (?, ?, ?, ?, ?, ?, ?) 
                """,
                (comment_id, claim_id, channel_id, comment, parent_id, sig, timestamp)
            )
        return comment_id

    def create_comment(self, comment: str, claim_id: str, channel_name: str = None,
                       channel_id: str = None, **kwargs) -> dict:
        thing = None
        try:
            validate_input(
                comment=comment,
                claim_id=claim_id,
                channel_id=channel_id,
                channel_name=channel_name,
            )
            if channel_id and channel_name:
                self._insert_channel(channel_name, channel_id)
            else:
                channel_id = anonymous['channel_id']
            comcast_id = self._insert_comment(
                comment=comment,
                claim_id=claim_id,
                channel_id=channel_id,
                **kwargs
            )
            curry = self.connection.execute(
                'SELECT * FROM COMMENTS_ON_CLAIMS WHERE comment_id = ?', (comcast_id,)
            )
            thing = curry.fetchone()
        except AssertionError as e:
            print(e)
        finally:
            return dict(thing) if thing else None




    def get_comment_ids(self, claim_id: str, parent_id: str = None, page=1, page_size=50):
        """ Just return a list of the comment IDs that are associated with the given claim_id.
        If get_all is specified then it returns all the IDs, otherwise only the IDs at that level.
        if parent_id is left null then it only returns the top level comments.

        For pagination the parameters are:
            get_all XOR (page_size + page)
        """
        if parent_id is None:
            curs = self.connection.execute("""
                    SELECT comment_id FROM COMMENTS_ON_CLAIMS
                    WHERE claim_id LIKE ? AND parent_id IS NULL LIMIT ? OFFSET ?
                """, (claim_id, page_size, page_size*abs(page - 1),)
                                      )
        else:
            curs = self.connection.execute("""
                    SELECT comment_id FROM COMMENTS_ON_CLAIMS
                    WHERE claim_id LIKE ? AND parent_id LIKE ? LIMIT ? OFFSET ?
                """, (claim_id, parent_id, page_size, page_size * abs(page - 1),)
                                      )
        return [tuple(row) for row in curs.fetchall()]

    def get_comments_by_id(self, comment_ids: list) -> typing.Union[list, None]:
        """ Returns a list containing the comment data associated with each ID within the list"""
        placeholders = ', '.join('?' for _ in comment_ids)
        curs = self.connection.execute(
            f'SELECT * FROM COMMENTS_ON_CLAIMS WHERE comment_id IN ({placeholders})',
            comment_ids
        )
        return [dict(row) for row in curs.fetchall()]


if __name__ == '__main__':
    pass
    # __generate_database_schema(connection, 'comments_ddl.sql')
