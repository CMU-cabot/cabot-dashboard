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
        """全てのロボットの情報を取得"""
        return self.robots

    def get_connected_cabots_list(self) -> List[str]:
        """接続されているCaBotのリストを取得"""
        return list(self.robots.keys())

    def add_robot(self, robot_id: str, info: dict) -> None:
        """ロボットを追加または更新"""
        self.robots[robot_id] = info
        logger.info(f"Robot {robot_id} added/updated")

    def remove_robot(self, robot_id: str) -> None:
        """ロボットを削除"""
        if robot_id in self.robots:
            del self.robots[robot_id]
            logger.info(f"Robot {robot_id} removed")

    def add_message(self, message: dict) -> None:
        """メッセージを追加"""
        self.messages.append(message)
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)