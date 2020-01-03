import asyncio
import json

import aiohttp

from src.database.queries import obtain_connection


async def main():
    conn = obtain_connection('your_path_here')
    with conn:
        curs = conn.cursor()
        res = curs.execute("""
            SELECT DISTINCT LbryClaimId claim_id FROM COMMENT; 
        """).fetchall()
        rows = [tuple(r)[0] for r in res]
        claims = {cid: {"comments": []} for cid in rows}

        comments = curs.execute("""
            SELECT channel_name, comment, comment_id, claim_id, timestamp 
            FROM COMMENTS_ON_CLAIMS
        """).fetchall()
        comments = [dict(r) for r in comments]
        while len(comments) > 0:
            c = comments.pop()
            cid = c.pop('claim_id')
            claims[cid]['comments'].append(c)

    lbrynet = 'http://localhost:5279'

    async with aiohttp.ClientSession() as client:
        i = 0
        for cid, data in claims.items():
            body = {
                'method': 'claim_search',
                'params': {
                    'claim_id': cid,
                    'no_totals': True
                }
            }

            async with client.post(lbrynet, json=body) as resp:
                res = (await resp.json())

            try:
                res = res['result']['items']
                print(f'{i} - ok')
                if res:
                    data.update({
                        'name': res[0]['name'],
                        'permanent_url': res[0]['permanent_url']
                    })
            except KeyError:
                print(f'{i}: broke')
                # await asyncio.sleep(1)
            i += 1
    return claims


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    claims = loop.run_until_complete(main())
    # print(claims)
    with open('comments_on_claims.json', 'w') as fp:
        json.dump(claims, fp, indent=2)


