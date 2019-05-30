# cython: language_level=3
import logging
import pathlib
import re

import aiojobs.aiohttp
import asyncio
from aiohttp import web

import schema.db_helpers
from src.database import obtain_connection
from src.handles import api_endpoint
from src.handles import create_comment_scheduler
from src.settings import config_path, get_config
from src.writes import DatabaseWriter

config = get_config(config_path)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(config['LOGGING_FORMAT'])
debug_handler = logging.FileHandler(config['PATH']['LOG'])
error_handler = logging.FileHandler(config['PATH']['ERROR_LOG'])
stdout_handler = logging.StreamHandler()

debug_handler.setLevel(logging.DEBUG)
error_handler.setLevel(logging.ERROR)
stdout_handler.setLevel(logging.DEBUG)

debug_handler.setFormatter(formatter)
error_handler.setFormatter(formatter)
stdout_handler.setFormatter(formatter)

logger.addHandler(debug_handler)
logger.addHandler(error_handler)
logger.addHandler(stdout_handler)


async def setup_db_schema(app):
    if not pathlib.Path(app['db_path']).exists():
        logger.info('Setting up schema in %s', app['db_path'])
        schema.db_helpers.setup_database(app['db_path'])
    else:
        logger.info('Database already exists in %s, skipping setup', app['db_path'])


async def close_comment_scheduler(app):
    logger.debug('Closing comment_scheduler')
    await app['comment_scheduler'].close()


async def create_database_backup(app):
    try:
        while True:
            await asyncio.sleep(app['config']['BACKUP_INT'])
            with obtain_connection(app['db_path']) as conn:
                logger.debug('backing up database')
                schema.db_helpers.backup_database(conn, app['backup'])

    except asyncio.CancelledError as e:
        pass


async def start_background_tasks(app: web.Application):
    app['waitful_backup'] = app.loop.create_task(create_database_backup(app))
    app['comment_scheduler'] = await create_comment_scheduler()
    app['writer'] = DatabaseWriter(app['db_path'])


def insert_to_config(app, conf=None, db_file=None):
    db_file = db_file if db_file else 'DEFAULT'
    app['config'] = conf if conf else config
    app['db_path'] = conf['PATH'][db_file]
    app['backup'] = re.sub(r'\.db$', '.backup.db', app['db_path'])
    assert app['db_path'] != app['backup']


async def cleanup_background_tasks(app):
    logger.debug('Ending background backup loop')
    app['waitful_backup'].cancel()
    await app['waitful_backup']
    app['reader'].close()
    app['writer'].close()


def create_app(conf, db_path='DEFAULT', **kwargs):
    app = web.Application()
    insert_to_config(app, conf, db_path)
    app.on_startup.append(setup_db_schema)
    app.on_startup.append(start_background_tasks)
    app['reader'] = obtain_connection(app['db_path'], True)
    app.on_shutdown.append(close_comment_scheduler)
    app.on_shutdown.append(cleanup_background_tasks)
    aiojobs.aiohttp.setup(app, **kwargs)
    app.add_routes([web.post('/api', api_endpoint)])
    return app


def run_app():
    appl = create_app(conf=config, db_path='DEFAULT', close_timeout=5.0)
    try:
        asyncio.run(web.run_app(appl, access_log=logger, host=config['HOST'], port=config['PORT']))
    except asyncio.CancelledError:
        pass
    except ValueError:
        pass
