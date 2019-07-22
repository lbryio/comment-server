import unittest
from random import randint

import requests
import re
import faker
from itertools import *
from faker.providers import internet
from faker.providers import lorem
from faker.providers import misc

from src.settings import config

fake = faker.Faker()
fake.add_provider(internet)
fake.add_provider(lorem)
fake.add_provider(misc)

def fake_lbryusername():
    return '@' + fake.user_name()


def jsonrpc_post(url, method, **params):
    json_body = {
        'jsonrpc': '2.0',
        'id': None,
        'method': method,
        'params': params
    }
    return requests.post(url=url, json=json_body)


def nothing():
    return None


class ServerTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = 'http://' + config['HOST'] + ':5921/api'


    def post_comment(self, **params):
        json_body = {
            'jsonrpc': '2.0',
            'id': None,
            'method': 'create_comment',
            'params': params
        }
        return requests.post(url=self.url, json=json_body)

    def assertIsValidMessageTest(self, message, test):
        self.assertIsNotNone(message)
        try:
            if not test['claim_id'] or \
                    (bool(test['channel_id']) ^ bool(test['channel_name'])):
                self.assertIn('error', message)
                self.assertNotIn('result', message)
            else:
                self.assertNotIn('error', message)
                self.assertIn('result', message)
                self.assertIn('comment_id', message['result'])
                self.assertEquals(message['result']['claim_id'], test['claim_id'])
        except AssertionError:
            raise requests.HTTPError(message.text)

    def isValidMessage(self, message: dict):
        return message and type(message) is dict and ('error' in message or 'result' in message)

    def isValidTest(self, test: dict):
        cond = test['claim_id'] and test['comment'] and not \
                (bool(test['channel_id']) ^ bool(test['channel_name']))
        if cond:
            cond = (0 < len(test['comment']) <= 2000) and cond
            if test['channel_id']:
                cond = (1 < len(test['channel_name']) <= 256) and cond
                channel_match = re.fullmatch(
                    '^@(?:(?![\x00-\x08\x0b\x0c\x0e-\x1f\x23-\x26'
                    '\x2f\x3a\x3d\x3f-\x40\uFFFE-\U0000FFFF]).){1,255}$',
                    test['channel_name']
                )
                cond = cond and channel_match
        return cond

    def setUp(self) -> None:
        self.reply_id = 'ace7800f36e55c74c4aa6a698f97a7ee5f1ccb047b5a0730960df90e58c41dc2'

    def test01CreateCommentNoReply(self):
        anonymous_test = create_test_comments(
            ('claim_id', 'channel_id', 'channel_name', 'comment'),
            comment=None,
            channel_name=None,
            channel_id=None,
            claim_id=None
        )
        for test in anonymous_test:
            with self.subTest(test=test):
                message = self.post_comment(**test)
                message = message.json()
                if self.isValidTest(test):
                    self.assertIn('result', message)
                    self.assertIsNotNone(message['result'])
                    self.assertIn('comment_id', message['result'])
                else:
                    self.assertIn('error', message)

    def test02CreateNamedCommentsNoReply(self):
        named_test = create_test_comments(
            ('channel_name', 'channel_id', 'signature'),
            claim_id='1234567890123456789012345678901234567890',
            channel_name='@JamieFoxx',
            channel_id='1234567890'*4,
            comment='blah blah blahbity blah',
            signature=None
        )
        for test in named_test:
            with self.subTest(test=test):
                message = self.post_comment(**test)
                message = message.json()
                if self.isValidTest(test):
                    self.assertTrue(self.isValidMessage(message))
                else:
                    self.assertFalse(self.isValidMessage(message))

    def test03CreateAllTestComments(self):
        test_all = create_test_comments(replace.keys(), **{
            k: None for k in replace.keys()
        })
        for test in test_all:
            with self.subTest(test=test):
                message = self.post_comment(**test)
                message = message.json()
                if self.isValidTest(test):
                    self.assertTrue(self.isValidMessage(message))
                    self.assertNotIn('error', message)
                    self.assertIsNotNone(message['result'])
                else:
                    self.assertIsNotNone(message)
                    self.assertIn('error', message)

    def test04CreateAllReplies(self):
        claim_id = '1d8a5cc39ca02e55782d619e67131c0a20843be8'
        parent_comment = self.post_comment(
            channel_name='@KevinWalterRabie',
            channel_id=fake.sha1(),
            comment='Hello everybody and welcome back to my chan nel',
            claim_id=claim_id,
        )
        parent_id = parent_comment.json()['result']['comment_id']
        test_all = create_test_comments(
            ('comment', 'channel_name', 'channel_id', 'signature', 'parent_id'),
            parent_id=parent_id,
            comment=None,
            channel_name=None,
            channel_id=None,
            signature=None,
            claim_id=claim_id
        )
        for test in test_all:
            with self.subTest(test=test) as subtest:
                if test['parent_id'] != parent_id:
                    continue
                else:
                    message = self.post_comment(**test)
                    message = message.json()
                    if self.isValidTest(test):
                        self.assertTrue(self.isValidMessage(message))
                        self.assertNotIn('error', message)
                        self.assertIsNotNone(message['result'])
                        message = message['result']
                        self.assertIn('parent_id', message)
                        self.assertEquals(message['parent_id'], parent_id)
                    else:
                        self.assertIn('error', message)



class ListCommentsTest(unittest.TestCase):
    replace = {
        'claim_id': fake.sha1,
        'comment': fake.text,
        'channel_id': fake.sha1,
        'channel_name': fake_lbryusername,
        'signature': nothing,
        'parent_id': nothing
    }

    @classmethod
    def post_comment(cls, **params):
        json_body = {
            'jsonrpc': '2.0',
            'id': None,
            'method': 'create_comment',
            'params': params
        }
        return requests.post(url=cls.url, json=json_body)

    @classmethod
    def setUpClass(cls) -> None:
        cls.url = 'http://' + config['HOST'] + ':5921/api'
        cls.claim_id = '1d8a5cc39ca02e55782d619e67131c0a20843be8'
        cls.comment_list = [{key: cls.replace[key]() for key in cls.replace.keys()} for _ in range(23)]
        for comment in cls.comment_list:
            comment['claim_id'] = cls.claim_id
        cls.comment_ids = [cls.post_comment(**comm).json()['result']['comment_id']
                           for comm in cls.comment_list]

    def testListComments(self):
        response_one = jsonrpc_post(self.url, 'get_claim_comments', page_size=20,
                                    page=1, top_level=1, claim_id=self.claim_id).json()
        self.assertIsNotNone(response_one)
        self.assertIn('result', response_one)
        response_one: dict = response_one['result']
        self.assertIs(type(response_one), dict)
        self.assertEquals(response_one['page_size'], len(response_one['items']))
        self.assertIn('items', response_one)
        self.assertGreaterEqual(response_one['total_pages'], response_one['page'])
        last_page = response_one['total_pages']
        response = jsonrpc_post(self.url, 'get_claim_comments', page_size=20,
                                page=last_page, top_level=1, claim_id=self.claim_id).json()
        self.assertIsNotNone(response)
        self.assertIn('result', response)
        response: dict = response['result']
        self.assertIs(type(response['items']), list)
        self.assertEqual(response['total_items'], response_one['total_items'])
        self.assertEqual(response['total_pages'], response_one['total_pages'])





replace = {
    'claim_id': fake.sha1,
    'comment': fake.text,
    'channel_id': fake.sha1,
    'channel_name': fake_lbryusername,
    'signature': fake.uuid4,
    'parent_id': fake.sha256
}


def create_test_comments(values: iter, **default):
    vars_combo = chain.from_iterable(combinations(values, r) for r in range(1, len(values) + 1))
    return [{k: replace[k]() if k in comb else v for k, v in default.items()}
            for comb in vars_combo]


def create_comment(channel_name, channel_id, claim_id=None, maxchar=500, reply_id=None, signature=None, parent_id=None):
    return {
        'claim_id': claim_id if claim_id else fake.sha1(),
        'comment': ''.join(fake.text(max_nb_chars=maxchar)),
        'channel_name': channel_name,
        'channel_id': channel_id,
        'signature': signature if signature else fake.uuid4(),
        'parent_id': reply_id
    }


