from typing import Dict, List
from datetime import datetime
from app.utils.logger import logger
from app.config import settings
from app.services.websocket import manager as websocket_manager
import asyncio
import json

class RobotStateManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RobotStateManager, cls).__new__(cls)
            cls._instance.connected_cabots = {}
            cls._instance.messages = []  # Initialize messages list
            cls._instance.POLLING_TIMEOUT = settings.polling_timeout
            cls._instance.MAX_MESSAGES = 100  # Maximum number of messages to retain per robot
            cls._instance.DISPLAY_MESSAGES = 5  # Number of messages to display
        for cabot_id in settings.allowed_cabot_id_list:
            cls._instance.connected_cabots[cabot_id] = {
                "id": cabot_id,
                "status": "unknown",
                "system_status": "unknown",
                "last_poll": None,
                "connected": False,
                "images": {},
                "messages": []  # List of messages for each robot
            }
        return cls._instance

    def __init__(self):
        # Empty since initialization is done in __new__
        pass

    async def _notify_state_change(self):
        """Notify all connected dashboard clients about state changes"""
        try:
            message = {
                "type": "robot_state",
                "cabots": self.get_connected_cabots_list(),
                "messages": self.messages
            }
            logger.debug(f"Broadcasting state change: {json.dumps(message, indent=2)}")
            await websocket_manager.broadcast(message)
        except Exception as e:
            logger.error(f"Error broadcasting state change: {e}")

    def update_robot_state(self, client_id: str, state: dict):
        logger.debug(f"Updating state for {client_id}: {state}")
        # Get current state to preserve existing fields
        current_state = self.connected_cabots.get(client_id, {})

        # Update state while preserving messages and other fields
        updated_state = {
            "id": client_id,
            "status": state.get("status", "unknown"),
            "system_status": state.get("system_status", "unknown"),
            "last_poll": datetime.now().isoformat(),
            "connected": True if state.get("status") == "connected" else current_state.get("connected", False),
            "images": current_state.get("images", {}),
            "messages": current_state.get("messages", [])  # Preserve message history
        }

        self.connected_cabots[client_id] = updated_state
        logger.debug(f"Updated connected_cabots: {self.connected_cabots}")
        asyncio.create_task(self._notify_state_change())

    def update_robot_polling(self, client_id: str):
        if client_id in self.connected_cabots:
            current_state = self.connected_cabots[client_id]

            # Create new state with all current values
            updated_state = current_state.copy()
            # Update only the polling-related fields
            updated_state.update({
                "status": "connected",
                'last_poll': datetime.now().isoformat()
            })
            
            # Update the state atomically
            self.connected_cabots[client_id] = updated_state

            asyncio.create_task(self._notify_state_change())
        else:
            logger.warning(f"Attempted to update status for unknown client: {client_id}")
            raise ValueError(f"Client {client_id} not found")

    def update_robot_status(self, client_id: str, status: str):
        if client_id in self.connected_cabots:
            current_state = self.connected_cabots[client_id]

            # Create new state with all current values
            updated_state = current_state.copy()
            # Update only the status
            updated_state['status'] = status

            # Update the state atomically
            self.connected_cabots[client_id] = updated_state
            
            asyncio.create_task(self._notify_state_change())
        else:
            logger.warning(f"Attempted to update status for unknown client: {client_id}")
            raise ValueError(f"Client {client_id} not found")

    @classmethod
    def update_robot_message(cls, cabot_id: str, message: str, level: str = "info"):
        """Update robot message with timestamp"""
        if not cls._instance:
            return

        if cabot_id not in cls._instance.connected_cabots:
            cls._instance.connected_cabots[cabot_id] = {
                "id": cabot_id,
                "status": "unknown",
                "system_status": "unknown",
                "last_poll": None,
                "connected": False,
                "images": {},
                "messages": []
            }

        # Add new message with timestamp
        new_message = {
            "message": message,
            "level": level,
            "timestamp": datetime.now().isoformat()
        }

        # Add to messages list and keep only the latest 100 messages
        robot = cls._instance.connected_cabots[cabot_id]
        robot["messages"].append(new_message)
        if len(robot["messages"]) > 100:
            robot["messages"] = robot["messages"][-100:]

    def update_robot_images(self, client_id: str, images: Dict[str, str]):
        """Update image tags for a robot
        Args:
            client_id (str): Robot ID
            images (Dict[str, str]): Dictionary of image name to tag mapping
        """
        if client_id in self.connected_cabots:
            logger.info(f"Updating images for {client_id}: {images}")
            # Get current state to preserve all fields
            current_state = self.connected_cabots[client_id]

            # Create new state with all current values
            updated_state = current_state.copy()
            # Update only the images
            updated_state['images'] = images

            # Update the state atomically
            self.connected_cabots[client_id] = updated_state

            # Ensure the state change is broadcast
            asyncio.create_task(self._notify_state_change())
        else:
            logger.warning(f"Attempted to update images for unknown client: {client_id}")
            raise ValueError(f"Client {client_id} not found")

    def get_robot_images(self, client_id: str) -> Dict[str, str]:
        """Get image tags for a robot
        Args:
            client_id (str): Robot ID
        Returns:
            Dict[str, str]: Dictionary of image name to tag mapping
        """
        if client_id in self.connected_cabots:
            return self.connected_cabots[client_id].get('images', {})
        else:
            logger.warning(f"Attempted to get images for unknown client: {client_id}")
            raise ValueError(f"Client {client_id} not found")

    def get_connected_cabots_list(self) -> list:
        current_time = datetime.now()
        cabot_list = []
        logger.debug(f"Getting all cabots from: {self.connected_cabots}")
        for robot_id, robot_info in self.connected_cabots.items():
            try:
                last_poll_str = robot_info.get('last_poll')
                if last_poll_str:
                    last_poll = datetime.fromisoformat(last_poll_str)
                    time_since_last_poll = (current_time - last_poll).seconds
                    if robot_info.get('status') == 'connected':
                        is_connected = time_since_last_poll < self.POLLING_TIMEOUT
                    else:
                        is_connected = False
                else:
                    time_since_last_poll = None
                    is_connected = False

                # Get only the latest messages within 5 minutes
                messages = []
                for msg in robot_info.get('messages', []):
                    try:
                        msg_time = datetime.fromisoformat(msg['timestamp'])
                        if (current_time - msg_time).total_seconds() <= 300:  # 5 minutes = 300 seconds
                            messages.append(msg)
                    except Exception as e:
                        logger.error(f"Error processing message timestamp: {e}")

                # Sort messages by timestamp in descending order
                messages = sorted(messages, key=lambda x: x['timestamp'], reverse=True)

                # Limit to DISPLAY_MESSAGES
                messages = messages[:self.DISPLAY_MESSAGES]

                robot_data = {
                    'id': robot_id,
                    'name': robot_id,
                    'status': robot_info.get('status', 'unknown'),
                    'system_status': robot_info.get('system_status', 'unknown'),
                    'last_poll': robot_info.get('last_poll'),
                    'messages': messages,
                    'connected': is_connected,
                    'time_since_last_poll': time_since_last_poll,
                    'polling_timeout': self.POLLING_TIMEOUT,
                    'images': robot_info.get('images', {})
                }

                # Update connected status in robot_info for future reference
                robot_info['connected'] = is_connected

                cabot_list.append(robot_data)
                logger.debug(f"Added robot {robot_id} to list. Connected: {is_connected}, "
                           f"Last poll: {time_since_last_poll}s ago (timeout: {self.POLLING_TIMEOUT}s)")
            except Exception as e:
                logger.error(f"Error processing robot {robot_id}: {e}")
                cabot_list.append({
                    'id': robot_id,
                    'name': robot_id,
                    'status': 'error',
                    'system_status': 'unknown',
                    'message': str(e),
                    'connected': False,
                    'polling_timeout': self.POLLING_TIMEOUT,
                    'images': {},
                    'messages': []
                })
        logger.debug(f"Returning all cabots: {cabot_list}")
        return cabot_list

    async def send_command(self, robot_id: str, command: Dict) -> None:
        if robot_id not in self.connected_cabots:
            raise ValueError(f"Robot {robot_id} not connected")
        self.connected_cabots[robot_id].update({
            'last_command': datetime.now().isoformat(),
            'last_command_type': command.get('type')
        })
        asyncio.create_task(self._notify_state_change())

    def add_message(self, client_id: str, message: str, level: str = "info"):
        timestamp = datetime.now().isoformat()
        
        new_message = {
            "timestamp": timestamp,
            "client_id": client_id,
            "message": message,
            "level": level
        }
        self.messages.append(new_message)
        if len(self.messages) > self.MAX_MESSAGES:
            self.messages = self.messages[-self.MAX_MESSAGES:]
        asyncio.create_task(self._notify_state_change())

    def get_messages(self, limit: int = 5) -> list:
        """Get latest messages
        Args:
            limit (int): Number of messages to return (default: 5)
        Returns:
            list: List of messages, newest first
        """
        return sorted(self.messages[-limit:], key=lambda x: x['timestamp'], reverse=True)

    @classmethod
    def get_robot_state(cls, cabot_id: str) -> dict:
        """Get robot state including latest messages"""
        if not cls._instance or cabot_id not in cls._instance.connected_cabots:
            return None

        robot_state = cls._instance.connected_cabots[cabot_id].copy()
        # Sort messages by timestamp in descending order
        robot_state["messages"] = sorted(
            robot_state["messages"],
            key=lambda x: x["timestamp"],
            reverse=True
        )
        return robot_state