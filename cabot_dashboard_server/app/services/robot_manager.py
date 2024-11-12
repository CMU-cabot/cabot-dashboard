from typing import Dict, List
from app.utils.logger import get_logger

logger = get_logger(__name__)

class RobotManager:
    def __init__(self):
        self.robots: Dict[str, dict] = {}
        self.messages: List[dict] = []
        self.max_messages = 100
        logger.info("RobotManager initialized")

    def get_robot_info(self) -> Dict[str, dict]:
        """Get information for all robots"""
        return self.robots

    def get_connected_cabots_list(self) -> List[str]:
        """Get list of connected CaBots"""
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

    def add_robot(self, robot_id: str, info: dict) -> None:
        """Add or update robot"""
        self.robots[robot_id] = info
        logger.info(f"Robot {robot_id} added/updated")

    def remove_robot(self, robot_id: str) -> None:
        """Remove robot"""
        if robot_id in self.robots:
            del self.robots[robot_id]
            logger.info(f"Robot {robot_id} removed")

    def add_message(self, message: dict) -> None:
        """Add message"""
        self.messages.append(message)
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)