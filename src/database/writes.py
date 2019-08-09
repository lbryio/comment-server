import logging
import sqlite3

from asyncio import coroutine

from src.database.queries import delete_comment_by_id
from src.database.queries import get_comment_or_none
from src.database.queries import insert_comment
from src.database.queries import insert_channel
from src.database.queries import get_channel_id_from_comment_id
from src.database.queries import hide_comment_by_id
from src.server.misc import is_authentic_delete_signal
from src.server.misc import request_lbrynet
from src.server.misc import validate_signature_from_claim
from src.server.misc import channel_matches_pattern_or_error

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


async def delete_comment_if_authorized(app, comment_id, **kwargs):
    authorized = await is_authentic_delete_signal(app, comment_id, **kwargs)
    if not authorized:
        return {'deleted': False}

    job = await app['comment_scheduler'].spawn(delete_comment(app, comment_id))
    return {'deleted': await job.wait()}


async def write_comment(app, params):
    return await coroutine(create_comment_or_error)(app['writer'], **params)


async def hide_comment(app, comment_id):
    return await coroutine(hide_comment_by_id)(app['writer'], comment_id)

async def claim_search(app, **kwargs):
    return (await request_lbrynet(app, 'claim_search', **kwargs))['items'][0]

# comment_ids: [
#   {
#       "comment_id": id,
#       "signing_ts": signing_ts,
#       "signature": signature
#   },
#   ...
# ]
async def hide_comment_if_authorized(app, comment_id, signing_ts, signature):
    channel = get_channel_id_from_comment_id(app['reader'], comment_id)
    claim = await request_lbrynet(app, 'claim_search', claim_id=channel['channel_id'])
    claim = claim['items'][0]
    if not validate_signature_from_claim(claim, signature, signing_ts, comment_id):
        raise ValueError('Invalid Signature')

    job = await app['comment_scheduler'].spawn(hide_comment(app, comment_id))
    return {
        'hidden': await job.wait()
    }
