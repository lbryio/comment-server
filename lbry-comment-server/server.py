import asyncio
import json

from aiohttp import web

from src import database_dir
from src.database import DatabaseConnection

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
        self.db_conn = DatabaseConnection(database_dir)

    def ping(self):
        return 'pong'

    methods = {
        'ping': ping,
        'get_claim_comments': None,
        'get_comment_ids': None,
        'get_comments_by_id': None,
        'create_comment': None
    }

    __db_methods = {
        'get_claim_comments',
        'get_comment_ids',
        'get_comments_by_id',
        'create_comment'
    }

    def process_json(self, body) -> dict:
        response = {'jsonrpc': '2.0', 'id': body['id']}
        if body['method'] in self.methods:
            method = body['method']
            params = body.get('params', {})
            try:
                if method in self.__db_methods:
                    result = self.db_conn.__getattribute__(method).__call__(**params)
                else:
                    result = self.methods[method](self, **params)
                response['result'] = result
            except TypeError as te:
                print(te)
                response['error'] = ERRORS['INVALID_PARAMS']
        else:
            response['error'] = ERRORS['UNKNOWN']
        return response

    async def _start(self):
        self.db_conn.obtain_connection()
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.server = web.TCPSite(self.runner, 'localhost', self.port)
        await self.server.start()

    async def _stop(self):
        self.db_conn.connection.close()
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
        try:
            body = await request.json()
            if type(body) is list or type(body) is dict:
                if type(body) is list:  # batch request
                    response = [self.process_json(part) for part in body]
                else:  # single rpc request
                    response = self.process_json(body)
                return web.json_response(response)
            else:
                return web.json_response({'error': ERRORS['UNKNOWN']})
        except json.decoder.JSONDecodeError as jde:
            return web.json_response({
                'error': {'message': jde.msg, 'code': -1}
            })



if __name__ == '__main__':
    app = CommentServer()
    asyncio.run(app.run())
