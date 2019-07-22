import logging
import sqlite3

logger = logging.getLogger(__name__)


def setup_database(db_path, schema_path):
    logger.info(f'Creating db schema from {schema_path} in {db_path}')
    with sqlite3.connect(db_path) as conn:
        with open(schema_path, 'r') as ddl:
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
