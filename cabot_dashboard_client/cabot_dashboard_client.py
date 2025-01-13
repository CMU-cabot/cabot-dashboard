from enum import Enum
import aiohttp
import asyncio
import argparse
import logging
import os
from aiohttp import ClientError
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, Union
import json
import random

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
    debug_mode: bool
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
            client_secret=os.environ.get("CABOT_DASHBOARD_CLIENT_SECRET"),
            debug_mode=os.environ.get('CABOT_DASHBOARD_DEBUG_MODE', 'false').lower() == 'true'
        )

class CommandType(Enum):
    """Supported command types"""
    ROS_START = "ros-start"
    ROS_STOP = "ros-stop"
    SYSTEM_REBOOT = "system-reboot"
    SYSTEM_POWEROFF = "system-poweroff"
    CABOT_IS_ACTIVE = "cabot-is-active"
    SOFTWARE_UPDATE = "software_update"
    GET_IMAGE_TAGS = "get-image-tags"
    DEBUG1 = "debug1"
    DEBUG2 = "debug2"

class SystemCommand:
    """System command execution handler"""
    def __init__(self, cabot_id: str, debug_mode: bool = False):
        self.cabot_id = cabot_id
        self.debug_mode = debug_mode
        self.logger = logging.getLogger(__name__)
        
    async def execute(self, command: list[str], command_type: Optional[CommandType] = None) -> Tuple[bool, Optional[str]]:
        if self.debug_mode:
            # Debug mode handling based on CommandType
            if command_type == CommandType.GET_IMAGE_TAGS:
                self.logger.info("Debug mode: Returning debug image tags")
                # Add 2 seconds delay for debugging
                await asyncio.sleep(2)
                # Return formatted output like actual docker images command
                debug_output = []
                num_images = random.randint(3, 10)
                for i in range(1, num_images + 1):
                    debug_output.append(f"image{i}:tag{i}")
                self.logger.info(f"Debug mode: Generated {num_images} images: {debug_output}")
                return True, "\n".join(debug_output)
            elif command_type == CommandType.CABOT_IS_ACTIVE:
                debug_status = os.environ.get('CABOT_DASHBOARD_DEBUG_STATUS', 'active')
                self.logger.debug(f"Debug mode: Returning status {debug_status}")
                if debug_status == 'active':
                    return True, None
                return False, debug_status

        try:
            self.logger.info(f"Executing command: {' '.join(command)}")
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            stdout_str = stdout.decode().strip()
            stderr_str = stderr.decode().strip()
            self.logger.info(f"Command returncode: {process.returncode}")
            self.logger.info(f"Command stdout: {stdout_str}")
            self.logger.info(f"Command stderr: {stderr_str}")

            if process.returncode == 0:
                return True, stdout_str
            else:
                error_msg = stdout_str or stderr_str or "Unknown error"
                return False, error_msg

        except Exception as e:
            self.logger.error(f"Error executing command: {e}")
            return False, str(e)

    async def execute_software_update(self, images: list[dict]) -> Tuple[bool, Optional[str]]:
        try:
            # Use the existing execute method to run the update command
            update_command = [
                'sudo',
                'systemctl',
                'start',
                f'cabot-software-update@{json.dumps(images)}'  # Pass images as a parameter to the service
            ]
            
            self.logger.info(f"Executing software update with images: {images}")
            return await self.execute(update_command)
            
        except Exception as e:
            self.logger.error(f"Error executing software update: {e}")
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
        self.auth_retry_count = 0
        self.MAX_AUTH_RETRIES = 3
        self.system_command = SystemCommand(cabot_id, self.config.debug_mode)
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
                    'grant_type': 'password',
                    'client_id': self.config.client_id,
                    'client_secret': self.config.client_secret,
                    'username': self.config.client_id,
                    'password': self.config.client_secret
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
            async with getattr(session, method)(url, headers=headers, json=data) as response:
                response_data = await response.json() if response.status == 200 else None
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

    async def send_status(self, session: aiohttp.ClientSession, status: Union[str, Dict]) -> bool:
        """Send status to server
        Args:
            session: aiohttp client session
            status: Status message (string) or status data (dict)
        """
        # If status is already a dict, use it as is, otherwise create a simple message dict
        data = {"message": status} if isinstance(status, str) else status
        self.logger.info(f"Sending status: {json.dumps(data, indent=2)}")
        status_code, _ = await self._make_request(session, 'post', f"send/{self.cabot_id}", data)
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
        self.logger.info(f"Received command: {command}")
        
        try:
            cmd_type = CommandType(command_type)
            
            if cmd_type == CommandType.SOFTWARE_UPDATE:
                images = command.get('commandOption', {}).get('images', [])
                if not images:
                    await self.send_status(session, {
                        "type": "software_update",
                        "status": "error",
                        "message": "No images specified for software update"
                    })
                    return
                
                await self.send_status(session, {
                    "type": "software_update",
                    "status": "start",
                    "message": f"Starting software update for {len(images)} images..."
                })
                success, error = await self.system_command.execute_software_update(images)
                
                if success:
                    await self.send_status(session, {
                        "type": "software_update",
                        "status": "success",
                        "message": "Software update completed successfully"
                    })
                else:
                    await self.send_status(session, {
                        "type": "software_update",
                        "status": "error",
                        "message": f"Software update failed: {error}"
                    })
                return

            if cmd_type == CommandType.GET_IMAGE_TAGS:
                self.logger.info("Starting GET_IMAGE_TAGS command processing")
                await self.send_status(session, {
                    "type": "image_tags",
                    "status": "start",
                    "message": "Getting image tags..."
                })
                # Get docker images tags
                self.logger.info("Executing docker images command")
                success, output = await self.system_command.execute(['docker', 'images', '--format', '{{.Repository}}:{{.Tag}}'], cmd_type)
                self.logger.info(f"Docker images command result - success: {success}, output: {output}")
                
                # Parse the output and create a dictionary of image:tag pairs
                image_tags = {}
                if success and output:
                    for line in output.split('\n'):
                        if line.strip():
                            try:
                                repo_tag = line.strip().split(':')
                                if len(repo_tag) == 2:
                                    if self.config.debug_mode:
                                        # In debug mode, use the image name as is
                                        image_name = repo_tag[0]
                                    else:
                                        # In production mode, get the last part of the image name
                                        image_name = repo_tag[0].split('/')[-1]
                                    image_tags[image_name] = repo_tag[1]
                                    self.logger.info(f"Parsed image tag - name: {image_name}, tag: {repo_tag[1]}")
                            except Exception as e:
                                self.logger.error(f"Error parsing image tag line {line}: {e}")
                    
                    self.logger.info(f"Final parsed image tags: {image_tags}")
                    # Send the image tags back
                    await self.send_status(session, {
                        "type": "image_tags",
                        "status": "success",
                        "tags": image_tags
                    })
                else:
                    error_msg = "No output from docker images command" if not output else f"Error getting image tags: {output}"
                    await self.send_status(session, {
                        "type": "image_tags",
                        "status": "error",
                        "message": error_msg
                    })
                return
            
            command_args = self._command_handlers.get(cmd_type)
            if not command_args:
                await self.send_status(session, {
                    "type": "command",
                    "status": "error",
                    "message": f"Unknown command type: {command_type}"
                })
                return

            await self.send_status(session, {
                "type": "command",
                "status": "start",
                "message": f"Executing {command_type}..."
            })
            success, error = await self.system_command.execute(command_args)

            if success:
                await self.send_status(session, {
                    "type": "command",
                    "status": "success",
                    "message": f"{command_type} completed successfully"
                })
            else:
                await self.send_status(session, {
                    "type": "command",
                    "status": "error",
                    "message": f"Error {command_type}: {error}"
                })

        except ValueError:
            await self.send_status(session, {
                "type": "command",
                "status": "error",
                "message": f"Invalid command type: {command_type}"
            })
        except Exception as e:
            await self.send_status(session, {
                "type": "command",
                "status": "error",
                "message": f"Error executing command {command_type}: {str(e)}"
            })

    async def get_cabot_system_status(self) -> str:
        success, error = await self.system_command.execute(
            ['systemctl', '--user', 'is-active', 'cabot'],
            CommandType.CABOT_IS_ACTIVE
        )
        if not success:
            if not error:
                return "unknown"

            status = error.strip()
            if status == "inactive":
                return "inactive"
            elif status == "failed":
                return "failed"
            elif status == "deactivating":
                return "deactivating"
            else:
                self.logger.info(f"check_service_active unknown status: {status}")
                return "unknown"

        return "active"

    async def run(self) -> None:
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    if await self.connect(session):
                        while True:
                            cabot_system_status = await self.get_cabot_system_status()
                            self.logger.debug(f"Add status to poll request: {cabot_system_status}")
                            status_code, data = await self._make_request(
                                session, 
                                'get', 
                                f"poll/{self.cabot_id}",
                                {"cabot_system_status": cabot_system_status}
                            )

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