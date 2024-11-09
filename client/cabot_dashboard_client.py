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

    async def _make_request(self, session, method, endpoint, data=None):
        headers = {"X-API-Key": self.api_key}
        url = f"{self.base_url}/api/client/{endpoint}"
        try:
            async with getattr(session, method)(url, headers=headers, json=data) as response:
                return response.status, await response.json() if response.status == 200 else None
        except ClientError as e:
            logger.error(f"CabotDashboardClient {self.cabot_id}: Request error: {e}")
            return None, None

    async def send_status(self, session, status):
        status_code, response = await self._make_request(session, 'post', f"send/{self.cabot_id}", {"message": status})
        if status_code == 200:
            logger.info(f"CabotDashboardClient {self.cabot_id}: Status sent successfully: {status}")
        elif status_code == 404:
            logger.error(f"CabotDashboardClient {self.cabot_id}: Endpoint not found. URL: {self.base_url}/api/client/send/{self.cabot_id}")
            # 接続が切れた可能性があるため、再接続を促す
            return False
        else:
            logger.warning(f"CabotDashboardClient {self.cabot_id}: Failed to send status. Status code: {status_code}")
        return True

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
        
        if not isinstance(command, dict):
            logger.error(f"CabotDashboardClient {self.cabot_id}: Invalid command format: {command}")
            await self.send_status(session, "Error: Invalid command format")
            return

        command_type = command.get('command')
        command_option = command.get('commandOption', {})

        if command_type == "start":
            process_name = command_option.get('ProcessName')
            if not process_name:
                logger.error(f"CabotDashboardClient {self.cabot_id}: ProcessName not specified in command")
                await self.send_status(session, "Error: ProcessName not specified")
                return

            await self.send_status(session, f"Restarting {process_name}...")
            try:
                process = await asyncio.create_subprocess_exec(
                    'sudo', 'systemctl', 'restart', process_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    logger.info(f"CabotDashboardClient {self.cabot_id}: Successfully restarted {process_name}")
                    await self.send_status(session, f"{process_name} restart completed successfully")
                else:
                    error_msg = stderr.decode() if stderr else "Unknown error"
                    logger.error(f"CabotDashboardClient {self.cabot_id}: Failed to restart {process_name}: {error_msg}")
                    await self.send_status(session, f"Error restarting {process_name}: {error_msg}")
            
            except Exception as e:
                logger.error(f"CabotDashboardClient {self.cabot_id}: Error executing systemctl: {str(e)}")
                await self.send_status(session, f"Error executing restart command: {str(e)}")
        
        elif command_type == "stop":
            process_name = command_option.get('ProcessName')
            if not process_name:
                logger.error(f"CabotDashboardClient {self.cabot_id}: ProcessName not specified in command")
                await self.send_status(session, "Error: ProcessName not specified")
                return

            await self.send_status(session, f"Stopping {process_name}...")
            # ここにプロセス停止のロジックを追加

        elif command_type == "debug":
            message = command_option.get('message', 'No message provided')
            logger.debug(f"CabotDashboardClient {self.cabot_id}: Debug message received: {message}")
            await self.send_status(session, f"Debug message processed: {message}")

        else:
            logger.warning(f"CabotDashboardClient {self.cabot_id}: Unknown command type: {command_type}")
            await self.send_status(session, f"Unknown command type: {command_type}")

    async def run(self):
        """メインループ"""
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    if await self.connect(session):
                        logger.info(f"CabotDashboardClient {self.cabot_id}: Connected to server")
                        
                        # ポーリングループ
                        polling_count = 0
                        while True:
                            try:
                                polling_count += 1
                                logger.info(f"CabotDashboardClient {self.cabot_id}: Polling attempt {polling_count}")
                                
                                status_code, data = await self._make_request(session, 'get', f"poll/{self.cabot_id}")
                                logger.debug(f"CabotDashboardClient {self.cabot_id}: Poll response - Status: {status_code}, Data: {data}")
                                
                                if status_code == 200:
                                    logger.info(f"CabotDashboardClient {self.cabot_id}: Received command - {data}")
                                    await self.handle_command(session, data)
                                elif status_code == 404:
                                    logger.warning(f"CabotDashboardClient {self.cabot_id}: Connection lost, attempting to reconnect...")
                                    break
                                else:
                                    logger.warning(f"CabotDashboardClient {self.cabot_id}: Unexpected response status: {status_code}")
                                
                                # ステータス更新を送信
                                await self.send_status(session, f"Status update {polling_count} from {self.cabot_id}")
                                
                                # ポーリング間隔を待機
                                logger.debug(f"CabotDashboardClient {self.cabot_id}: Waiting {self.polling_interval} seconds before next poll")
                                await asyncio.sleep(self.polling_interval)
                                
                            except Exception as e:
                                logger.error(f"CabotDashboardClient {self.cabot_id}: Error during polling: {e}")
                                break
                    
                    # 接続に失敗した場合は再試行
                    logger.info(f"CabotDashboardClient {self.cabot_id}: Waiting {self.retry_delay} seconds before reconnection attempt")
                    await asyncio.sleep(self.retry_delay)
                    
                except Exception as e:
                    logger.error(f"CabotDashboardClient {self.cabot_id}: Unexpected error: {e}")
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