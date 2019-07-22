import logging
import sqlite3

from asyncio import coroutine

from src.database import delete_comment_by_id
from src.misc import is_authentic_delete_signal

from src.database import get_comment_or_none
from src.database import insert_comment
from src.database import insert_channel
from src.misc import channel_matches_pattern_or_error

logger = logging.getLogger(__name__)


def create_comment_or_error(conn, comment, claim_id, channel_id=None, channel_name=None,
                            signature=None, signing_ts=None, parent_id=None) -> dict:
    if channel_id or channel_name or signature or signing_ts:
        insert_channel_or_error(conn, channel_name, channel_id)
    comment_id = insert_comment(
        conn=conn, comment=comment, claim_id=claim_id, channel_id=channel_id,
        signature=signature, parent_id=parent_id, signing_ts=signing_ts
    )
    return get_comment_or_none(conn, comment_id)


def insert_channel_or_error(conn: sqlite3.Connection, channel_name: str, channel_id: str):
    try:
        channel_matches_pattern_or_error(channel_id, channel_name)
        insert_channel(conn, channel_name, channel_id)
    except AssertionError:
        logger.exception('Invalid channel values given')
        raise ValueError('Received invalid values for channel_id or channel_name')


async def delete_comment(app, comment_id):
    return await coroutine(delete_comment_by_id)(app['writer'], comment_id)


async def delete_comment_if_authorized(app, comment_id, channel_name, channel_id, signature):
    authorized = await is_authentic_delete_signal(app, comment_id, channel_name, channel_id, signature)
    if not authorized:
        return {'deleted': False}

    job = await app['comment_scheduler'].spawn(delete_comment(app, comment_id))
    return {'deleted': await job.wait()}


async def write_comment(app, comment):
    return await coroutine(create_comment_or_error)(app['writer'], **comment)
