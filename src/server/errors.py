import json

import logging
import aiohttp


logger = logging.getLogger(__name__)


ERRORS = {
    'INVALID_PARAMS': {'code': -32602, 'message': 'Invalid Method Parameter(s).'},
    'INTERNAL': {'code': -32603, 'message': 'Internal Server Error. Please notify a LBRY Administrator.'},
    'METHOD_NOT_FOUND': {'code': -32601, 'message': 'The method does not exist / is not available.'},
    'INVALID_REQUEST': {'code': -32600, 'message': 'The JSON sent is not a valid Request object.'},
    'PARSE_ERROR': {
        'code': -32700,
        'message': 'Invalid JSON was received by the server.\n'
                   'An error occurred on the server while parsing the JSON text.'
    }
}


def make_error(error, exc=None) -> dict:
    body = ERRORS[error] if error in ERRORS else ERRORS['INTERNAL']
    try:
        if exc:
            exc_name = type(exc).__name__
            body.update({exc_name: str(exc)})

    finally:
        return body


async def report_error(app, exc, body: dict):
    try:
        if 'slack_webhook' in app['config']:
            body_dump = json.dumps(body, indent=4)
            exec_name = type(exc).__name__
            exec_body = str(exc)
            message = {
                "text": f"Got `{exec_name}`: `\n{exec_body}`\n```{body_dump}```"
            }
            async with aiohttp.ClientSession() as sesh:
                async with sesh.post(app['config']['slack_webhook'], json=message) as resp:
                    await resp.wait_for_close()

    except Exception:
        logger.critical('Error while logging to slack webhook')