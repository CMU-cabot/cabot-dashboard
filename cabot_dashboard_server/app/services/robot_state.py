from datetime import datetime
from typing import Dict, List
from app.utils.logger import logger
from app.config import settings

class RobotStateManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RobotStateManager, cls).__new__(cls)
            cls._instance.connected_cabots = {}
            cls._instance.messages = []
            cls._instance.POLLING_TIMEOUT = settings.polling_timeout
            cls._instance.MAX_MESSAGES = 1000  # Maximum number of messages to retain
        return cls._instance

    def __init__(self):
        # Empty since initialization is done in __new__
        pass

    def update_robot_state(self, client_id: str, state: dict):
        logger.debug(f"Updating state for {client_id}: {state}")
        self.connected_cabots[client_id] = {
            "id": client_id,
            "status": state.get("status", "unknown"),
            "last_poll": datetime.now().isoformat(),
            "message": state.get("message", "")
        }
        logger.debug(f"Updated connected_cabots: {self.connected_cabots}")

    def update_robot_polling(self, client_id: str):
        if client_id in self.connected_cabots:
            self.connected_cabots[client_id].update({
                "status": "connected",
                'last_poll': datetime.now().isoformat()
            })
        else:
            logger.warning(f"Attempted to update status for unknown client: {client_id}")
            raise ValueError(f"Client {client_id} not found")

    def update_robot_status(self, client_id: str, status: str):
        if client_id in self.connected_cabots:
            self.connected_cabots[client_id].update({
                'status': status
            })
        else:
            logger.warning(f"Attempted to update status for unknown client: {client_id}")
            raise ValueError(f"Client {client_id} not found")

    def update_robot_message(self, client_id: str, message: str):
        if client_id in self.connected_cabots:
            self.connected_cabots[client_id].update({
                'message': message
            })
            self.add_message(client_id, message)
        else:
            logger.warning(f"Attempted to update message for unknown client: {client_id}")
            raise ValueError(f"Client {client_id} not found")

    def get_connected_cabots_list(self) -> List[str]:
        cabot_list = []
        for robot_id, info in self.robots.items():
            cabot_list.append({
                'id': robot_id,
                'status': info.get('status', 'unknown'),
                'last_poll': info.get('last_poll'),
                'message': info.get('message', ''),
                'connected': info.get('connected', False)
            })
        return cabot_list

    def get_connected_cabots_list(self) -> list:
        current_time = datetime.now()
        cabot_list = []
        logger.debug(f"Getting all cabots from: {self.connected_cabots}")
        for robot_id, robot_info in self.connected_cabots.items():
            try:
                last_poll = datetime.fromisoformat(robot_info.get('last_poll', ''))
                time_since_last_poll = (current_time - last_poll).seconds
                if robot_info.get('status') is 'connected':
                    is_connected = time_since_last_poll < self.POLLING_TIMEOUT  # Use timeout value
                else:
                    is_connected = False

                cabot_list.append({
                    'id': robot_id,
                    'status': robot_info.get('status', 'unknown'),
                    'last_poll': robot_info.get('last_poll'),
                    'message': robot_info.get('message', ''),
                    'connected': is_connected,
                    'time_since_last_poll': time_since_last_poll,
                    'polling_timeout': self.POLLING_TIMEOUT  # Include timeout value
                })
                logger.debug(f"Added robot {robot_id} to list. Connected: {is_connected}, "
                           f"Last poll: {time_since_last_poll}s ago (timeout: {self.POLLING_TIMEOUT}s)")
            except Exception as e:
                logger.error(f"Error processing robot {robot_id}: {e}")
                cabot_list.append({
                    'id': robot_id,
                    'status': 'error',
                    'message': str(e),
                    'connected': False,
                    'polling_timeout': self.POLLING_TIMEOUT
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

    def add_message(self, client_id: str, message: str):
        timestamp = datetime.now().isoformat()
        new_message = {
            "timestamp": timestamp,
            "client_id": client_id,
            "message": message
        }
        self.messages.append(new_message)
        if len(self.messages) > self.MAX_MESSAGES:
            self.messages = self.messages[-self.MAX_MESSAGES:]

    def get_messages(self, limit: int = 100) -> list:
        return self.messages[-limit:]