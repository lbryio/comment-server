import typing
import random
import asyncio
from aiohttp import web


class FakedCommentServer:
    def __init__(self, port=2903):
        self.port = port
        self.app = web.Application(debug=True)
        self.app.add_routes([web.post('/api', self.api)])
        self.runner = None
        self.server = None

    def get_claim_comments(self, uri: str, better_keys: bool) -> typing.Union[dict, list, None]:
        return [self.get_comment(i) for i in range(75)]

    def get_comment(self, comment_id: int, parent_id: int = None) -> dict:
        return {
            'comment_id': comment_id,
            'parent_id': parent_id,
            'author': f'Person{comment_id}',
            'message': f'comment {comment_id}',
            'claim_id': random.randint(1, 2**16),
            'time_posted': random.randint(2**16, 2**32 - 1),
            'upvotes': random.randint(0, 9999), 'downvotes': random.randint(0, 9999)
        }

    def comment(self, uri: str, poster: str, message: str) -> typing.Union[int, dict, None]:
        if not uri.startswith('lbry://'):
            return {'error': self.ERRORS['INVALID_URI']}
        return random.randint(1, 9999)

    def reply(self, parent_id: int, poster: str, message: str) -> dict:
        if 2 <= len(message) <= 2000 and 2 <= len(poster) <= 127 and parent_id > 0:
            return random.randint(parent_id + 1, 2**32 - 1)
        return {'error': self.ERRORS['INVALID_PARAMS']}

    def get_comment_data(self, comm_index: int, better_keys: bool = False) -> typing.Union[dict, None]:
        return self.get_comment(comm_index)

    def get_comment_replies(self, comm_index: int) -> typing.Union[list, None]:
        return [random.randint(comm_index, comm_index+250) for _ in range(75)]

    methods = {
        'get_claim_comments': get_claim_comments,
        'get_comment_data': get_comment_data,
        'get_comment_replies': get_comment_replies,
        'comment': comment,
        'reply': reply
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
            response['error'] = self.ERRORS['UNKNOWN']
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
            return web.json_response({'error': self.ERRORS['UNKNOWN']})


if __name__ == '__main__':
    app = FakedCommentServer()
    asyncio.run(app.run())
