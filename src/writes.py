import logging
import sqlite3

from src.database import get_comment_or_none
from src.database import insert_comment
from src.database import insert_channel
from src.misc import channel_matches_pattern

logger = logging.getLogger(__name__)


def create_comment_or_error(conn, comment, claim_id, channel_id=None, channel_name=None,
                            signature=None, signing_ts=None, parent_id=None) -> dict:
    if channel_id or channel_name or signature or signing_ts:
        # validate_signature(signature, signing_ts, comment, channel_name, channel_id)
        insert_channel_or_error(conn, channel_name, channel_id)
    comment_id = insert_comment(
        conn=conn, comment=comment, claim_id=claim_id, channel_id=channel_id,
        signature=signature, parent_id=parent_id, signing_ts=signing_ts
    )
    return get_comment_or_none(conn, comment_id)


def insert_channel_or_error(conn: sqlite3.Connection, channel_name: str, channel_id: str):
    try:
        channel_matches_pattern(channel_id, channel_name)
        insert_channel(conn, channel_name, channel_id)
    except AssertionError as ae:
        logger.exception('Invalid channel values given: %s', ae)
        raise ValueError('Received invalid values for channel_id or channel_name')
