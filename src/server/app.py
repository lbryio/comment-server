# cython: language_level=3
import logging
import pathlib
import signal
import time

import aiojobs
import aiojobs.aiohttp
import asyncio
from aiohttp import web

from src.database.queries import setup_database, backup_database
from src.database.queries import obtain_connection, DatabaseWriter
from src.server.handles import api_endpoint, get_api_endpoint

logger = logging.getLogger(__name__)


async def setup_db_schema(app):
    if not pathlib.Path(app['db_path']).exists():
        logger.info(f'Setting up schema in {app["db_path"]}')
        setup_database(app['db_path'])
    else:
        logger.info(f'Database already exists in {app["db_path"]}, skipping setup')


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
    app['waitful_backup'] = asyncio.create_task(database_backup_routine(app))
    app['comment_scheduler'] = await aiojobs.create_scheduler(limit=1, pending_limit=0)
    app['db_writer'] = DatabaseWriter(app['db_path'])
    app['writer'] = app['db_writer'].connection


async def close_database_connections(app):
    logger.info('Ending background backup loop')
    app['waitful_backup'].cancel()
    await app['waitful_backup']
    app['reader'].close()
    app['writer'].close()
    app['db_writer'].cleanup()


async def close_comment_scheduler(app):
    logger.info('Closing comment_scheduler')
    await app['comment_scheduler'].close()


class CommentDaemon:
    def __init__(self, config, db_file=None, backup=None, **kwargs):
        self.config = config
        app = web.Application()
        app['config'] = config
        if db_file:
            app['db_path'] = db_file
            app['backup'] = backup
        else:
            app['db_path'] = config['PATH']['DATABASE']
            app['backup'] = backup or (app['db_path'] + '.backup')
        app.on_startup.append(setup_db_schema)
        app.on_startup.append(start_background_tasks)
        app.on_shutdown.append(close_comment_scheduler)
        app.on_cleanup.append(close_database_connections)
        aiojobs.aiohttp.setup(app, **kwargs)
        app.add_routes([
            web.post('/api', api_endpoint),
            web.get('/', get_api_endpoint),
            web.get('/api', get_api_endpoint)
        ])
        self.app = app
        self.app_runner = None
        self.app_site = None

    async def start(self, host=None, port=None):
        self.app['START_TIME'] = time.time()
        self.app_runner = web.AppRunner(self.app)
        await self.app_runner.setup()
        self.app_site = web.TCPSite(
            runner=self.app_runner,
            host=host or self.config['HOST'],
            port=port or self.config['PORT'],
        )
        await self.app_site.start()
        logger.info(f'Comment Server is running on {self.config["HOST"]}:{self.config["PORT"]}')

    async def stop(self):
        await self.app_runner.shutdown()
        await self.app_runner.cleanup()


def run_app(config, db_file=None):
    comment_app = CommentDaemon(config=config, db_file=db_file, close_timeout=5.0)

    loop = asyncio.get_event_loop()

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
