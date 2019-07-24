from multiprocessing import Pool
import json
import requests


def make_comment(num):
    return{
        'jsonrpc': '2.0',
        'id': None,
        'method': 'create_comment',
        'params': {
            'comment': f'Comment #{num}',
            'claim_id': '6d266af6c25c80fa2ac6cc7662921ad2e90a07e7',
        }
    }


def send_comment_to_server(params):
    with requests.post(params[0], json=params[1]) as req:
        return req.json()


if __name__ == '__main__':
    urls = [f'http://localhost:{port}/api' for port in range(5921, 5925)]
    comments = [make_comment(i) for i in range(1, 5)]
    inputs = list(zip(urls, comments))
    print(json.dumps(inputs, indent=2))
    with Pool(4) as pool:
        print(json.dumps(pool.map(send_comment_to_server, inputs), indent=2))
