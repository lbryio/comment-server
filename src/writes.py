import logging
import sqlite3

from src.database import get_comment_or_none
from src.database import insert_comment
from src.database import insert_channel
from src.misc import validate_channel
from src.misc import validate_signature

logger = logging.getLogger(__name__)


def create_comment_or_error(conn: sqlite3.Connection, comment: str, claim_id: str, channel_id: str = None,
                            channel_name: str = None, signature: str = None, signing_ts: str = None, parent_id: str = None):
    if channel_id or channel_name or signature or signing_ts:
        validate_signature(signature, signing_ts, comment, channel_name, channel_id)
        insert_channel_or_error(conn, channel_name, channel_id)
    try:
        comment_id = insert_comment(
            conn=conn, comment=comment, claim_id=claim_id, channel_id=channel_id,
            signature=signature, parent_id=parent_id, signing_ts=signing_ts
        )
        return get_comment_or_none(conn, comment_id)
    except sqlite3.IntegrityError as ie:
        logger.exception(ie)


def insert_channel_or_error(conn: sqlite3.Connection, channel_name: str, channel_id: str):
    try:
        validate_channel(channel_id, channel_name)
        insert_channel(conn, channel_name, channel_id)
    except AssertionError as ae:
        logger.exception('Invalid channel values given: %s', ae)
        raise ValueError('Received invalid values for channel_id or channel_name')
