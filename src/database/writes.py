import logging
import sqlite3
from asyncio import coroutine

from src.server.validation import is_valid_channel
from src.server.validation import is_valid_base_comment
from src.server.validation import is_valid_credential_input
from src.server.validation import validate_signature_from_claim
from src.server.validation import body_is_valid
from src.server.misc import get_claim_from_id
from src.server.external import send_notifications
from src.server.external import send_notification
import src.database.queries as db


logger = logging.getLogger(__name__)


def create_comment_or_error(conn, comment, claim_id=None, channel_id=None, channel_name=None,
                            signature=None, signing_ts=None, parent_id=None) -> dict:
    if channel_id and channel_name:
        insert_channel_or_error(conn, channel_name, channel_id)
    fn = db.insert_comment if parent_id is None else db.insert_reply
    comment_id = fn(
        conn=conn,
        comment=comment,
        claim_id=claim_id,
        channel_id=channel_id,
        signature=signature,
        parent_id=parent_id,
        signing_ts=signing_ts
    )
    return db.get_comment_or_none(conn, comment_id)


def insert_channel_or_error(conn: sqlite3.Connection, channel_name: str, channel_id: str):
    try:
        is_valid_channel(channel_id, channel_name)
        db.insert_channel(conn, channel_name, channel_id)
    except AssertionError:
        logger.exception('Invalid channel values given')
        raise ValueError('Received invalid values for channel_id or channel_name')


""" COROUTINE WRAPPERS """


async def _create_comment(app, params):  # CREATE
    return await coroutine(create_comment_or_error)(app['writer'], **params)


async def _hide_comments(app, comment_ids):  # UPDATE
    return await coroutine(db.hide_comments_by_id)(app['writer'], comment_ids)


async def _edit_comment(**params):
    return await coroutine(db.edit_comment_by_id)(**params)


async def _abandon_comment(app, comment_id):  # DELETE
    return await coroutine(db.delete_comment_by_id)(app['writer'], comment_id)


""" Core Functions called by request handlers """


async def create_comment(app, params):
    if is_valid_base_comment(**params) and is_valid_credential_input(**params):
        job = await app['comment_scheduler'].spawn(_create_comment(app, params))
        comment = await job.wait()
        if comment:
            await app['webhooks'].spawn(
                send_notification(app, 'CREATE', comment)
            )
        return comment
    else:
        raise ValueError('base comment is invalid')


async def hide_comments(app, pieces: list) -> list:
    comment_cids = db.get_claim_ids_from_comment_ids(
        conn=app['reader'],
        comment_ids=[p['comment_id'] for p in pieces]
    )
    # TODO: Amortize this process
    claims = {}
    comments_to_hide = []
    for p in pieces:
        claim_id = comment_cids[p['comment_id']]
        if claim_id not in claims:
            claim = await get_claim_from_id(app, claim_id)
            if claim:
                claims[claim_id] = claim

        channel = claims[claim_id].get('signing_channel')
        if validate_signature_from_claim(channel, p['signature'], p['signing_ts'], p['comment_id']):
            comments_to_hide.append(p)

    comment_ids = [c['comment_id'] for c in comments_to_hide]
    job = await app['comment_scheduler'].spawn(_hide_comments(app, comment_ids))
    await app['webhooks'].spawn(
        send_notifications(
            app, 'UPDATE', db.get_comments_by_id(app['reader'], comment_ids)
        )
    )
    await job.wait()
    return comment_ids


async def edit_comment(app, comment_id: str, comment: str, channel_id: str,
                       channel_name: str, signature: str, signing_ts: str):
    if not(is_valid_credential_input(channel_id, channel_name, signature, signing_ts)
            and body_is_valid(comment)):
        logging.error('Invalid argument values, check input and try again')
        return

    cmnt = db.get_comment_or_none(app['reader'], comment_id)
    if not(cmnt and 'channel_id' in cmnt and cmnt['channel_id'] == channel_id.lower()):
        logging.error("comment doesnt exist")
        return

    channel = await get_claim_from_id(app, channel_id)
    if not validate_signature_from_claim(channel, signature, signing_ts, comment):
        logging.error("signature could not be validated")
        return

    job = await app['comment_scheduler'].spawn(_edit_comment(
        conn=app['writer'],
        comment_id=comment_id,
        signature=signature,
        signing_ts=signing_ts,
        comment=comment
    ))

    return await job.wait()


async def abandon_comment(app, comment_id, channel_id, signature, signing_ts, **kwargs):
    channel = await get_claim_from_id(app, channel_id)
    if not validate_signature_from_claim(channel, signature, signing_ts, comment_id):
        return False

    comment = db.get_comment_or_none(app['reader'], comment_id)
    job = await app['comment_scheduler'].spawn(_abandon_comment(app, comment_id))
    await app['webhooks'].spawn(send_notification(app, 'DELETE', comment))
    return await job.wait()
