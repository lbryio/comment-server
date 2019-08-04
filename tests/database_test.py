from random import randint

import faker
from faker.providers import internet
from faker.providers import lorem
from faker.providers import misc

from src.database.queries import get_comments_by_id
from src.database.queries import get_comment_ids
from src.database.queries import get_claim_comments
from src.database.queries import get_hidden_claim_comments
from src.database.writes import create_comment_or_error
from src.database.queries import hide_comment_by_id
from src.database.queries import delete_comment_by_id
from tests.testcase import DatabaseTestCase

fake = faker.Faker()
fake.add_provider(internet)
fake.add_provider(lorem)
fake.add_provider(misc)


class TestCommentCreation(DatabaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.claimId = '529357c3422c6046d3fec76be2358004ba22e340'

    def test01NamedComments(self):
        comment = create_comment_or_error(
            conn=self.conn,
            claim_id=self.claimId,
            comment='This is a named comment',
            channel_name='@username',
            channel_id='529357c3422c6046d3fec76be2358004ba22abcd',
            signature=fake.uuid4(),
            signing_ts='aaa'
        )
        self.assertIsNotNone(comment)
        self.assertNotIn('parent_in', comment)
        previous_id = comment['comment_id']
        reply = create_comment_or_error(
            conn=self.conn,
            claim_id=self.claimId,
            comment='This is a named response',
            channel_name='@another_username',
            channel_id='529357c3422c6046d3fec76be2358004ba224bcd',
            parent_id=previous_id,
            signature=fake.uuid4(),
            signing_ts='aaa'
        )
        self.assertIsNotNone(reply)
        self.assertEqual(reply['parent_id'], comment['comment_id'])

    def test02AnonymousComments(self):
        comment = create_comment_or_error(
            conn=self.conn,
            claim_id=self.claimId,
            comment='This is an ANONYMOUS comment'
        )
        self.assertIsNotNone(comment)
        previous_id = comment['comment_id']
        reply = create_comment_or_error(
            conn=self.conn,
            claim_id=self.claimId,
            comment='This is an unnamed response',
            parent_id=previous_id
        )
        self.assertIsNotNone(reply)
        self.assertEqual(reply['parent_id'], comment['comment_id'])

    def test03SignedComments(self):
        comment = create_comment_or_error(
            conn=self.conn,
            claim_id=self.claimId,
            comment='I like big butts and i cannot lie',
            channel_name='@sirmixalot',
            channel_id='529357c3422c6046d3fec76be2358005ba22abcd',
            signature=fake.uuid4(),
            signing_ts='asdasd'
        )
        self.assertIsNotNone(comment)
        self.assertIn('signing_ts', comment)
        previous_id = comment['comment_id']
        reply = create_comment_or_error(
            conn=self.conn,
            claim_id=self.claimId,
            comment='This is a LBRY verified response',
            channel_name='@LBRY',
            channel_id='529357c3422c6046d3fec76be2358001ba224bcd',
            parent_id=previous_id,
            signature=fake.uuid4(),
            signing_ts='sfdfdfds'
        )
        self.assertIsNotNone(reply)
        self.assertEqual(reply['parent_id'], comment['comment_id'])
        self.assertIn('signing_ts', reply)

    def test04UsernameVariations(self):
        self.assertRaises(
            AssertionError,
            callable=create_comment_or_error,
            conn=self.conn,
            claim_id=self.claimId,
            channel_name='$#(@#$@#$',
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this is an invalid username'
        )
        valid_username = create_comment_or_error(
            conn=self.conn,
            claim_id=self.claimId,
            channel_name='@' + 'a' * 255,
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this is a valid username'
        )
        self.assertIsNotNone(valid_username)
        self.assertRaises(AssertionError,
                          callable=create_comment_or_error,
                          conn=self.conn,
                          claim_id=self.claimId,
                          channel_name='@' + 'a' * 256,
                          channel_id='529357c3422c6046d3fec76be2358001ba224b23',
                          comment='this username is too long'
                          )

        self.assertRaises(
            AssertionError,
            callable=create_comment_or_error,
            conn=self.conn,
            claim_id=self.claimId,
            channel_name='',
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this username should not default to ANONYMOUS'
        )
        self.assertRaises(
            AssertionError,
            callable=create_comment_or_error,
            conn=self.conn,
            claim_id=self.claimId,
            channel_name='@',
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this username is too short'
        )

    def test05InsertRandomComments(self):
        # TODO: Fix this test into something practical
        self.skipTest('This is a bad test')
        top_comments, claim_ids = generate_top_comments_random()
        total = 0
        success = 0
        for _, comments in top_comments.items():
            for i, comment in enumerate(comments):
                with self.subTest(comment=comment):
                    result = create_comment_or_error(self.conn, **comment)
                    if result:
                        success += 1
                    comments[i] = result
                    del comment
                total += len(comments)
        self.assertLessEqual(success, total)
        self.assertGreater(success, 0)
        success = 0
        for reply in generate_replies_random(top_comments):
            reply_id = create_comment_or_error(self.conn, **reply)
            if reply_id:
                success += 1
        self.assertGreater(success, 0)
        self.assertLess(success, total)
        del top_comments
        del claim_ids

    def test06GenerateAndListComments(self):
        # TODO: Make this test not suck
        self.skipTest('this is a stupid test')
        top_comments, claim_ids = generate_top_comments()
        total, success = 0, 0
        for _, comments in top_comments.items():
            for i, comment in enumerate(comments):
                result = create_comment_or_error(self.conn, **comment)
                if result:
                    success += 1
                comments[i] = result
                del comment
            total += len(comments)
        self.assertEqual(total, success)
        self.assertGreater(total, 0)
        for reply in generate_replies(top_comments):
            create_comment_or_error(self.conn, **reply)
        for claim_id in claim_ids:
            comments_ids = get_comment_ids(self.conn, claim_id)
            with self.subTest(comments_ids=comments_ids):
                self.assertIs(type(comments_ids), list)
                self.assertGreaterEqual(len(comments_ids), 0)
                self.assertLessEqual(len(comments_ids), 50)
                replies = get_comments_by_id(self.conn, comments_ids)
                self.assertLessEqual(len(replies), 50)
                self.assertEqual(len(replies), len(comments_ids))


class ListDatabaseTest(DatabaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        top_coms, self.claim_ids = generate_top_comments(5, 75)

    def testLists(self):
        for claim_id in self.claim_ids:
            with self.subTest(claim_id=claim_id):
                comments = get_claim_comments(self.conn, claim_id)
                self.assertIsNotNone(comments)
                self.assertGreater(comments['page_size'], 0)
                top_comments = get_claim_comments(self.conn, claim_id, top_level=True, page=1, page_size=50)
                self.assertIsNotNone(top_comments)
                self.assertEqual(top_comments['page_size'], 50)
                self.assertEqual(top_comments['page'], 1)
                self.assertGreaterEqual(top_comments['total_pages'], 0)
                self.assertGreaterEqual(top_comments['total_items'], 0)
                comment_ids = get_comment_ids(self.conn, claim_id, page_size=50, page=1)
                with self.subTest(comment_ids=comment_ids):
                    self.assertIsNotNone(comment_ids)
                    self.assertLessEqual(len(comment_ids), 50)
                    matching_comments = get_comments_by_id(self.conn, comment_ids)
                    self.assertIsNotNone(matching_comments)
                    self.assertEqual(len(matching_comments), len(comment_ids))


def generate_top_comments(ncid=15, ncomm=100, minchar=50, maxchar=500):
    claim_ids = [fake.sha1() for _ in range(ncid)]
    top_comments = {
        cid: [{
            'claim_id': cid,
            'comment': ''.join(fake.text(max_nb_chars=randint(minchar, maxchar))),
            'channel_name': '@' + fake.user_name(),
            'channel_id': fake.sha1(),
            'signature': fake.uuid4(),
            'signing_ts': fake.uuid4()
        } for _ in range(ncomm)]
        for cid in claim_ids
    }
    return top_comments, claim_ids


def generate_replies(top_comments):
    return [{
        'claim_id': comment['claim_id'],
        'parent_id': comment['comment_id'],
        'comment': ' '.join(fake.text(max_nb_chars=randint(50, 500))),
        'channel_name': '@' + fake.user_name(),
        'channel_id': fake.sha1(),
        'signature': fake.uuid4(),
        'signing_ts': fake.uuid4()
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
