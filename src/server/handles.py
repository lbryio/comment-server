import asyncio
import logging
import time
import typing

from aiohttp import web
from aiojobs.aiohttp import atomic
from peewee import DoesNotExist

from src.server.validation import validate_signature_from_claim
from src.misc import clean_input_params, get_claim_from_id
from src.server.errors import make_error, report_error
from src.database.models import Comment, Channel
from src.database.models import get_comment
from src.database.models import comment_list
from src.database.models import create_comment
from src.database.models import edit_comment
from src.database.models import delete_comment
from src.database.models import set_hidden_flag


logger = logging.getLogger(__name__)


# noinspection PyUnusedLocal
def ping(*args):
    return 'pong'


def handle_get_channel_from_comment_id(app: web.Application, comment_id: str) -> dict:
    comment = get_comment(comment_id)
    return {
        'channel_id': comment['channel_id'],
        'channel_name': comment['channel_name']
    }


def handle_get_comment_ids(
        app: web.Application,
        claim_id: str,
        parent_id: str = None,
        page: int = 1,
        page_size: int = 50,
        flattened=False
) -> dict:
    results = comment_list(
        claim_id=claim_id,
        parent_id=parent_id,
        top_level=(parent_id is None),
        page=page,
        page_size=page_size,
        select_fields=['comment_id', 'parent_id']
    )
    if flattened:
        results.update({
            'items': [item['comment_id'] for item in results['items']],
            'replies': [(item['comment_id'], item.get('parent_id'))
                        for item in results['items']]
        })
    return results


def handle_get_comments_by_id(
        app: web.Application,
        comment_ids: typing.Union[list, tuple]
) -> dict:
    expression = Comment.comment_id.in_(comment_ids)
    return comment_list(expressions=expression, page_size=len(comment_ids))


def handle_get_claim_comments(
        app: web.Application,
        claim_id: str,
        parent_id: str = None,
        page: int = 1,
        page_size: int = 50,
        top_level: bool = False
) -> dict:
    return comment_list(
        claim_id=claim_id,
        parent_id=parent_id,
        page=page,
        page_size=page_size,
        top_level=top_level
    )


def handle_get_claim_hidden_comments(
        app: web.Application,
        claim_id: str,
        hidden: bool,
        page: int = 1,
        page_size: int = 50,
) -> dict:
    exclude = 'hidden' if hidden else 'visible'
    return comment_list(
        claim_id=claim_id,
        exclude_mode=exclude,
        page=page,
        page_size=page_size
    )


def get_channel_from_comment_id(app, comment_id: str) -> dict:
    results = comment_list(
        expressions=(Comment.comment_id == comment_id),
        select_fields=['channel_name', 'channel_id', 'channel_url'],
        page_size=1
    )
    # todo: make the return type here consistent
    return results['items'].pop()


async def handle_abandon_comment(
        app: web.Application,
        comment_id: str,
        signature: str,
        signing_ts: str,
        **kwargs,
) -> dict:
    comment = get_comment(comment_id)
    try:
        channel = await get_claim_from_id(app, comment['channel_id'])
    except DoesNotExist:
        raise ValueError('Could not find a channel associated with the given comment')
    else:
        if not validate_signature_from_claim(channel, signature, signing_ts, comment_id):
            raise ValueError('Abandon signature could not be validated')

    with app['db'].atomic():
        return {
            'abandoned': delete_comment(comment_id)
        }


async def handle_hide_comments(app: web.Application, pieces: list, hide: bool = True) -> dict:
    # let's get all the distinct claim_ids from the list of comment_ids
    pieces_by_id = {p['comment_id']: p for p in pieces}
    comment_ids = list(pieces_by_id.keys())
    comments = (Comment
                .select(Comment.comment_id, Comment.claim_id)
                .where(Comment.comment_id.in_(comment_ids))
                .tuples())

    # resolve the claims and map them to their corresponding comment_ids
    claims = {}
    for comment_id, claim_id in comments:
        try:
            # try and resolve the claim, if fails then we mark it as null
            # and remove the associated comment from the pieces
            if claim_id not in claims:
                claims[claim_id] = await get_claim_from_id(app, claim_id)


async def handle_hide_comments(app, pieces: list = None, claim_id: str = None) -> dict:

    # return {'hidden': await hide_comments(app, **params)}
    raise NotImplementedError


async def handle_edit_comment(app, comment: str = None, comment_id: str = None,
                              signature: str = None, signing_ts: str = None, **params) -> dict:
    current = get_comment(comment_id)
    channel_claim = await get_claim_from_id(app, current['channel_id'])
    if not validate_signature_from_claim(channel_claim, signature, signing_ts, comment):
        raise ValueError('Signature could not be validated')

    with app['db'].atomic():
        if not edit_comment(comment_id, comment, signature, signing_ts):
            raise ValueError('Comment could not be edited')
        return get_comment(comment_id)


def handle_create_comment(app, comment: str = None, claim_id: str = None,
                          parent_id: str = None, channel_id: str = None, channel_name: str = None,
                          signature: str = None, signing_ts: str = None) -> dict:
    with app['db'].atomic():
        return create_comment(
            comment=comment,
            claim_id=claim_id,
            parent_id=parent_id,
            channel_id=channel_id,
            channel_name=channel_name,
            signature=signature,
            signing_ts=signing_ts
        )


METHODS = {
    'ping': ping,
    'get_claim_comments': handle_get_claim_comments,    # this gets used
    'get_claim_hidden_comments': handle_get_claim_hidden_comments,  # this gets used
    'get_comment_ids': handle_get_comment_ids,
    'get_comments_by_id': handle_get_comments_by_id,    # this gets used
    'get_channel_from_comment_id': get_channel_from_comment_id,  # this gets used
    'create_comment': handle_create_comment,   # this gets used
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
                result = await METHODS[method](app, **params)
            else:
                result = METHODS[method](app, **params)

        except Exception as err:
            logger.exception(f'Got {type(err).__name__}:\n{err}')
            if type(err) in (ValueError, TypeError):  # param error, not too important
                response['error'] = make_error('INVALID_PARAMS', err)
            else:
                response['error'] = make_error('INTERNAL', err)
            await app['webhooks'].spawn(report_error(app, err, body))
        else:
            response['result'] = result

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
