import logging
import sqlite3

from asyncio import coroutine

from src.database.queries import hide_comments_by_id
from src.database.queries import delete_comment_by_id
from src.database.queries import get_comment_or_none
from src.database.queries import insert_comment
from src.database.queries import insert_channel
from src.database.queries import get_claim_ids_from_comment_ids
from src.server.misc import validate_signature_from_claim
from src.server.misc import channel_matches_pattern_or_error
from src.server.misc import get_claim_from_id


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


async def abandon_comment(app, comment_id):
    return await coroutine(delete_comment_by_id)(app['writer'], comment_id)


async def abandon_comment_if_authorized(app, comment_id, channel_id, signature, signing_ts, **kwargs):
    claim = await get_claim_from_id(app, channel_id)
    if not validate_signature_from_claim(claim, signature, signing_ts, comment_id):
        return False

    job = await app['comment_scheduler'].spawn(abandon_comment(app, comment_id))
    return await job.wait()


async def write_comment(app, params):
    return await coroutine(create_comment_or_error)(app['writer'], **params)


async def hide_comments(app, comment_ids):
    return await coroutine(hide_comments_by_id)(app['writer'], comment_ids)


async def hide_comments_where_authorized(app, pieces: list):
    comment_cids = get_claim_ids_from_comment_ids(
        conn=app['reader'],
        comment_ids=[p['comment_id'] for p in pieces]
    )
    # TODO: Amortize this process
    claims = {}
    comments_to_hide = []
    for p in pieces:
        claim_id = comment_cids[p['comment_id']]
        if claim_id not in claims:
            claims[claim_id] = await get_claim_from_id(app, claim_id, no_totals=True)
        channel = claims[claim_id].get('signing_channel')
        if validate_signature_from_claim(channel, p['signature'], p['signing_ts'], p['comment_id']):
            comments_to_hide.append(p['comment_id'])

    if comments_to_hide:
        job = await app['comment_scheduler'].spawn(hide_comments(app, comments_to_hide))
        await job.wait()

    return {'hidden': comments_to_hide}
