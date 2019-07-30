import unittest
from multiprocessing.pool import Pool

import requests


class ConcurrentWriteTest(unittest.TestCase):

    @staticmethod
    def make_comment(num):
        return {
            'jsonrpc': '2.0',
            'id': num,
            'method': 'create_comment',
            'params': {
                'comment': f'Comment #{num}',
                'claim_id': '6d266af6c25c80fa2ac6cc7662921ad2e90a07e7',
            }
        }

    @staticmethod
    def send_comment_to_server(params):
        with requests.post(params[0], json=params[1]) as req:
            return req.json()

    def test01Concurrency(self):
        urls = [f'http://localhost:{port}/api' for port in range(5921, 5925)]
        comments = [self.make_comment(i) for i in range(1, 5)]
        inputs = list(zip(urls, comments))
        with Pool(4) as pool:
            results = pool.map(self.send_comment_to_server, inputs)
        results = list(filter(lambda x: 'comment_id' in x['result'], results))
        self.assertIsNotNone(results)
        self.assertEqual(len(results), len(inputs))
