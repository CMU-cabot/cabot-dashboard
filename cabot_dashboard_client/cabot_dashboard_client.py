from enum import Enum
import aiohttp
import asyncio
import argparse
import logging
import os
from aiohttp import ClientError
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any

@dataclass
class Config:
    """Configuration data class"""
    log_level: str
    log_to_file: bool
    log_file: str
    server_url: str
    api_key: str
    max_retries: int
    retry_delay: int
    polling_interval: int
    client_id: str
    client_secret: str
    token: Optional[str] = None
    token_type: Optional[str] = None

    @classmethod
    def from_env(cls) -> 'Config':
        """Load configuration from environment variables"""
        return cls(
            log_level=os.environ.get('CABOT_DASHBOARD_LOG_LEVEL', 'INFO'),
            log_to_file=os.environ.get('CABOT_DASHBOARD_LOG_TO_FILE', 'false').lower() == 'true',
            log_file=os.environ.get('CABOT_DASHBOARD_LOG_FILE', 'cabot.log'),
            server_url=os.environ.get("CABOT_DASHBOARD_SERVER_URL", "http://localhost:8000"),
            api_key=os.environ.get("CABOT_DASHBOARD_API_KEY", "your_secret_api_key_here"),
            max_retries=int(os.environ.get("CABOT_DASHBOARD_MAX_RETRIES", "5")),
            retry_delay=int(os.environ.get("CABOT_DASHBOARD_RETRY_DELAY", "5")),
            polling_interval=int(os.environ.get("CABOT_DASHBOARD_POLLING_INTERVAL", "1")),
            client_id=os.environ.get("CABOT_DASHBOARD_CLIENT_ID"),
            client_secret=os.environ.get("CABOT_DASHBOARD_CLIENT_SECRET")
        )

class CommandType(Enum):
    """Supported command types"""
    ROS_START = "ros-start"
    ROS_STOP = "ros-stop"
    SYSTEM_REBOOT = "system-reboot"
    SYSTEM_POWEROFF = "system-poweroff"
    DEBUG1 = "debug1"
    DEBUG2 = "debug2"

class SystemCommand:
    """System command execution handler"""
    def __init__(self, cabot_id: str):
        self.cabot_id = cabot_id
        
    async def execute(self, command: list[str]) -> Tuple[bool, Optional[str]]:
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            return (True, None) if process.returncode == 0 else (False, stderr.decode() if stderr else "Unknown error")
        except Exception as e:
            return False, str(e)

def setup_logger(config: Config) -> logging.Logger:
    logger = logging.getLogger(__name__)
    logger.setLevel(config.log_level)
    logger.handlers.clear()

    handler = logging.FileHandler(config.log_file) if config.log_to_file else logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S'))
    logger.addHandler(handler)
    
    logger.debug("Logger initialized with:")
    logger.debug(f"- Log level: {config.log_level}")
    logger.debug(f"- Server URL: {config.server_url}")
    logger.debug(f"- API Key: {config.api_key[:4]}..." if config.api_key else "- API Key: Not set")
    
    return logger

class CabotDashboardClient:
    def __init__(self, cabot_id: str):
        self.cabot_id = cabot_id
        self.config = Config.from_env()
        self.logger = setup_logger(self.config)
        self.system_command = SystemCommand(cabot_id)
        self.auth_retry_count = 0
        self.MAX_AUTH_RETRIES = 3
        self._command_handlers = {
            CommandType.ROS_START: ['systemctl', '--user', 'start', 'cabot'],
            CommandType.ROS_STOP: ['systemctl', '--user', 'stop', 'cabot'],
            CommandType.SYSTEM_REBOOT: ['sudo', 'systemctl', 'reboot'],
            CommandType.SYSTEM_POWEROFF: ['sudo', 'systemctl', 'poweroff'],
            CommandType.DEBUG1: ['systemctl', '--user', 'restart', 'myapp'],
            CommandType.DEBUG2: ['sudo', 'systemctl', 'restart', 'cron']
        }

    async def _get_token(self) -> None:
        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    'grant_type': 'client_credentials',
                    'client_id': self.config.client_id,
                    'client_secret': self.config.client_secret,
                }
                
                self.logger.debug(f"Requesting token from {self.config.server_url}/oauth/token")
                self.logger.debug(f"Client ID: {self.config.client_id}")
                
                async with session.post(
                    f"{self.config.server_url}/oauth/token",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                ) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        self.config.token = token_data['access_token']
                        self.config.token_type = token_data['token_type']
                        self.logger.debug("Token obtained successfully")
                    else:
                        response_text = await response.text()
                        self.logger.error(f"Failed to get token. Status: {response.status}, Response: {response_text}")
                        raise Exception(f"Failed to get access token: {response_text}")
        except Exception as e:
            self.logger.error(f"Token request failed: {str(e)}")
            raise

    async def _make_request(self, session: aiohttp.ClientSession, method: str, endpoint: str, data: Optional[Dict] = None) -> Tuple[Optional[int], Optional[Dict]]:
        if not self.config.token:
            await self._get_token()
        
        if not self.config.api_key:
            self.logger.error("API key is not configured")
            return None, None
            
        headers = {
            "Authorization": f"Bearer {self.config.token}",
            "X-API-Key": self.config.api_key,
            "Content-Type": "application/json"
        }
        
        url = f"{self.config.server_url}/api/client/{endpoint}"
        self.logger.debug(f"Making request to {url} with API key: {self.config.api_key[:4]}...")
        
        try:
            async with session.request(method, url, json=data, headers=headers) as response:
                response_text = await response.text()
                self.logger.debug(f"Response status: {response.status}, body: {response_text}")
                
                if response.status == 401:
                    self.logger.warning("Token expired, refreshing...")
                    await self._get_token()
                    headers["Authorization"] = f"Bearer {self.config.token}"
                    async with session.request(method, url, json=data, headers=headers) as retry_response:
                        return retry_response.status, await retry_response.json() if retry_response.status == 200 else None
                return response.status, await response.json() if response.status == 200 else None
        except Exception as e:
            self.logger.error(f"Request error: {str(e)}")
            return None, None

    async def send_status(self, session: aiohttp.ClientSession, status: str) -> bool:
        status_code, _ = await self._make_request(session, 'post', f"send/{self.cabot_id}", {"message": status})
        if status_code == 404:
            return False
        return True

    async def connect(self, session: aiohttp.ClientSession) -> bool:
        for attempt in range(self.config.max_retries):
            status_code, _ = await self._make_request(session, 'post', f"connect/{self.cabot_id}")
            if status_code == 200:
                return True
            elif status_code == 403:
                return False
            await asyncio.sleep(self.config.retry_delay)
        return False

    async def handle_command(self, session: aiohttp.ClientSession, command: Dict[str, Any]) -> None:
        command_type = command.get('command')
        try:
            cmd_type = CommandType(command_type)
            command_args = self._command_handlers.get(cmd_type)
            
            if not command_args:
                await self.send_status(session, f"Unknown command type: {command_type}")
                return

            await self.send_status(session, f"Executing {command_type}...")
            success, error = await self.system_command.execute(command_args)

            if success:
                await self.send_status(session, f"{command_type} completed successfully")
            else:
                await self.send_status(session, f"Error {command_type}: {error}")

        except ValueError:
            await self.send_status(session, f"Invalid command type: {command_type}")
        except Exception as e:
            await self.send_status(session, f"Error executing command {command_type}: {str(e)}")

    async def run(self) -> None:
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    if await self.connect(session):
                        while True:
                            status_code, data = await self._make_request(session, 'get', f"poll/{self.cabot_id}")
                            
                            if status_code == 200:
                                await self.handle_command(session, data)
                            elif status_code == 404:
                                break
                                
                            await asyncio.sleep(self.config.polling_interval)
                            
                    await asyncio.sleep(self.config.retry_delay)
                    
                except Exception:
                    await asyncio.sleep(self.config.retry_delay)

async def main():
    parser = argparse.ArgumentParser(description='CaBot Dashboard Client')
    parser.add_argument('-s', '--simulate', type=int, help='Simulation mode: specify number of clients to generate')
    args = parser.parse_args()

    if args.simulate:
        clients = [CabotDashboardClient(f"cabot_{i+1}").run() for i in range(args.simulate)]
        await asyncio.gather(*clients)
    else:
        cabot_id = os.environ.get("CABOT_DASHBOARD_CABOT_ID")
        if not cabot_id:
            logging.error("Environment variable CABOT_ID is not set")
            return
        
        client = CabotDashboardClient(cabot_id)
        await client.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.critical(f"Unexpected error in main process: {e}")