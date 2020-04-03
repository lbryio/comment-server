from random import randint
import faker
from faker.providers import internet
from faker.providers import lorem
from faker.providers import misc

from src.database.models import create_comment
from src.database.models import delete_comment
from src.database.models import comment_list, get_comment
from src.database.models import set_hidden_flag
from test.testcase import DatabaseTestCase

fake = faker.Faker()
fake.add_provider(internet)
fake.add_provider(lorem)
fake.add_provider(misc)


class TestDatabaseOperations(DatabaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.claimId = '529357c3422c6046d3fec76be2358004ba22e340'

    def test01NamedComments(self):
        comment = create_comment(
            claim_id=self.claimId,
            comment='This is a named comment',
            channel_name='@username',
            channel_id='529357c3422c6046d3fec76be2358004ba22abcd',
            signature='22'*64,
            signing_ts='aaa'
        )
        self.assertIsNotNone(comment)
        self.assertNotIn('parent_in', comment)

        previous_id = comment['comment_id']
        reply = create_comment(
            claim_id=self.claimId,
            comment='This is a named response',
            channel_name='@another_username',
            channel_id='529357c3422c6046d3fec76be2358004ba224bcd',
            parent_id=previous_id,
            signature='11'*64,
            signing_ts='aaa'
        )
        self.assertIsNotNone(reply)
        self.assertEqual(reply['parent_id'], comment['comment_id'])

    def test02AnonymousComments(self):
        self.assertRaises(
            ValueError,
            create_comment,
            claim_id=self.claimId,
            comment='This is an ANONYMOUS comment'
        )

    def test03SignedComments(self):
        comment = create_comment(
            claim_id=self.claimId,
            comment='I like big butts and i cannot lie',
            channel_name='@sirmixalot',
            channel_id='529357c3422c6046d3fec76be2358005ba22abcd',
            signature='24'*64,
            signing_ts='asdasd'
        )
        self.assertIsNotNone(comment)
        self.assertIn('signing_ts', comment)

        previous_id = comment['comment_id']
        reply = create_comment(
            claim_id=self.claimId,
            comment='This is a LBRY verified response',
            channel_name='@LBRY',
            channel_id='529357c3422c6046d3fec76be2358001ba224bcd',
            parent_id=previous_id,
            signature='12'*64,
            signing_ts='sfdfdfds'
        )
        self.assertIsNotNone(reply)
        self.assertEqual(reply['parent_id'], comment['comment_id'])
        self.assertIn('signing_ts', reply)

    def test04UsernameVariations(self):
        self.assertRaises(
            ValueError,
            create_comment,
            claim_id=self.claimId,
            channel_name='$#(@#$@#$',
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this is an invalid username',
            signature='1' * 128,
            signing_ts='123'
        )

        valid_username = create_comment(
            claim_id=self.claimId,
            channel_name='@' + 'a' * 255,
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this is a valid username',
            signature='1'*128,
            signing_ts='123'
        )
        self.assertIsNotNone(valid_username)

        self.assertRaises(
            ValueError,
            create_comment,
            claim_id=self.claimId,
            channel_name='@' + 'a' * 256,
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this username is too long',
            signature='2' * 128,
            signing_ts='123'
        )

        self.assertRaises(
            ValueError,
            create_comment,
            claim_id=self.claimId,
            channel_name='',
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this username should not default to ANONYMOUS',
            signature='3' * 128,
            signing_ts='123'
        )

        self.assertRaises(
            ValueError,
            create_comment,
            claim_id=self.claimId,
            channel_name='@',
            channel_id='529357c3422c6046d3fec76be2358001ba224b23',
            comment='this username is too short',
            signature='3' * 128,
            signing_ts='123'
        )

    def test05HideComments(self):
        comm = create_comment(
            comment='Comment #1',
            claim_id=self.claimId,
            channel_id='1'*40,
            channel_name='@Doge123',
            signature='a'*128,
            signing_ts='123'
        )
        comment = get_comment(comm['comment_id'])
        self.assertFalse(comment['is_hidden'])

        success = set_hidden_flag([comm['comment_id']])
        self.assertTrue(success)

        comment = get_comment(comm['comment_id'])
        self.assertTrue(comment['is_hidden'])

        success = set_hidden_flag([comm['comment_id']])
        self.assertTrue(success)

        comment = get_comment(comm['comment_id'])
        self.assertTrue(comment['is_hidden'])

    def test06DeleteComments(self):
        # make sure that the comment was created
        comm = create_comment(
            comment='Comment #1',
            claim_id=self.claimId,
            channel_id='1'*40,
            channel_name='@Doge123',
            signature='a'*128,
            signing_ts='123'
        )
        comments = comment_list(self.claimId)
        match = [x for x in comments['items'] if x['comment_id'] == comm['comment_id']]
        self.assertTrue(len(match) > 0)

        deleted = delete_comment(comm['comment_id'])
        self.assertTrue(deleted)

        # make sure that we can't find the comment here
        comments = comment_list(self.claimId)
        match = [x for x in comments['items'] if x['comment_id'] == comm['comment_id']]
        self.assertFalse(match)
        self.assertRaises(
            ValueError,
            delete_comment,
            comment_id=comm['comment_id'],
        )


class ListDatabaseTest(DatabaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        top_coms, self.claim_ids = generate_top_comments(5, 75)

    def testLists(self):
        for claim_id in self.claim_ids:
            with self.subTest(claim_id=claim_id):
                comments = comment_list(claim_id)
                self.assertIsNotNone(comments)
                self.assertGreater(comments['page_size'], 0)
                self.assertIn('has_hidden_comments', comments)
                self.assertFalse(comments['has_hidden_comments'])
                top_comments = comment_list(claim_id, top_level=True, page=1, page_size=50)
                self.assertIsNotNone(top_comments)
                self.assertEqual(top_comments['page_size'], 50)
                self.assertEqual(top_comments['page'], 1)
                self.assertGreaterEqual(top_comments['total_pages'], 0)
                self.assertGreaterEqual(top_comments['total_items'], 0)
                comment_ids = comment_list(claim_id, page_size=50, page=1)
                with self.subTest(comment_ids=comment_ids):
                    self.assertIsNotNone(comment_ids)
                    self.assertLessEqual(len(comment_ids), 50)
                    matching_comments = (comment_ids)
                    self.assertIsNotNone(matching_comments)
                    self.assertEqual(len(matching_comments), len(comment_ids))

    def testHiddenCommentLists(self):
        claim_id = 'a'*40
        comm1 = create_comment(
            'Comment #1',
            claim_id,
            channel_id='1'*40,
            channel_name='@Doge123',
            signature='a'*128,
            signing_ts='123'
        )
        comm2 = create_comment(
            'Comment #2', claim_id,
            channel_id='1'*40,
            channel_name='@Doge123',
            signature='b'*128,
            signing_ts='123'
        )
        comm3 = create_comment(
            'Comment #3', claim_id,
            channel_id='1'*40,
            channel_name='@Doge123',
            signature='c'*128,
            signing_ts='123'
        )
        comments = [comm1, comm2, comm3]

        listed_comments = comment_list(claim_id)
        self.assertEqual(len(comments), listed_comments['total_items'])
        self.assertFalse(listed_comments['has_hidden_comments'])

        set_hidden_flag([comm2['comment_id']])
        hidden = comment_list(claim_id, exclude_mode='hidden')

        self.assertTrue(hidden['has_hidden_comments'])
        self.assertGreater(len(hidden['items']), 0)

        visible = comment_list(claim_id, exclude_mode='visible')
        self.assertFalse(visible['has_hidden_comments'])
        self.assertNotEqual(listed_comments['items'], visible['items'])

        # make sure the hidden comment is the one we marked as hidden
        hidden_comment = hidden['items'][0]
        self.assertEqual(hidden_comment['comment_id'], comm2['comment_id'])

        hidden_ids = [c['comment_id'] for c in hidden['items']]
        visible_ids = [c['comment_id'] for c in visible['items']]
        composite_ids = hidden_ids + visible_ids
        listed_comments = comment_list(claim_id)
        all_ids = [c['comment_id'] for c in listed_comments['items']]
        composite_ids.sort()
        all_ids.sort()
        self.assertEqual(composite_ids, all_ids)


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
