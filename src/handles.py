# cython: language_level=3
import json
import logging

import aiojobs
import asyncio
from aiohttp import web
from aiojobs.aiohttp import atomic
from asyncio import coroutine

from src.database import DatabaseWriter
from src.database import get_claim_comments
from src.database import get_comments_by_id, get_comment_ids
from src.database import obtain_connection
from src.writes import create_comment_or_error

logger = logging.getLogger(__name__)

ERRORS = {
    'INVALID_PARAMS': {'code': -32602, 'message': 'Invalid parameters'},
    'INTERNAL': {'code': -32603, 'message': 'An internal error'},
    'UNKNOWN': {'code': -1, 'message': 'An unknown or very miscellaneous error'},
}

ID_LIST = {'claim_id', 'parent_id', 'comment_id', 'channel_id'}


def ping(*args, **kwargs):
    return 'pong'


def handle_get_comment_ids(app, kwargs):
    with obtain_connection(app['db_path']) as conn:
        return get_comment_ids(conn, **kwargs)


def handle_get_claim_comments(app, kwargs):
    with obtain_connection(app['db_path']) as conn:
        return get_claim_comments(conn, **kwargs)


def handle_get_comments_by_id(app, kwargs):
    with obtain_connection(app['db_path']) as conn:
        return get_comments_by_id(conn, **kwargs)


async def create_comment_scheduler():
    return await aiojobs.create_scheduler(limit=1, pending_limit=0)


async def write_comment(comment):
    with DatabaseWriter._writer.connection as conn:
        return await coroutine(create_comment_or_error)(conn, **comment)


async def handle_create_comment(scheduler, comment):
    job = await scheduler.spawn(write_comment(comment))
    return await job.wait()


METHODS = {
    'ping': ping,
    'get_claim_comments': handle_get_claim_comments,
    'get_comment_ids': handle_get_comment_ids,
    'get_comments_by_id': handle_get_comments_by_id,
    'create_comment': handle_create_comment
}


def clean_input_params(kwargs: dict):
    for k, v in kwargs.items():
        if type(v) is str:
            kwargs[k] = v.strip()
            if k in ID_LIST:
                kwargs[k] = v.lower()


async def process_json(app, body: dict) -> dict:
    response = {'jsonrpc': '2.0', 'id': body['id']}
    if body['method'] in METHODS:
        method = body['method']
        params = body.get('params', {})
        clean_input_params(params)
        try:
            if asyncio.iscoroutinefunction(METHODS[method]):
                result = await METHODS[method](app['comment_scheduler'], params)
            else:
                result = METHODS[method](app, params)
            response['result'] = result
        except TypeError as te:
            logger.exception('Got TypeError: %s', te)
            response['error'] = ERRORS['INVALID_PARAMS']
        except ValueError as ve:
            logger.exception('Got ValueError: %s', ve)
            response['error'] = ERRORS['INVALID_PARAMS']
    else:
        response['error'] = ERRORS['UNKNOWN']
    return response


@atomic
async def api_endpoint(request: web.Request):
    try:
        logger.info('Received POST request from %s', request.remote)
        body = await request.json()
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
