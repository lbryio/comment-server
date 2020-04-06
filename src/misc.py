import logging

from src.server.external import request_lbrynet

logger = logging.getLogger(__name__)

ID_LIST = {'claim_id', 'parent_id', 'comment_id', 'channel_id'}


async def get_claim_from_id(app, claim_id, **kwargs):
    try:
        return (await request_lbrynet(app, 'claim_search', claim_id=claim_id, **kwargs))['items'][0]
    except IndexError:
        return


def clean_input_params(kwargs: dict):
    for k, v in kwargs.items():
        if type(v) is str and k != 'comment':
            kwargs[k] = v.strip()
            if k in ID_LIST:
                kwargs[k] = v.lower()


def clean(thing: dict) -> dict:
    return {k: v for k, v in thing.items() if v is not None}