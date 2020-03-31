# cython: language_level=3
import asyncio
import logging
import pathlib
import signal
import time

import aiojobs
import aiojobs.aiohttp
from aiohttp import web

from src.database.queries import obtain_connection, DatabaseWriter
from src.database.queries import setup_database
from src.server.handles import api_endpoint, get_api_endpoint

logger = logging.getLogger(__name__)


async def setup_db_schema(app):
    if not pathlib.Path(app['db_path']).exists():
        logger.info(f'Setting up schema in {app["db_path"]}')
        setup_database(app['db_path'])
    else:
        logger.info(f'Database already exists in {app["db_path"]}, skipping setup')


async def start_background_tasks(app):
    # Reading the DB
    app['reader'] = obtain_connection(app['db_path'], True)

    # Scheduler to prevent multiple threads from writing to DB simulataneously
    app['comment_scheduler'] = await aiojobs.create_scheduler(limit=1, pending_limit=0)
    app['db_writer'] = DatabaseWriter(app['db_path'])
    app['writer'] = app['db_writer'].connection

    # for requesting to external and internal APIs
    app['webhooks'] = await aiojobs.create_scheduler(pending_limit=0)


async def close_database_connections(app):
    app['reader'].close()
    app['writer'].close()
    app['db_writer'].cleanup()


async def close_schedulers(app):
    logger.info('Closing comment_scheduler')
    await app['comment_scheduler'].close()

    logger.info('Closing scheduler for webhook requests')
    await app['webhooks'].close()


class CommentDaemon:
    def __init__(self, config, db_file=None, **kwargs):
        app = web.Application()

        # configure the config
        app['config'] = config
        self.config = app['config']

        # configure the db file
        app['db_path'] = db_file or config.get('db_path')

        # configure the order of tasks to run during app lifetime
        app.on_startup.append(setup_db_schema)
        app.on_startup.append(start_background_tasks)
        app.on_shutdown.append(close_schedulers)
        app.on_cleanup.append(close_database_connections)
        aiojobs.aiohttp.setup(app, **kwargs)

        # Configure the routes
        app.add_routes([
            web.post('/api', api_endpoint),
            web.get('/', get_api_endpoint),
            web.get('/api', get_api_endpoint)
        ])
        self.app = app
        self.app_runner = None
        self.app_site = None

    async def start(self, host=None, port=None):
        self.app['start_time'] = time.time()
        self.app_runner = web.AppRunner(self.app)
        await self.app_runner.setup()
        self.app_site = web.TCPSite(
            runner=self.app_runner,
            host=host or self.config['host'],
            port=port or self.config['port'],
        )
        await self.app_site.start()
        logger.info(f'Comment Server is running on {self.config["host"]}:{self.config["port"]}')

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
