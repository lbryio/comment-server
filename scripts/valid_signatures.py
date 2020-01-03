import binascii
import logging
import hashlib
import json
import sqlite3
import asyncio
import aiohttp

from server.validation import is_signature_valid, get_encoded_signature

logger = logging.getLogger(__name__)


async def request_lbrynet(url, method, **params):
    body = {'method': method, 'params': {**params}}
    async with aiohttp.request('POST', url, json=body) as req:
        try:
            resp = await req.json()
        finally:
            if 'result' in resp:
                return resp['result']


def get_comments_with_signatures(_conn: sqlite3.Connection) -> list:
    with _conn:
        curs = _conn.execute("SELECT * FROM COMMENTS_ON_CLAIMS WHERE signature IS NOT NULL")
        return [dict(r) for r in curs.fetchall()]


def is_valid_signature(pubkey, channel_id, signature, signing_ts, data: str) -> bool:
    try:
        if pubkey:
            claim_hash = binascii.unhexlify(channel_id.encode())[::-1]
            injest = b''.join((signing_ts.encode(), claim_hash, data.encode()))
            return is_signature_valid(
                encoded_signature=get_encoded_signature(signature),
                signature_digest=hashlib.sha256(injest).digest(),
                public_key_bytes=binascii.unhexlify(pubkey.encode())
            )
        else:
            raise Exception("Pubkey is null")
    except Exception as e:
        print(e)
        return False


async def get_channel_pubkeys(comments: list):
    urls = {c['channel_url'] for c in comments}
    claims = await request_lbrynet('http://localhost:5279', 'resolve', urls=list(urls))
    cids = {c['channel_id']: None for c in comments}
    error_claims = []
    for url, claim in claims.items():
        if 'error' not in claim:
            cids.update({
                claim['claim_id']: claim['value']['public_key']
            })
        else:
            error_claims.append({url: claim})
    return cids, error_claims


def count_valid_signatures(cmts: list, chan_pubkeys: dict):
    invalid_comments = []
    for c in cmts:
        pubkey = chan_pubkeys.get(c['channel_id'])
        if not is_valid_signature(pubkey, c['channel_id'], c['signature'], c['signing_ts'], c['comment']):
            invalid_comments.append(c)
    return len(cmts) - len(invalid_comments), invalid_comments


if __name__ == '__main__':
    conn = sqlite3.connect('database/default.db')
    conn.row_factory = sqlite3.Row
    comments = get_comments_with_signatures(conn)
    loop = asyncio.get_event_loop()
    chan_keys, errored = loop.run_until_complete(get_channel_pubkeys(comments))
    valid_sigs, invalid_coms = count_valid_signatures(comments, chan_keys)
    print(f'Total Signatures: {len(comments)}\nValid Signatures: {valid_sigs}')
    print(f'Invalid Signatures: {len(comments) - valid_sigs}')
    print(f'Percent Valid: {round(valid_sigs/len(comments)*100, 3)}%')
    print(f'# Unresolving claims: {len(errored)}')
    print(f'Num invalid comments: {len(invalid_coms)}')
    print(json.dumps(errored, indent=2))
    json.dump(invalid_coms, 'invalid_coms.json', indent=2)

