import aiohttp
import asyncio
import logging
import os
from aiohttp import ClientError, ClientConnectorError, ServerDisconnectedError

def setup_logger():
    log_level = os.environ.get('CABOT_DASHBOARD_LOG_LEVEL', 'INFO')
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    logger.handlers.clear()

    log_to_file = os.environ.get('CABOT_DASHBOARD_LOG_TO_FILE', 'false').lower() == 'true'
    log_file = os.environ.get('CABOT_DASHBOARD_LOG_FILE', 'cabot.log')
    handler = logging.FileHandler(log_file) if log_to_file else logging.StreamHandler()

    handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(handler)

    return logger

logger = setup_logger()

class CabotDashboardClient:
    def __init__(self, cabot_id):
        self.cabot_id = cabot_id
        self.base_url = os.environ.get("CABOT_DASHBOARD_SERVER_URL", "http://server:8000")
        self.api_key = os.environ.get("CABOT_DASHBOARD_API_KEY", "your_secret_api_key_here")
        self.max_retries = 5
        self.retry_delay = 5  # seconds
        self.polling_interval = int(os.environ.get("CABOT_DASHBOARD_POLLING_INTERVAL", "1"))
        self.command_queue = asyncio.Queue()
        self.state_update_event = asyncio.Event()

    async def _make_request(self, session, method, endpoint, data=None):
        headers = {"X-API-Key": self.api_key}
        url = f"{self.base_url}/{endpoint}"
        try:
            async with getattr(session, method)(url, headers=headers, json=data) as response:
                return response.status, await response.json() if response.status == 200 else None
        except ClientError as e:
            logger.error(f"CabotDashboardClient {self.cabot_id}: Request error: {e}")
            return None, None

    async def send_status(self, session, status):
        status_code, _ = await self._make_request(session, 'post', f"send/{self.cabot_id}", {"message": status})
        if status_code == 200:
            logger.info(f"CabotDashboardClient {self.cabot_id}: Status sent successfully: {status}")
        else:
            logger.warning(f"CabotDashboardClient {self.cabot_id}: Failed to send status. Status code: {status_code}")

    async def connect(self, session):
        for attempt in range(self.max_retries):
            status_code, _ = await self._make_request(session, 'post', f"connect/{self.cabot_id}")
            if status_code == 200:
                logger.info(f"CabotDashboardClient {self.cabot_id}: Connected to server")
                return True
            elif status_code == 403:
                logger.error(f"CabotDashboardClient {self.cabot_id}: Authentication failed. Please check your API key.")
                return False
            else:
                logger.error(f"CabotDashboardClient {self.cabot_id}: Connection failed. Status: {status_code}")
            
            await asyncio.sleep(self.retry_delay)
        
        logger.error(f"CabotDashboardClient {self.cabot_id}: Failed to connect after {self.max_retries} attempts")
        return False

    async def handle_command(self, session, command):
        logger.info(f"CabotDashboardClient {self.cabot_id}: Processing command: {command}")
        if command == "restart":
            await self.send_status(session, "Restarting...")
            logger.info(f"CabotDashboardClient {self.cabot_id} Restarting...")
            await asyncio.sleep(10)  # Simulating restart time
            logger.info(f"CabotDashboardClient {self.cabot_id} Restart complete.")
            await self.send_status(session, "Restart complete.")
        else:
            logger.warning(f"CabotDashboardClient {self.cabot_id}: Unknown command: {command}")

    async def poll(self, session):
        status_code, data = await self._make_request(session, 'get', f"poll/{self.cabot_id}")
        if status_code == 200:
            logger.info(f"CabotDashboardClient {self.cabot_id}: Received data from server: {data}")
            if data['type'] == 'command':
                await self.handle_command(session, data['data'])
            elif data['type'] == 'state':
                await self.handle_state_update(data['data'])
        elif status_code == 404:
            logger.warning(f"CabotDashboardClient {self.cabot_id}: Not connected to server. Attempting to reconnect...")
            return False
        else:
            logger.warning(f"CabotDashboardClient {self.cabot_id}: Unexpected response status: {status_code}")
        return status_code == 200

    async def run(self):
        async with aiohttp.ClientSession() as session:
            while True:
                if await self.connect(session):
                    try:
                        while await self.poll(session):
                            await self.send_status(session, f"Status update from {self.cabot_id}")
                            await asyncio.sleep(10)  # Status update every 10 seconds
                    except Exception as e:
                        logger.error(f"CabotDashboardClient {self.cabot_id}: Error during polling: {e}")
                await asyncio.sleep(self.retry_delay)

async def main():
    cabots = [CabotDashboardClient(f"cabot{i}") for i in range(1, 4)]
    await asyncio.gather(*(cabot.run() for cabot in cabots))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.critical(f"Unexpected error in main process: {e}")