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


async def report_error(app, exc, msg=''):
    try:
        if 'slack_webhook' in app['config']:
            if msg:
                msg = f'"{msg}"'
            body = {
                "text": f"Got `{type(exc).__name__}`: ```\n{str(exc)}```\n{msg}"
            }
            async with aiohttp.ClientSession() as sesh:
                async with sesh.post(app['config']['slack_webhook'], json=body) as resp:
                    await resp.wait_for_close()

    except Exception:
        logger.critical('Error while logging to slack webhook')