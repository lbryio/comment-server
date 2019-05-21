import logging
import sqlite3

from src.settings import config

logger = logging.getLogger(__name__)


def setup_database(db_path):
    logger.info('Creating db schema from %s in %s',
                config['PATH']['SCHEMA'], db_path)
    with sqlite3.connect(db_path) as conn:
        with open(config['PATH']['SCHEMA'], 'r') as ddl:
            with conn:
                conn.executescript(ddl.read())


def teardown_database(db_path):
    logger.info('Dropping all tables from %s', db_path)
    with sqlite3.connect(db_path) as conn:
        conn.executescript("""
            DROP VIEW IF EXISTS COMMENTS_ON_CLAIMS;
            DROP VIEW IF EXISTS COMMENT_REPLIES;
            DROP TABLE IF EXISTS COMMENT;
            DROP TABLE IF EXISTS CHANNEL;
        """)


def backup_database(conn: sqlite3.Connection, back_fp):
    with sqlite3.connect(back_fp) as back:
        conn.backup(back)
