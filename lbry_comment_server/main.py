import asyncio
from aiohttp import web
import aiojobs.aiohttp

import schema.db_helpers as helpers
import lbry_comment_server.writes as writes
from lbry_comment_server.settings import config
from lbry_comment_server.handles import api_endpoint


async def setup_db_schema(app):
    helpers.setup_database(app['db_path'])


async def close_comment_scheduler(app):
    await app['comment_scheduler'].close()


def create_app(**kwargs):
    app = web.Application()
    app['config'] = config
    app['db_path'] = config['PATH']['DEFAULT']
    app['backup'] = config['PATH']['BACKUP']
    app.on_startup.append(setup_db_schema)
    app.on_shutdown.append(close_comment_scheduler)
    aiojobs.aiohttp.setup(app, **kwargs)
    app.add_routes([web.post('/api', api_endpoint)])
    return app


async def stop_app(runner):
    await runner.cleanup()


async def run_app(app, duration=3600):
    app['comment_scheduler'] = await writes.create_comment_scheduler()
    app['writer'] = writes.DatabaseWriter(config['PATH']['DEFAULT'])
    runner = None
    try:
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, config['HOST'], config['PORT'])
        await site.start()
        await asyncio.sleep(duration)
    except asyncio.CancelledError:
        pass
    finally:
        await stop_app(runner)


if __name__ == '__main__':
    appl = create_app(close_timeout=5.0)
    asyncio.run(run_app(appl))
