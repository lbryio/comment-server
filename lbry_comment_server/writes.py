import aiojobs
import atexit
from asyncio import coroutine
import lbry_comment_server.database as db


# DatabaseWriter should be instantiated on startup
class DatabaseWriter(object):
    _writer = None

    def __init__(self, db_file):
        if not DatabaseWriter._writer:
            self.conn = db.obtain_connection(db_file)
            DatabaseWriter._writer = self
            atexit.register(self.cleanup)
        else:
            raise TypeError('Database Writer already exists!')

    def cleanup(self):
        DatabaseWriter._writer = None
        self.conn.close()

    @property
    def connection(self):
        return self.conn


async def create_comment_scheduler():
    return await aiojobs.create_scheduler(limit=1, pending_limit=0)


async def write_comment(**comment):
    with DatabaseWriter._writer.connection as conn:
        return await coroutine(db.create_comment)(conn, **comment)
