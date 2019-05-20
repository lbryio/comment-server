from aiohttp import web

from lbry_comment_server import api_endpoint


def add_routes(app: web.Application):
    app.add_routes([web.post('/api', api_endpoint)])
