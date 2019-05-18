import typing
import asyncio
from aiohttp import web

import database as db


ERRORS = {
    'INVALID_PARAMS': {'code': -32602, 'message': 'Invalid parameters'},
    'INTERNAL': {'code': -32603, 'message': 'An internal error'},
    'UNKNOWN': {'code': -1, 'message': 'An unknown or very miscellaneous error'},
}


class CommentServer:
    def __init__(self, port=2903):
        self.port = port
        self.app = web.Application(debug=True)
        self.app.add_routes([web.post('/api', self.api)])
        self.runner = None
        self.server = None

    methods = {
        'get_claim_comments': db.get_claim_comments,
        'get_comment_ids': db.get_comment_ids,
        'get_comments_by_id': db.get_comments_by_id,
        'create_comment': db.create_comment,
    }

    def process_json(self, body) -> dict:
        response = {'jsonrpc': '2.0', 'id': body['id']}
        if body['method'] in self.methods:
            params = body.get('params', {})
            result = self.methods[body['method']](self, **params)
            if type(result) is dict and 'error' in result:
                response['error'] = result['error']
            else:
                response['result'] = result
        else:
            response['error'] = ERRORS['UNKNOWN']
        return response

    async def _start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.server = web.TCPSite(self.runner, 'localhost', self.port)
        await self.server.start()

    async def _stop(self):
        await self.runner.cleanup()

    async def run(self, max_timeout=3600):
        try:
            await self._start()
            await asyncio.sleep(max_timeout)
        except asyncio.CancelledError:
            pass
        finally:
            await self._stop()

    async def api(self, request):
        body = await request.json()
        if type(body) is list or type(body) is dict:
            if type(body) is list:
                response = [self.process_json(part) for part in body]
            else:
                response = self.process_json(body)
            return web.json_response(response)
        else:
            return web.json_response({'error': ERRORS['UNKNOWN']})


if __name__ == '__main__':
    app = CommentServer()
    asyncio.run(app.run())
