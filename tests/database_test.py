import unittest

from faker.providers import internet
from faker.providers import lorem
from faker.providers import misc

import server.conf
import server.database as db
import sqlite3
import faker
from random import randint

fake = faker.Faker()
fake.add_provider(internet)
fake.add_provider(lorem)
fake.add_provider(misc)


class DatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.db = db.DatabaseConnection('test.db')
        self.db.obtain_connection()
        self.db.generate_schema(server.conf.schema_dir)

    def tearDown(self) -> None:
        curs = self.db.connection.execute('SELECT * FROM COMMENT')
        results = {'COMMENT': [dict(r) for r in curs.fetchall()]}
        curs = self.db.connection.execute('SELECT * FROM CHANNEL')
        results['CHANNEL'] = [dict(r) for r in curs.fetchall()]
        curs = self.db.connection.execute('SELECT * FROM COMMENTS_ON_CLAIMS')
        results['COMMENTS_ON_CLAIMS'] = [dict(r) for r in curs.fetchall()]
        curs = self.db.connection.execute('SELECT * FROM COMMENT_REPLIES')
        results['COMMENT_REPLIES'] = [dict(r) for r in curs.fetchall()]
        # print(json.dumps(results, indent=4))
        conn: sqlite3.Connection = self.db.connection
        with conn:
            conn.executescript("""
                DROP TABLE IF EXISTS COMMENT;
                DROP TABLE IF EXISTS CHANNEL;
                DROP VIEW IF EXISTS COMMENTS_ON_CLAIMS;
                DROP VIEW IF EXISTS COMMENT_REPLIES;
            """)
        conn.close()


class TestCommentCreation(DatabaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.claimId = '529357c3422c6046d3fec76be2358004ba22e340'

    def testNamedComments(self):
        comment = self.db.create_comment(
            claim_id=self.claimId,
            comment='This is a named comment',
            channel_name='@username',
            channel_id='529357c3422c6046d3fec76be2358004ba22abcd',
        )
        self.assertIsNotNone(comment)
        self.assertIn('comment', comment)
        self.assertIn('comment_id', comment)
        self.assertIn('parent_id', comment)
        self.assertIsNone(comment['parent_id'])
        previous_id = comment['comment_id']
        reply = self.db.create_comment(
            claim_id=self.claimId,
            comment='This is a named response',
            channel_name='@another_username',
            channel_id='529357c3422c6046d3fec76be2358004ba224bcd',
            parent_id=previous_id
        )
        self.assertIsNotNone(reply)
        self.assertIn('comment', reply)
        self.assertIn('comment_id', reply)
        self.assertIn('parent_id', reply)
        self.assertEqual(reply['parent_id'], comment['comment_id'])
        self.assertEqual(reply['claim_id'], comment['claim_id'])

    def testAnonymousComments(self):
        comment = self.db.create_comment(
            claim_id=self.claimId,
            comment='This is an anonymous comment'
        )
        self.assertIsNotNone(comment)
        self.assertIn('comment', comment)
        self.assertIn('comment_id', comment)
        self.assertIn('parent_id', comment)
        self.assertIsNone(comment['parent_id'])
        previous_id = comment['comment_id']
        reply = self.db.create_comment(
            claim_id=self.claimId,
            comment='This is an unnamed response',
            parent_id=previous_id
        )
        self.assertIsNotNone(reply)
        self.assertIn('comment', reply)
        self.assertIn('comment_id', reply)
        self.assertIn('parent_id', reply)
        self.assertEqual(reply['parent_id'], comment['comment_id'])
        self.assertEqual(reply['claim_id'], comment['claim_id'])

    def testSignedComments(self):
        comment = self.db.create_comment(
            claim_id=self.claimId,
            comment='I like big butts and i cannot lie',
            channel_name='@sirmixalot',
            channel_id='529357c3422c6046d3fec76be2358005ba22abcd',
            sig='siggy'
        )
        self.assertIsNotNone(comment)
        self.assertIn('comment', comment)
        self.assertIn('comment_id', comment)
        self.assertIn('parent_id', comment)
        self.assertIsNone(comment['parent_id'])
        previous_id = comment['comment_id']
        reply = self.db.create_comment(
            claim_id=self.claimId,
            comment='This is a LBRY verified response',
            channel_name='@LBRY',
            channel_id='529357c3422c6046d3fec76be2358001ba224bcd',
            parent_id=previous_id,
            sig='Cursive Font Goes Here'
        )
        self.assertIsNotNone(reply)
        self.assertIn('comment', reply)
        self.assertIn('comment_id', reply)
        self.assertIn('parent_id', reply)
        self.assertEqual(reply['parent_id'], comment['comment_id'])
        self.assertEqual(reply['claim_id'], comment['claim_id'])

    def testUsernameVariations(self):
        invalid_comment = self.db.create_comment(
            claim_id=self.claimId,
            channel_name='$#(@#$@#$',
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this is an invalid username'
        )
        self.assertIsNone(invalid_comment)
        valid_username = self.db.create_comment(
            claim_id=self.claimId,
            channel_name='@' + 'a'*255,
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this is a valid username'
        )
        self.assertIsNotNone(valid_username)

        lengthy_username = self.db.create_comment(
            claim_id=self.claimId,
            channel_name='@' + 'a'*256,
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this username is too long'
        )
        self.assertIsNone(lengthy_username)
        comment = self.db.create_comment(
            claim_id=self.claimId,
            channel_name='',
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this username should not default to anonymous'
        )
        self.assertIsNone(comment)
        short_username = self.db.create_comment(
            claim_id=self.claimId,
            channel_name='@',
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this username is too short'
        )
        self.assertIsNone(short_username)


class PopulatedDatabaseTest(DatabaseTestCase):
    def setUp(self) -> None:
        super().setUp()

    def test01InsertRandomComments(self):
        top_comments, claim_ids = generate_top_comments_random()
        total = 0
        success = 0
        for _, comments in top_comments.items():
            for i, comment in enumerate(comments):
                with self.subTest(comment=comment):
                    result = self.db.create_comment(**comment)
                    if result:
                        success += 1
                    comments[i] = result
                    del comment
                total += len(comments)
        self.assertLessEqual(success, total)
        self.assertGreater(success, 0)
        success = 0
        for reply in generate_replies_random(top_comments):
            reply_id = self.db.create_comment(**reply)
            if reply_id:
                success += 1
        self.assertGreater(success, 0)
        self.assertLess(success, total)
        del top_comments
        del claim_ids

    def test02GenerateAndListComments(self):
        top_comments, claim_ids = generate_top_comments()
        total, success = 0, 0
        for _, comments in top_comments.items():
            for i, comment in enumerate(comments):
                result = self.db.create_comment(**comment)
                if result:
                    success += 1
                comments[i] = result
                del comment
            total += len(comments)
        self.assertEqual(total, success)
        self.assertGreater(total, 0)
        success, total = 0, 0
        for reply in generate_replies(top_comments):
            self.db.create_comment(**reply)
        self.assertEqual(success, total)
        for claim_id in claim_ids:
            comments_ids = self.db.get_comment_ids(claim_id)
            with self.subTest(comments_ids=comments_ids):
                self.assertIs(type(comments_ids), list)
                self.assertGreaterEqual(len(comments_ids), 0)
                self.assertLessEqual(len(comments_ids), 50)
                replies = self.db.get_comments_by_id(comments_ids)
                self.assertLessEqual(len(replies), 50)
                self.assertEqual(len(replies), len(comments_ids))


def generate_replies(top_comments):
    return [{
        'claim_id': comment['claim_id'],
        'parent_id': comment['comment_id'],
        'comment': ' '.join(fake.text(max_nb_chars=randint(50, 500))),
        'channel_name': '@' + fake.user_name(),
        'channel_id': fake.sha1(),
        'signature': fake.uuid4()
    }
        for claim, comments in top_comments.items()
        for i, comment in enumerate(comments)
        if comment  # ensures comment is non-null
    ]


def generate_replies_random(top_comments):
    return [{
        'claim_id': comment['claim_id'],
        'parent_id': comment['comment_id'],
        'comment': ' '.join(fake.text(max_nb_chars=randint(50, 2500))),
        'channel_name': '@' + fake.user_name(),
        'channel_id': fake.sha1() if hash(comment['comment_id']) % 5 == 0 else '',
        'signature': fake.uuid4() if hash(comment['comment_id']) % 11 == 0 else None
    }
        for claim, comments in top_comments.items()
        for i, comment in enumerate(comments)
        if comment
    ]


def generate_top_comments():
    claim_ids = [fake.sha1() for _ in range(15)]
    top_comments = {
        cid: [{
            'claim_id': cid,
            'comment': ''.join(fake.text(max_nb_chars=randint(50, 500))),
            'channel_name': '@' + fake.user_name(),
            'channel_id': fake.sha1(),
            'signature': fake.uuid4()
        } for _ in range(100)]
        for cid in claim_ids
    }
    return top_comments, claim_ids


def generate_top_comments_random():
    claim_ids = [fake.sha1() for _ in range(15)]
    top_comments = {
        cid: [{
            'claim_id': cid,
            'comment': ''.join(fake.text(max_nb_chars=randint(50, 2500))),
            'channel_name': '@' + fake.user_name() if (hash(cid) * i) % 7 > 0 else '',
            'channel_id': fake.sha1() if (hash(cid) * i) % 7 > 0 else '',
            'signature': fake.uuid4() if (hash(cid) * i) % 7 > 0 > hash(cid) else None
        } for i in range(randint(60, 200))]
        for cid in claim_ids
    }
    return top_comments, claim_ids

