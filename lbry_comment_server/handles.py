import json
import asyncio
from aiojobs.aiohttp import atomic
from aiohttp import web
from lbry_comment_server import create_comment, get_claim_comments
from lbry_comment_server import  get_comments_by_id, get_comment_ids

ERRORS = {
    'INVALID_PARAMS': {'code': -32602, 'message': 'Invalid parameters'},
    'INTERNAL': {'code': -32603, 'message': 'An internal error'},
    'UNKNOWN': {'code': -1, 'message': 'An unknown or very miscellaneous error'},
}


def ping():
    return 'pong'


@atomic
async def handle_create_comment(**kwargs):
    pass


def handle_get_comment_ids(**kwargs):
    pass


def handle_get_claim_comments(**kwargs):
    pass


def handle_get_comments_by_id(**kwargs):
    pass


METHODS = {
    'ping': ping,
    'get_claim_comments': handle_get_claim_comments,
    'get_comment_ids': handle_get_comment_ids,
    'get_comments_by_id': handle_get_comments_by_id,
    'create_comment': handle_create_comment
}


def process_json(body: dict) -> dict:
    response = {'jsonrpc': '2.0', 'id': body['id']}
    if body['method'] in METHODS:
        method = body['method']
        params = body.get('params', {})
        try:
            if method in self.__db_methods:
                result = self.db_conn.__getattribute__(method).__call__(**params)
            else:
                result = self.methods[method](self, **params)
            response['result'] = result
        except TypeError as te:
            print(te)
            response['error'] = ERRORS['INVALID_PARAMS']
    else:
        response['error'] = ERRORS['UNKNOWN']
    return response


async def api_endpoint(request):
    try:
        body = await request.json()
        if type(body) is list or type(body) is dict:
            if type(body) is list:
                return web.json_response([process_json(part) for part in body])
            else:
                return web.json_response(process_json(body))
        else:
            return web.json_response({'error': ERRORS['UNKNOWN']})
    except json.decoder.JSONDecodeError as jde:
        return web.json_response({
            'error': {'message': jde.msg, 'code': -1}
        })




