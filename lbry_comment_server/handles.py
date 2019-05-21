import json
import asyncio
from aiojobs.aiohttp import atomic
from aiohttp import web
import logging
from lbry_comment_server.database import obtain_connection
from lbry_comment_server import get_claim_comments
from lbry_comment_server import get_comments_by_id, get_comment_ids
import lbry_comment_server.writes as writes


logger = logging.getLogger(__name__)

ERRORS = {
    'INVALID_PARAMS': {'code': -32602, 'message': 'Invalid parameters'},
    'INTERNAL': {'code': -32603, 'message': 'An internal error'},
    'UNKNOWN': {'code': -1, 'message': 'An unknown or very miscellaneous error'},
}


def ping(*args):
    return 'pong'


def handle_get_comment_ids(app, **kwargs):
    with obtain_connection(app['db_path']) as conn:
        return get_comment_ids(conn, **kwargs)


def handle_get_claim_comments(app, **kwargs):
    with obtain_connection(app['db_path']) as conn:
        return get_claim_comments(conn, **kwargs)


def handle_get_comments_by_id(app, **kwargs):
    with obtain_connection(app['db_path']) as conn:
        return get_comments_by_id(conn, **kwargs)


async def handle_create_comment(scheduler, **kwargs):
    job = await scheduler.spawn(writes.write_comment(**kwargs))
    return await job.wait()


METHODS = {
    'ping': ping,
    'get_claim_comments': handle_get_claim_comments,
    'get_comment_ids': handle_get_comment_ids,
    'get_comments_by_id': handle_get_comments_by_id,
    'create_comment': handle_create_comment
}


async def process_json(app, body: dict) -> dict:
    response = {'jsonrpc': '2.0', 'id': body['id']}
    if body['method'] in METHODS:
        method = body['method']
        params = body.get('params', {})
        try:
            if asyncio.iscoroutinefunction(METHODS[method]):
                result = await METHODS[method](app['comment_scheduler'], **params)
            else:
                result = METHODS[method](app, **params)
            response['result'] = result
        except TypeError as te:
            logger.exception('Got TypeError: %s', te)
            response['error'] = ERRORS['INVALID_PARAMS']
    else:
        response['error'] = ERRORS['UNKNOWN']
    return response


@atomic
async def api_endpoint(request: web.Request):
    try:
        body = await request.json()
        logger.info('Received POST request from %s', request.remote)
        if type(body) is list or type(body) is dict:
            if type(body) is list:
                return web.json_response(
                    [await process_json(request.app, part) for part in body]
                )
            else:
                return web.json_response(await process_json(request.app, body))
        else:
            return web.json_response({'error': ERRORS['UNKNOWN']})
    except json.decoder.JSONDecodeError as jde:
        logger.exception('Received malformed JSON from %s: %s', request.remote, jde.msg)
        logger.debug('Request headers: %s', request.headers)
        return web.json_response({
            'error': {'message': jde.msg, 'code': -1}
        })




