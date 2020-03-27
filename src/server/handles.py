import asyncio
import logging
import time

from aiohttp import web
from aiojobs.aiohttp import atomic

import src.database.queries as db
from src.database.writes import abandon_comment, create_comment
from src.database.writes import hide_comments
from src.database.writes import edit_comment
from src.server.misc import clean_input_params
from src.server.errors import make_error, report_error

logger = logging.getLogger(__name__)


# noinspection PyUnusedLocal
def ping(*args):
    return 'pong'


def handle_get_channel_from_comment_id(app, kwargs: dict):
    return db.get_channel_id_from_comment_id(app['reader'], **kwargs)


def handle_get_comment_ids(app, kwargs):
    return db.get_comment_ids(app['reader'], **kwargs)


def handle_get_claim_comments(app, kwargs):
    return db.get_claim_comments(app['reader'], **kwargs)


def handle_get_comments_by_id(app, kwargs):
    return db.get_comments_by_id(app['reader'], **kwargs)


def handle_get_claim_hidden_comments(app, kwargs):
    return db.get_claim_hidden_comments(app['reader'], **kwargs)


async def handle_abandon_comment(app, params):
    return {'abandoned': await abandon_comment(app, **params)}


async def handle_hide_comments(app, params):
    return {'hidden': await hide_comments(app, **params)}


async def handle_edit_comment(app, params):
    if await edit_comment(app, **params):
        return db.get_comment_or_none(app['reader'], params['comment_id'])


METHODS = {
    'ping': ping,
    'get_claim_comments': handle_get_claim_comments,    # this gets used
    'get_claim_hidden_comments': handle_get_claim_hidden_comments,  # this gets used
    'get_comment_ids': handle_get_comment_ids,
    'get_comments_by_id': handle_get_comments_by_id,    # this gets used
    'get_channel_from_comment_id': handle_get_channel_from_comment_id,  # this gets used
    'create_comment': create_comment,   # this gets used
    'delete_comment': handle_abandon_comment,
    'abandon_comment': handle_abandon_comment,  # this gets used
    'hide_comments': handle_hide_comments,  # this gets used
    'edit_comment': handle_edit_comment     # this gets used
}


async def process_json(app, body: dict) -> dict:
    response = {'jsonrpc': '2.0', 'id': body['id']}
    if body['method'] in METHODS:
        method = body['method']
        params = body.get('params', {})
        clean_input_params(params)
        logger.debug(f'Received Method {method}, params: {params}')
        start = time.time()
        try:
            if asyncio.iscoroutinefunction(METHODS[method]):
                result = await METHODS[method](app, params)
            else:
                result = METHODS[method](app, params)
            response['result'] = result
        except Exception as err:
            logger.exception(f'Got {type(err).__name__}:')
            if type(err) in (ValueError, TypeError):  # param error, not too important
                response['error'] = make_error('INVALID_PARAMS', err)
            else:
                response['error'] = make_error('INTERNAL', err)
                await app['webhooks'].spawn(report_error(app, err, body))

        finally:
            end = time.time()
            logger.debug(f'Time taken to process {method}: {end - start} secs')
    else:
        response['error'] = make_error('METHOD_NOT_FOUND')
    return response


@atomic
async def api_endpoint(request: web.Request):
    try:
        web.access_logger.info(f'Forwarded headers: {request.remote}')
        logging.debug(f'Request: {request}')
        for k, v in request.items():
            logging.debug(f'{k}: {v}')

        body = await request.json()
        if type(body) is list or type(body) is dict:
            if type(body) is list:
                # for batching
                return web.json_response(
                    [await process_json(request.app, part) for part in body]
                )
            else:
                return web.json_response(await process_json(request.app, body))
    except Exception as e:
        return make_error('INVALID_REQUEST', e)


async def get_api_endpoint(request: web.Request):
    return web.json_response({
        'text': 'OK',
        'is_running': True,
        'uptime': int(time.time()) - request.app['start_time']
    })
