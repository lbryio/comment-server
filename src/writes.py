import atexit
import logging

import aiojobs
from asyncio import coroutine

from src.database import obtain_connection, create_comment

logger = logging.getLogger(__name__)


# DatabaseWriter should be instantiated on startup
class DatabaseWriter(object):
    _writer = None

    def __init__(self, db_file):
        if not DatabaseWriter._writer:
            self.conn = obtain_connection(db_file)
            DatabaseWriter._writer = self
            atexit.register(self.cleanup)
            logging.info('Database writer has been created at %s', repr(self))
        else:
            logging.warning('Someone attempted to insantiate DatabaseWriter')
            raise TypeError('Database Writer already exists!')

    def cleanup(self):
        logging.info('Cleaning up database writer')
        DatabaseWriter._writer = None
        self.conn.close()

    @property
    def connection(self):
        return self.conn


async def create_comment_scheduler():
    return await aiojobs.create_scheduler(limit=1, pending_limit=0)


async def write_comment(**comment):
    with DatabaseWriter._writer.connection as conn:
        return await coroutine(create_comment)(conn, **comment)
