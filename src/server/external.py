import logging
from json import JSONDecodeError
from typing import List

import aiohttp
from aiohttp import ClientConnectorError


logger = logging.getLogger(__name__)


async def send_notifications(app, action: str, comments: List[dict]):
    events = create_notification_batch(action, comments)
    async with aiohttp.ClientSession() as session:
        for event in events:
            event.update(auth_token=app['config']['notifications']['auth_token'])
            try:
                async with session.get(app['config']['notifications']['url'], params=event) as resp:
                    logger.debug(f'Completed Notification: {await resp.text()}, HTTP Status: {resp.status}')
            except Exception:
                logger.exception(f'Error requesting internal API, Status {resp.status}: {resp.text()}, '
                                 f'comment_id: {event["comment_id"]}')


async def send_notification(app, action: str, comment: dict):
    await send_notifications(app, action, [comment])


def create_notification_batch(action: str, comments: List[dict]) -> List[dict]:
    action_type = action[0].capitalize()  # to turn Create -> C, edit -> U, delete -> D
    events = []
    for comment in comments:
        event = {
            'action_type': action_type,
            'comment_id': comment['comment_id'],
            'claim_id': comment['claim_id']
        }
        if comment.get('channel_id'):
            event['channel_id'] = comment['channel_id']
        if comment.get('parent_id'):
            event['parent_id'] = comment['parent_id']
        if comment.get('comment'):
            event['comment'] = comment['comment']
        events.append(event)
    return events


async def request_lbrynet(app, method, **params):
    body = {'method': method, 'params': {**params}}
    try:
        async with aiohttp.request('POST', app['config']['lbrynet'], json=body) as req:
            try:
                resp = await req.json()
            except JSONDecodeError as jde:
                logger.exception(jde.msg)
                raise Exception('JSON Decode Error In lbrynet request')
            finally:
                if 'result' in resp:
                    return resp['result']
                raise ValueError('LBRYNET Request Error', {'error': resp['error']})
    except (ConnectionRefusedError, ClientConnectorError):
        logger.critical("Connection to the LBRYnet daemon failed, make sure it's running.")
        raise Exception("Server cannot verify delete signature")