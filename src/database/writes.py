import logging
import sqlite3
from asyncio import coroutine

from src.database.queries import delete_comment_by_id, get_comments_by_id
from src.database.queries import get_claim_ids_from_comment_ids
from src.database.queries import get_comment_or_none
from src.database.queries import hide_comments_by_id
from src.database.queries import insert_channel
from src.database.queries import insert_comment
from server.validation import is_valid_channel, is_valid_base_comment, is_valid_credential_input, \
    validate_signature_from_claim
from src.server.misc import get_claim_from_id
from server.external import send_notifications, send_notification

logger = logging.getLogger(__name__)


def create_comment_or_error(conn, comment, claim_id, channel_id=None, channel_name=None,
                            signature=None, signing_ts=None, parent_id=None) -> dict:
    if channel_id or channel_name or signature or signing_ts:
        insert_channel_or_error(conn, channel_name, channel_id)
    comment_id = insert_comment(
        conn=conn,
        comment=comment,
        claim_id=claim_id,
        channel_id=channel_id,
        signature=signature,
        parent_id=parent_id,
        signing_ts=signing_ts
    )
    return get_comment_or_none(conn, comment_id)


def insert_channel_or_error(conn: sqlite3.Connection, channel_name: str, channel_id: str):
    try:
        is_valid_channel(channel_id, channel_name)
        insert_channel(conn, channel_name, channel_id)
    except AssertionError:
        logger.exception('Invalid channel values given')
        raise ValueError('Received invalid values for channel_id or channel_name')


""" COROUTINE WRAPPERS """


async def write_comment(app, params):  # CREATE
    return await coroutine(create_comment_or_error)(app['writer'], **params)


async def hide_comments(app, comment_ids):  # UPDATE
    return await coroutine(hide_comments_by_id)(app['writer'], comment_ids)


async def abandon_comment(app, comment_id):  # DELETE
    return await coroutine(delete_comment_by_id)(app['writer'], comment_id)


""" Core Functions called by request handlers """


async def create_comment(app, params):
    if is_valid_base_comment(**params) and is_valid_credential_input(**params):
        job = await app['comment_scheduler'].spawn(write_comment(app, params))
        comment = await job.wait()
        if comment:
            await app['webhooks'].spawn(
                send_notification(app, 'CREATE', comment)
            )
        return comment
    else:
        raise ValueError('base comment is invalid')


async def hide_comments_where_authorized(app, pieces: list) -> list:
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
            comments_to_hide.append(p)

    comment_ids = [c['comment_id'] for c in comments_to_hide]
    job = await app['comment_scheduler'].spawn(hide_comments(app, comment_ids))
    await app['webhooks'].spawn(
        send_notifications(
            app, 'UPDATE', get_comments_by_id(app['reader'], comment_ids)
        )
    )

    await job.wait()
    return comment_ids


async def edit_comment(app, comment_id, new_comment, channel_id,
                       channel_name, new_signature, new_signing_ts):

    pass


async def abandon_comment_if_authorized(app, comment_id, channel_id, signature, signing_ts, **kwargs):
    channel = await get_claim_from_id(app, channel_id)
    if not validate_signature_from_claim(channel, signature, signing_ts, comment_id):
        return False

    comment = get_comment_or_none(app['reader'], comment_id)
    job = await app['comment_scheduler'].spawn(abandon_comment(app, comment_id))
    await app['webhooks'].spawn(send_notification(app, 'DELETE', comment))
    return await job.wait()
