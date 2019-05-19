import unittest
import server.conf
import server.database as db
import sqlite3
import json


class TestCommentCreation(unittest.TestCase):
    def setUp(self) -> None:
        self.db = db.DatabaseConnection('test.db')
        self.db.obtain_connection()
        self.db.generate_schema(server.conf.schema_dir)
        self.claimId = '529357c3422c6046d3fec76be2358004ba22e340'

    def tearDown(self) -> None:
        curs = self.db.connection.execute('SELECT * FROM COMMENT')
        results = {'COMMENT': [dict(r) for r in curs.fetchall()]}
        curs = self.db.connection.execute('SELECT * FROM CHANNEL')
        results['CHANNEL'] = [dict(r) for r in curs.fetchall()]
        curs = self.db.connection.execute('SELECT * FROM COMMENTS_ON_CLAIMS')
        results['COMMENTS_ON_CLAIMS'] = [dict(r) for r in curs.fetchall()]
        curs = self.db.connection.execute('SELECT * FROM COMMENT_REPLIES')
        results['COMMENT_REPLIES'] = [dict(r) for r in curs.fetchall()]
        print(json.dumps(results, indent=4))
        conn: sqlite3.Connection = self.db.connection
        conn.executescript("""
            DROP TABLE IF EXISTS COMMENT;
            DROP TABLE IF EXISTS CHANNEL;
            DROP VIEW IF EXISTS COMMENTS_ON_CLAIMS;
            DROP VIEW IF EXISTS COMMENT_REPLIES;
        """)
        conn.commit()
        conn.close()

    def testNamedComments(self):
        comment = self.db.create_comment(
            claim_id=self.claimId,
            comment='This is a named comment',
            channel_name='username',
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
            channel_name='another_username',
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
            channel_name='sirmixalot',
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
            channel_name='LBRY',
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

