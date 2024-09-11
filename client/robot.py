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
    if log_to_file:
        handler = logging.FileHandler(os.environ.get('CABOT_DASHBOARD_LOG_FILE', 'robot.log'))
    else:
        handler = logging.StreamHandler()

    handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(handler)

    return logger

logger = setup_logger()

class Robot:
    def __init__(self, robot_id):
        self.robot_id = robot_id
        self.base_url = os.environ.get("CABOT_DASHBOARD_SERVER_URL", "http://server:8000")
        self.api_key = os.environ.get("CABOT_DASHBOARD_API_KEY", "your_secret_api_key_here")
        self.max_retries = 5
        self.retry_delay = 5  # seconds

    async def send_status(self, session, status):
        headers = {"X-API-Key": self.api_key}
        try:
            async with session.post(f"{self.base_url}/send/{self.robot_id}", headers=headers, json={"message": status}) as response:
                if response.status != 200:
                    logger.warning(f"Robot {self.robot_id}: Failed to send status")
        except aiohttp.ClientError as e:
            logger.error(f"Robot {self.robot_id}: Failed to send status: {e}")

    async def connect(self, session):
        headers = {"X-API-Key": self.api_key}
        for attempt in range(self.max_retries):
            try:
                async with session.post(f"{self.base_url}/connect/{self.robot_id}", headers=headers) as response:
                    if response.status == 200:
                        logger.info(f"Robot {self.robot_id}: Connected to server")
                        return True
                    elif response.status == 403:
                        logger.error(f"Robot {self.robot_id}: Authentication failed. Check API key.")
                        return False
                    else:
                        logger.error(f"Robot {self.robot_id}: Failed to connect. Status: {response.status}")
            except (ClientConnectorError, ServerDisconnectedError, ClientError) as e:
                logger.error(f"Robot {self.robot_id}: Connection error: {e}. Retrying in {self.retry_delay} seconds...")
            except Exception as e:
                logger.error(f"Robot {self.robot_id}: Unexpected error: {e}")
            
            await asyncio.sleep(self.retry_delay)
        
        logger.error(f"Robot {self.robot_id}: Failed to connect after {self.max_retries} attempts")
        return False

    async def handle_command(self, session, command):
        if command == "restart":
            await self.send_status(session, "Restarting...")
            logger.info(f"Robot {self.robot_id} is restarting...")
            for i in range(10, 0, -1):
                logger.info(f"Robot {self.robot_id} will restart in {i} seconds...")
                await asyncio.sleep(1)
            logger.info(f"Robot {self.robot_id} has restarted.")
            await self.send_status(session, "Restart complete.")

    async def poll(self, session):
        headers = {"X-API-Key": self.api_key}
        try:
            async with session.get(f"{self.base_url}/poll/{self.robot_id}", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    message = data.get("message")
                    if message:
                        logger.info(f"Robot {self.robot_id} received command: {message}")
                        await self.handle_command(session, message)
                elif response.status == 404:
                    logger.warning(f"Robot {self.robot_id}: Not connected to server. Reconnecting...")
                    return False
                else:
                    logger.warning(f"Robot {self.robot_id}: Unexpected response status: {response.status}")
        except aiohttp.ClientError as e:
            logger.error(f"Robot {self.robot_id}: Polling error: {e}")
            return False
        return True

    async def run(self):
        async with aiohttp.ClientSession() as session:
            while True:
                if await self.connect(session):
                    try:
                        while await self.poll(session):
                            await asyncio.sleep(1)
                    except Exception as e:
                        logger.error(f"Robot {self.robot_id}: Error during polling: {e}")
                await asyncio.sleep(self.retry_delay)

async def main():
    robots = [Robot(f"robot{i}") for i in range(1, 4)]
    await asyncio.gather(*(robot.run() for robot in robots))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.critical(f"Unexpected error in main: {e}")