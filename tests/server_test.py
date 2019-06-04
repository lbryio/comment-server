import unittest

import faker
import requests
from faker.providers import internet
from faker.providers import lorem
from faker.providers import misc

from src.settings import config

fake = faker.Faker()
fake.add_provider(internet)
fake.add_provider(lorem)
fake.add_provider(misc)


def post_jsonrpc(url, method, **params):
    return requests.post(
        url=url,
        json={
            'jsonrpc': '2.0',
            'id': None,
            'method': method,
            'params': params
        }
    ).json()


def comment_create(**kwargs):
    return post_jsonrpc('http://localhost:5921/api', 'create_comment', **kwargs)


def comment_list(**kwargs):
    return post_jsonrpc('http://localhost:5921/api', 'get_claim_comments', **kwargs)


def fake_lbryusername():
    return '@' + fake.user_name()


class ServerTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = 'http://' + config['HOST'] + ':5921/api'

    def setUp(self) -> None:
        self.claim_id = '9cb713f01bf247a0e03170b5ed00d5161340c486'

    def test01CreateCommentNoReply(self):
        resp = comment_create(
            claim_id=self.claim_id,
            comment='anonymous comment'
        )
        self.assertIn('result', resp)
        resp = resp['result']
        self.assertIsNotNone(resp)
        self.assertIn('comment_id', resp)

    def test02CreateNamedCommentNoSignature(self):
        resp = comment_create(
            claim_id=self.claim_id,
            comment='blah blah blah this is my comment',
            channel_name=fake_lbryusername(),
            channel_id=fake.sha1(),
        )
        self.assertIn('result', resp)
        resp = resp['result']
        self.assertIsNotNone(resp)
        self.assertIn('comment_id', resp)
        self.assertNotIn('parent_id', resp)

    def test03InvalidComments(self):
        resp = comment_create(
            claim_id=self.claim_id,
            comment='this comment should fail',
            signature=fake.sha1()
        )
        self.assertNotIn('result', resp)
        self.assertIn('error', resp)
        resp = comment_create(
            comment='This comment has no claim_id'
        )
        self.assertNotIn('result', resp)
        self.assertIn('error', resp)
        resp = comment_create(claim_id=self.claim_id)
        self.assertIn('error', resp)
        resp = comment_create()
        self.assertIn('error', resp)
        resp = comment_create(
            claim_id=self.claim_id,
            comment='This comment has no channel_id',
            channel_name=fake_lbryusername(),
        )
        self.assertIn('error', resp)
        resp = comment_create(
            claim_id=self.claim_id,
            comment='This comment has no channel_name',
            channel_id=fake.sha1(),
        )
        self.assertIn('error', resp)

    def test04CreateAnonymousReply(self):
        resp = comment_create(claim_id=self.claim_id, comment='anonymous comment')
        self.assertIn('result', resp)
        resp = resp['result']
        self.assertIn('comment_id', resp)
        reply = comment_create(
            claim_id=self.claim_id,
            comment='anonymous reply',
            parent_id=resp['comment_id']
        )
        self.assertIn('result', reply)
        self.assertIn('parent_id', reply['result'])
        self.assertEquals(reply['result']['parent_id'], resp['comment_id'])

    def test05CreateNamedReplies(self):
        resp = comment_create(
            claim_id=self.claim_id,
            comment='blah blah blah this is my comment',
            channel_name=fake_lbryusername(),
            channel_id=fake.sha1(),
        )
        self.assertIn('result', resp)
        parent_id = resp['result']['comment_id']
        reply = comment_create(
            claim_id=self.claim_id,
            comment='this is a boring response to a named comment',
            channel_name='@DukeSilver',
            channel_id=fake.sha1(),
            parent_id=parent_id
        )
        self.assertIn('result', reply)
        self.assertIn('comment_id', reply['result'])
        self.assertIn('parent_id', reply['result'])
        self.assertEquals(reply['result']['parent_id'], parent_id)
