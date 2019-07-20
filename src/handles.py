# cython: language_level=3
import logging

import asyncio
from aiohttp import web
from aiojobs.aiohttp import atomic
from asyncio import coroutine

from misc import clean_input_params
from src.database import get_claim_comments
from src.database import get_comments_by_id, get_comment_ids
from src.database import get_channel_from_comment_id
from src.database import obtain_connection
from src.database import delete_comment_by_id
from src.writes import create_comment_or_error
from src.misc import is_authentic_delete_signal

logger = logging.getLogger(__name__)


# noinspection PyUnusedLocal
def ping(*args):
    return 'pong'


def handle_get_channel_from_comment_id(app, kwargs: dict):
    with obtain_connection(app['db_path']) as conn:
        return get_channel_from_comment_id(conn, **kwargs)


def handle_get_comment_ids(app, kwargs):
    with obtain_connection(app['db_path']) as conn:
        return get_comment_ids(conn, **kwargs)


def handle_get_claim_comments(app, kwargs):
    with obtain_connection(app['db_path']) as conn:
        return get_claim_comments(conn, **kwargs)


def handle_get_comments_by_id(app, kwargs):
    with obtain_connection(app['db_path']) as conn:
        return get_comments_by_id(conn, **kwargs)


async def write_comment(app, comment):
    return await coroutine(create_comment_or_error)(app['writer'], **comment)


async def delete_comment(app, comment_id):
    return await coroutine(delete_comment_by_id)(app['writer'], comment_id)


async def handle_create_comment(app, params):
    job = await app['comment_scheduler'].spawn(write_comment(app, params))
    return await job.wait()


async def delete_comment_if_authorized(app, comment_id, channel_name, channel_id, signature):
    authorized = await is_authentic_delete_signal(app, comment_id, channel_name, channel_id, signature)
    if not authorized:
        return {'deleted': False}

    job = await app['comment_scheduler'].spawn(delete_comment(app, comment_id))
    return {'deleted': await job.wait()}


async def handle_delete_comment(app, params):
    return await delete_comment_if_authorized(app, **params)


METHODS = {
    'ping': ping,
    'get_claim_comments': handle_get_claim_comments,
    'get_comment_ids': handle_get_comment_ids,
    'get_comments_by_id': handle_get_comments_by_id,
    'get_channel_from_comment_id': handle_get_channel_from_comment_id,
    'create_comment': handle_create_comment,
    'delete_comment': handle_delete_comment,
    'abandon_comment': handle_delete_comment,
}


async def process_json(app, body: dict) -> dict:
    response = {'jsonrpc': '2.0', 'id': body['id']}
    if body['method'] in METHODS:
        method = body['method']
        params = body.get('params', {})
        clean_input_params(params)
        logger.debug(f'Received Method {method}, params: {params}')
        try:
            if asyncio.iscoroutinefunction(METHODS[method]):
                result = await METHODS[method](app, params)
            else:
                result = METHODS[method](app, params)
            response['result'] = result
        except Exception as err:
            logger.exception(f'Got {type(err).__name__}: {err}')
            if type(err) in (ValueError, TypeError):
                response['error'] = make_error('INVALID_PARAMS', err)
            else:
                response['error'] = make_error('INTERNAL', err)
    else:
        response['error'] = ERRORS['METHOD_NOT_FOUND']
    return response


@atomic
async def api_endpoint(request: web.Request):
    try:
        body = await request.json()
        if type(body) is list or type(body) is dict:
            if type(body) is list:
                # for batching
                return web.json_response(
                    [await process_json(request.app, part) for part in body]
                )
            else:
                return web.json_response(await process_json(request.app, body))
        else:
            logger.warning('Got invalid request from %s: %s', request.remote, body)
            return web.json_response({'error': ERRORS['INVALID_REQUEST']})
    except json.decoder.JSONDecodeError as jde:
        logger.exception('Received malformed JSON from %s: %s', request.remote, jde.msg)
        logger.debug('Request headers: %s', request.headers)
        return web.json_response({
            'error': ERRORS['PARSE_ERROR']
        })
    except Exception as e:
        logger.exception(f'Exception raised by request from {request.remote}: {e}')
        logger.debug(f'Request headers: {request.headers}')
        return make_error('INVALID_REQUEST', e)
