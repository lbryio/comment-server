import logging

import aiojobs.aiohttp
import asyncio
from aiohttp import web

from lbry_comment_server.writes import create_comment_scheduler, DatabaseWriter
import schema.db_helpers as helpers
from lbry_comment_server.database import obtain_connection
from lbry_comment_server.handles import api_endpoint
from lbry_comment_server.settings import config

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
    logger.info('Setting up schema in %s', app['db_path'])
    helpers.setup_database(app['db_path'])


async def close_comment_scheduler(app):
    logger.debug('Closing comment_scheduler')
    await app['comment_scheduler'].close()


async def create_database_backup(app):
    try:
        while True:
            await asyncio.sleep(app['config']['BACKUP_INT'])
            with obtain_connection(app['db_path']) as conn:
                logger.debug('%s backing up database')
                helpers.backup_database(conn, app['backup'])

    except asyncio.CancelledError as e:
        pass

async def start_background_tasks(app: web.Application):
    app['waitful_backup'] = app.loop.create_task(create_database_backup(app))
    app['comment_scheduler'] = await create_comment_scheduler()
    app['writer'] = DatabaseWriter(config['PATH']['DEFAULT'])


async def cleanup_background_tasks(app):
    logger.debug('Ending background backup loop')
    app['waitful_backup'].cancel()
    await app['waitful_backup']
    app['reader'].close()
    app['writer'].close()


def create_app(**kwargs):
    app = web.Application()
    app['config'] = config
    app['db_path'] = config['PATH']['DEFAULT']
    app['backup'] = config['PATH']['BACKUP']
    app.on_startup.append(setup_db_schema)
    app.on_startup.append(start_background_tasks)
    app['reader'] = obtain_connection(app['db_path'], True)
    app.on_shutdown.append(close_comment_scheduler)
    app.on_shutdown.append(cleanup_background_tasks)
    aiojobs.aiohttp.setup(app, **kwargs)
    app.add_routes([web.post('/api', api_endpoint)])
    return app


async def stop_app(runner):
    logger.info('stopping app; running cleanup routine')
    await runner.cleanup()


async def run_app(app, duration=3600):
    runner = None
    try:
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, config['HOST'], config['PORT'])
        await site.start()
        await asyncio.sleep(duration)
    except asyncio.CancelledError as cerr:
        pass
    finally:
        await stop_app(runner)


if __name__ == '__main__':
    appl = create_app(close_timeout=5.0)
    try:
        asyncio.run(web.run_app(appl, access_log=logger, host=config['HOST'], port=config['PORT']))
    except asyncio.CancelledError:
        pass
    except ValueError:
        pass
