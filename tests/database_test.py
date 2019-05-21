from random import randint
import faker
from faker.providers import internet
from faker.providers import lorem
from faker.providers import misc


import lbry_comment_server.database as db
import schema.db_helpers as schema
from lbry_comment_server.settings import config
from tests.testcase import DatabaseTestCase, AsyncioTestCase

fake = faker.Faker()
fake.add_provider(internet)
fake.add_provider(lorem)
fake.add_provider(misc)


class TestCommentCreation(DatabaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.claimId = '529357c3422c6046d3fec76be2358004ba22e340'

    def test01NamedComments(self):
        comment = db.create_comment(
            conn=self.conn,
            claim_id=self.claimId,
            comment='This is a named comment',
            channel_name='@username',
            channel_id='529357c3422c6046d3fec76be2358004ba22abcd',
        )
        self.assertIsNotNone(comment)
        self.assertIsNone(comment['parent_id'])
        previous_id = comment['comment_id']
        reply = db.create_comment(
            conn=self.conn,
            claim_id=self.claimId,
            comment='This is a named response',
            channel_name='@another_username',
            channel_id='529357c3422c6046d3fec76be2358004ba224bcd',
            parent_id=previous_id
        )
        self.assertIsNotNone(reply)
        self.assertEqual(reply['parent_id'], comment['comment_id'])
        self.assertEqual(reply['claim_id'], comment['claim_id'])

    def test02AnonymousComments(self):
        comment = db.create_comment(
            conn=self.conn,
            claim_id=self.claimId,
            comment='This is an ANONYMOUS comment'
        )
        self.assertIsNotNone(comment)
        self.assertIsNone(comment['parent_id'])
        previous_id = comment['comment_id']
        reply = db.create_comment(
            conn=self.conn,
            claim_id=self.claimId,
            comment='This is an unnamed response',
            parent_id=previous_id
        )
        self.assertIsNotNone(reply)
        self.assertEqual(reply['parent_id'], comment['comment_id'])
        self.assertEqual(reply['claim_id'], comment['claim_id'])

    def test03SignedComments(self):
        comment = db.create_comment(
            conn=self.conn,
            claim_id=self.claimId,
            comment='I like big butts and i cannot lie',
            channel_name='@sirmixalot',
            channel_id='529357c3422c6046d3fec76be2358005ba22abcd',
            signature='siggy'
        )
        self.assertIsNotNone(comment)
        self.assertIsNone(comment['parent_id'])
        previous_id = comment['comment_id']
        reply = db.create_comment(
            conn=self.conn,
            claim_id=self.claimId,
            comment='This is a LBRY verified response',
            channel_name='@LBRY',
            channel_id='529357c3422c6046d3fec76be2358001ba224bcd',
            parent_id=previous_id,
            signature='Cursive Font Goes Here'
        )
        self.assertIsNotNone(reply)
        self.assertEqual(reply['parent_id'], comment['comment_id'])
        self.assertEqual(reply['claim_id'], comment['claim_id'])

    def test04UsernameVariations(self):
        invalid_comment = db.create_comment(
            conn=self.conn,
            claim_id=self.claimId,
            channel_name='$#(@#$@#$',
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this is an invalid username'
        )
        self.assertIsNone(invalid_comment)
        valid_username = db.create_comment(
            conn=self.conn,
            claim_id=self.claimId,
            channel_name='@' + 'a'*255,
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this is a valid username'
        )
        self.assertIsNotNone(valid_username)

        lengthy_username = db.create_comment(
            conn=self.conn,
            claim_id=self.claimId,
            channel_name='@' + 'a'*256,
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this username is too long'
        )
        self.assertIsNone(lengthy_username)
        comment = db.create_comment(
            conn=self.conn,
            claim_id=self.claimId,
            channel_name='',
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this username should not default to ANONYMOUS'
        )
        self.assertIsNone(comment)
        short_username = db.create_comment(
            conn=self.conn,
            claim_id=self.claimId,
            channel_name='@',
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this username is too short'
        )
        self.assertIsNone(short_username)

    def test05InsertRandomComments(self):
        top_comments, claim_ids = generate_top_comments_random()
        total = 0
        success = 0
        for _, comments in top_comments.items():
            for i, comment in enumerate(comments):
                with self.subTest(comment=comment):
                    result = db.create_comment(self.conn, **comment)
                    if result:
                        success += 1
                    comments[i] = result
                    del comment
                total += len(comments)
        self.assertLessEqual(success, total)
        self.assertGreater(success, 0)
        success = 0
        for reply in generate_replies_random(top_comments):
            reply_id = db.create_comment(self.conn, **reply)
            if reply_id:
                success += 1
        self.assertGreater(success, 0)
        self.assertLess(success, total)
        del top_comments
        del claim_ids

    def test06GenerateAndListComments(self):
        top_comments, claim_ids = generate_top_comments()
        total, success = 0, 0
        for _, comments in top_comments.items():
            for i, comment in enumerate(comments):
                result = db.create_comment(self.conn, **comment)
                if result:
                    success += 1
                comments[i] = result
                del comment
            total += len(comments)
        self.assertEqual(total, success)
        self.assertGreater(total, 0)
        for reply in generate_replies(top_comments):
            db.create_comment(self.conn, **reply)
        for claim_id in claim_ids:
            comments_ids = db.get_comment_ids(self.conn, claim_id)
            with self.subTest(comments_ids=comments_ids):
                self.assertIs(type(comments_ids), list)
                self.assertGreaterEqual(len(comments_ids), 0)
                self.assertLessEqual(len(comments_ids), 50)
                replies = db.get_comments_by_id(self.conn, comments_ids)
                self.assertLessEqual(len(replies), 50)
                self.assertEqual(len(replies), len(comments_ids))


class ListDatabaseTest(DatabaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        top_coms, self.claim_ids = generate_top_comments(5, 75)
        self.top_comments = {
            commie_id: [db.create_comment(self.conn, **commie) for commie in commie_list]
            for commie_id, commie_list in top_coms.items()
        }
        self.replies = [
            db.create_comment(self.conn, **reply)
            for reply in generate_replies(self.top_comments)
        ]

    def testLists(self):
        for claim_id in self.claim_ids:
            with self.subTest(claim_id=claim_id):
                comments = db.get_claim_comments(self.conn, claim_id)
                self.assertIsNotNone(comments)
                self.assertLessEqual(len(comments), 50)
                top_comments = db.get_claim_comments(self.conn, claim_id, top_level=True, page=1, page_size=50)
                self.assertIsNotNone(top_comments)
                self.assertLessEqual(len(top_comments), 50)
                comment_ids = db.get_comment_ids(self.conn, claim_id, page_size=50, page=1)
                with self.subTest(comment_ids=comment_ids):
                    self.assertIsNotNone(comment_ids)
                    self.assertLessEqual(len(comment_ids), 50)
                    matching_comments = db.get_comments_by_id(self.conn, comment_ids)
                    self.assertIsNotNone(matching_comments)
                    self.assertEqual(len(matching_comments), len(comment_ids))


class AsyncWriteTest(AsyncioTestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_path = config['PATH']['TEST']
        self.claimId = '529357c3422c6046d3fec76be2358004ba22e340'

    async def asyncSetUp(self):
        await super().asyncSetUp()
        schema.setup_database(self.db_path)

    async def asyncTearDown(self):
        await super().asyncTearDown()
        schema.teardown_database(self.db_path)

    async def test01NamedComments(self):
        comment = await db.create_comment_async(
            self.db_path,
            claim_id=self.claimId,
            comment='This is a named comment',
            channel_name='@username',
            channel_id='529357c3422c6046d3fec76be2358004ba22abcd',
        )
        self.assertIsNotNone(comment)
        self.assertIsNone(comment['parent_id'])
        previous_id = comment['comment_id']
        reply = await db.create_comment_async(
            self.db_path,
            claim_id=self.claimId,
            comment='This is a named response',
            channel_name='@another_username',
            channel_id='529357c3422c6046d3fec76be2358004ba224bcd',
            parent_id=previous_id
        )
        self.assertIsNotNone(reply)
        self.assertEqual(reply['parent_id'], comment['comment_id'])
        self.assertEqual(reply['claim_id'], comment['claim_id'])

    async def test02AnonymousComments(self):
        comment = await db.create_comment_async(
            self.db_path,
            claim_id=self.claimId,
            comment='This is an ANONYMOUS comment'
        )
        self.assertIsNotNone(comment)
        self.assertIsNone(comment['parent_id'])
        previous_id = comment['comment_id']
        reply = await db.create_comment_async(
            self.db_path,
            claim_id=self.claimId,
            comment='This is an unnamed response',
            parent_id=previous_id
        )
        self.assertIsNotNone(reply)
        self.assertEqual(reply['parent_id'], comment['comment_id'])
        self.assertEqual(reply['claim_id'], comment['claim_id'])

    async def test03SignedComments(self):
        comment = await db.create_comment_async(
            self.db_path,
            claim_id=self.claimId,
            comment='I like big butts and i cannot lie',
            channel_name='@sirmixalot',
            channel_id='529357c3422c6046d3fec76be2358005ba22abcd',
            signature='siggy'
        )
        self.assertIsNotNone(comment)
        self.assertIsNone(comment['parent_id'])
        previous_id = comment['comment_id']
        reply = await db.create_comment_async(
            self.db_path,
            claim_id=self.claimId,
            comment='This is a LBRY verified response',
            channel_name='@LBRY',
            channel_id='529357c3422c6046d3fec76be2358001ba224bcd',
            parent_id=previous_id,
            signature='Cursive Font Goes Here'
        )
        self.assertIsNotNone(reply)
        self.assertEqual(reply['parent_id'], comment['comment_id'])
        self.assertEqual(reply['claim_id'], comment['claim_id'])

    async def test04UsernameVariations(self):
        invalid_comment = await db.create_comment_async(
            self.db_path,
            claim_id=self.claimId,
            channel_name='$#(@#$@#$',
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this is an invalid username'
        )
        self.assertIsNone(invalid_comment)
        valid_username = await db.create_comment_async(
            self.db_path,
            claim_id=self.claimId,
            channel_name='@' + 'a'*255,
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this is a valid username'
        )
        self.assertIsNotNone(valid_username)

        lengthy_username = await db.create_comment_async(
            self.db_path,
            claim_id=self.claimId,
            channel_name='@' + 'a'*256,
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this username is too long'
        )
        self.assertIsNone(lengthy_username)
        comment = await db.create_comment_async(
            self.db_path,
            claim_id=self.claimId,
            channel_name='',
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this username should not default to ANONYMOUS'
        )
        self.assertIsNone(comment)
        short_username = await db.create_comment_async(
            self.db_path,
            claim_id=self.claimId,
            channel_name='@',
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this username is too short'
        )
        self.assertIsNone(short_username)

    async def test06GenerateAndListComments(self):
        top_comments, claim_ids = generate_top_comments()
        total, success = 0, 0
        for _, comments in top_comments.items():
            for i, comment in enumerate(comments):
                result = await db.create_comment_async(self.db_path, **comment)
                if result:
                    success += 1
                comments[i] = result
                del comment
            total += len(comments)
        self.assertEqual(total, success)
        self.assertGreater(total, 0)
        success, total = 0, 0
        for reply in generate_replies(top_comments):
            inserted_reply = await db.create_comment_async(self.db_path, **reply)
            if inserted_reply:
                success += 1
            total += 1

        self.assertEqual(success, total)
        self.assertGreater(success, 0)


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


def generate_top_comments(ncid=15, ncomm=100, minchar=50, maxchar=500):
    claim_ids = [fake.sha1() for _ in range(ncid)]
    top_comments = {
        cid: [{
            'claim_id': cid,
            'comment': ''.join(fake.text(max_nb_chars=randint(minchar, maxchar))),
            'channel_name': '@' + fake.user_name(),
            'channel_id': fake.sha1(),
            'signature': fake.uuid4()
        } for _ in range(ncomm)]
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
