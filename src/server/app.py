# cython: language_level=3
import asyncio
import logging
import signal
import time

import aiojobs
import aiojobs.aiohttp
from aiohttp import web

from peewee import *
from src.server.handles import api_endpoint, get_api_endpoint
from src.database.models import Comment, Channel

MODELS = [Comment, Channel]
logger = logging.getLogger(__name__)


def setup_database(app):
    config = app['config']
    mode = config['mode']

    # switch between Database objects
    if config[mode]['database'] == 'mysql':
        app['db'] = MySQLDatabase(
            database=config[mode]['name'],
            user=config[mode]['user'],
            host=config[mode]['host'],
            password=config[mode]['password'],
            port=config[mode]['port'],
        )
    elif config[mode]['database'] == 'sqlite':
        app['db'] = SqliteDatabase(
            config[mode]['file'],
            pragmas=config[mode]['pragmas']
        )

    # bind the Model list to the database
    app['db'].bind(MODELS, bind_refs=False, bind_backrefs=False)


async def start_background_tasks(app):
    app['db'].connect()
    app['db'].create_tables(MODELS)

    # for requesting to external and internal APIs
    app['webhooks'] = await aiojobs.create_scheduler(pending_limit=0)


async def close_database_connections(app):
    app['db'].close()


async def close_schedulers(app):
    logger.info('Closing scheduler for webhook requests')
    await app['webhooks'].close()


class CommentDaemon:
    def __init__(self, config, **kwargs):
        app = web.Application()
        app['config'] = config

        # configure the config
        self.config = config
        self.host = config['host']
        self.port = config['port']

        setup_database(app)

        # configure the order of tasks to run during app lifetime
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
            host=host or self.host,
            port=port or self.port,
        )
        await self.app_site.start()
        logger.info(f'Comment Server is running on {self.host}:{self.port}')

    async def stop(self):
        await self.app_runner.shutdown()
        await self.app_runner.cleanup()


def run_app(config):
    comment_app = CommentDaemon(config=config)
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
