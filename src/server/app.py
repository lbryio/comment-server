# cython: language_level=3
import logging
import pathlib
import re
import signal
import time

import aiojobs
import aiojobs.aiohttp
import asyncio
from aiohttp import web

from src.schema.db_helpers import setup_database, backup_database
from src.server.database import obtain_connection, DatabaseWriter
from src.server.handles import api_endpoint, get_api_endpoint

logger = logging.getLogger(__name__)


async def setup_db_schema(app):
    if not pathlib.Path(app['db_path']).exists():
        logger.info('Setting up schema in %s', app['db_path'])
        setup_database(app['db_path'], app['config']['PATH']['SCHEMA'])
    else:
        logger.info(f'Database already exists in {app["db_path"]}, skipping setup')


async def close_comment_scheduler(app):
    logger.info('Closing comment_scheduler')
    await app['comment_scheduler'].close()


async def database_backup_routine(app):
    try:
        while True:
            await asyncio.sleep(app['config']['BACKUP_INT'])
            with app['reader'] as conn:
                logger.debug('backing up database')
                backup_database(conn, app['backup'])
    except asyncio.CancelledError:
        pass


async def start_background_tasks(app):
    app['reader'] = obtain_connection(app['db_path'], True)
    app['waitful_backup'] = app.loop.create_task(database_backup_routine(app))
    app['comment_scheduler'] = await aiojobs.create_scheduler(limit=1, pending_limit=0)
    app['db_writer'] = DatabaseWriter(app['db_path'])
    app['writer'] = app['db_writer'].connection


async def stop_background_tasks(app):
    logger.info('Ending background backup loop')
    app['waitful_backup'].cancel()
    await app['waitful_backup']
    app['reader'].close()
    app['writer'].close()


class CommentDaemon:
    def __init__(self, config, db_path=None, **kwargs):
        self.config = config
        app = web.Application()
        self.insert_to_config(app, config, db_file=db_path)
        app.on_startup.append(setup_db_schema)
        app.on_startup.append(start_background_tasks)
        app.on_shutdown.append(stop_background_tasks)
        app.on_shutdown.append(close_comment_scheduler)
        aiojobs.aiohttp.setup(app, **kwargs)
        app.add_routes([
            web.post('/api', api_endpoint),
            web.get('/', get_api_endpoint),
            web.get('/api', get_api_endpoint)
        ])
        self.app = app
        self.app_runner = web.AppRunner(app)
        self.app_site = None

    async def start(self):
        self.app['START_TIME'] = time.time()
        await self.app_runner.setup()
        self.app_site = web.TCPSite(
            runner=self.app_runner,
            host=self.config['HOST'],
            port=self.config['PORT'],
        )
        await self.app_site.start()
        logger.info(f'Comment Server is running on {self.config["HOST"]}:{self.config["PORT"]}')

    async def stop(self):
        await self.app.shutdown()
        await self.app.cleanup()
        await self.app_runner.cleanup()

    @staticmethod
    def insert_to_config(app, conf=None, db_file=None):
        db_file = db_file if db_file else 'DEFAULT'
        app['config'] = conf
        app['db_path'] = conf['PATH'][db_file]
        app['backup'] = re.sub(r'\.db$', '.backup.db', app['db_path'])
        assert app['db_path'] != app['backup']


def run_app(config):
    comment_app = CommentDaemon(config=config, db_path='DEFAULT', close_timeout=5.0)

    loop =  asyncio.get_event_loop()

    def __exit():
        raise web.GracefulExit()

    loop.add_signal_handler(signal.SIGINT, __exit)
    loop.add_signal_handler(signal.SIGTERM, __exit)

    try:
        loop.run_until_complete(comment_app.start())
        loop.run_forever()
    except (web.GracefulExit, KeyboardInterrupt, asyncio.CancelledError, ValueError):
        logging.warning('Server going down, asyncio loop raised cancelled error:')
    finally:
        loop.run_until_complete(comment_app.stop())