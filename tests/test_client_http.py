"""Local HTTP regression tests. Never connect to a robot or execute commands.

Run with the client requirements installed:
    python -m unittest discover -s tests -v
"""
import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import aiohttp
from aiohttp import web

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cabot_dashboard_client'))
from cabot_dashboard_client import CabotDashboardClient


class ClientHTTPTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.token_requests = 0
        self.poll_requests = 0
        self.sent = []
        app = web.Application()
        app.router.add_post('/oauth/token', self.token)
        app.router.add_post('/api/client/connect/robot-test', self.connect)
        app.router.add_get('/api/client/poll/robot-test', self.poll)
        app.router.add_post('/api/client/send/robot-test', self.send)
        app.router.add_get('/api/client/slow', self.slow)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, '127.0.0.1', 0)
        await site.start()
        port = self.runner.addresses[0][1]
        self.env = patch.dict(os.environ, {
            'CABOT_DASHBOARD_SERVER_URL': f'http://127.0.0.1:{port}',
            'CABOT_DASHBOARD_API_KEY': 'test-key',
            'CABOT_DASHBOARD_CLIENT_ID': 'test-client',
            'CABOT_DASHBOARD_CLIENT_SECRET': 'test-secret',
            'CABOT_DASHBOARD_LOG_LEVEL': 'CRITICAL',
            'CABOT_DASHBOARD_LOG_TO_FILE': 'false',
        })
        self.env.start()
        self.client = CabotDashboardClient('robot-test')
        self.session = aiohttp.ClientSession()

    async def asyncTearDown(self):
        await self.session.close()
        await self.runner.cleanup()
        self.env.stop()

    async def token(self, request):
        form = await request.post()
        self.assertEqual(form['client_id'], 'test-client')
        self.assertEqual(form['client_secret'], 'test-secret')
        self.token_requests += 1
        return web.json_response({'access_token': f'token-{self.token_requests}', 'token_type': 'bearer'})

    async def connect(self, request):
        self.assertEqual(request.headers['X-API-Key'], 'test-key')
        self.assertEqual(request.headers['Authorization'], 'Bearer token-1')
        return web.json_response({'connected': True})

    async def poll(self, request):
        self.poll_requests += 1
        if request.headers['Authorization'] == 'Bearer expired':
            return web.Response(status=401)
        self.assertEqual(await request.json(), {'status': 'active'})
        # Return compressed JSON to exercise aiohttp's HTTP response decoder.
        response = web.json_response({'command': 'dummy'})
        response.enable_compression()
        return response

    async def send(self, request):
        self.sent.append(await request.json())
        return web.json_response({'received': True})

    async def slow(self, request):
        await asyncio.sleep(0.05)
        return web.json_response({})

    async def test_token_connect_poll_and_status(self):
        self.assertTrue(await self.client.connect(self.session))
        status, data = await self.client._make_request(
            self.session, 'get', 'poll/robot-test', {'status': 'active'}, timeout=1)
        self.assertEqual((status, data), (200, {'command': 'dummy'}))
        status, _ = await self.client._make_request(
            self.session, 'post', 'send/robot-test', {'status': 'success'}, timeout=1)
        self.assertEqual(status, 200)
        self.assertEqual(self.sent, [{'status': 'success'}])
        self.assertEqual(self.token_requests, 1)

    async def test_401_refreshes_token_and_retries(self):
        self.client.config.token = 'expired'
        status, data = await self.client._make_request(
            self.session, 'get', 'poll/robot-test', {'status': 'active'}, timeout=1)
        self.assertEqual((status, data), (200, {'command': 'dummy'}))
        self.assertEqual(self.poll_requests, 2)
        self.assertEqual(self.token_requests, 1)

    async def test_timeout_preserves_failure_result(self):
        self.client.config.token = 'unused'
        self.assertEqual(await self.client._make_request(
            self.session, 'get', 'slow', timeout=0.001), (None, None))


if __name__ == '__main__':
    unittest.main()
