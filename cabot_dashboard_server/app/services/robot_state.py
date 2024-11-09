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
            cls._instance.MAX_MESSAGES = 1000  # メッセージの最大保持数
        return cls._instance

    def __init__(self):
        # __new__で初期化するため、ここは空でOK
        pass

    def get_robot_info(self) -> Dict:
        """全てのロボットの情報を取得"""
        current_time = datetime.now()
        robot_info = {}
        
        for robot_id, state in self.connected_cabots.items():
            # 最後のポーリングから一定時間（POLLING_TIMEOUT）以内のものを接続中とみなす
            last_poll = datetime.fromisoformat(state.get('last_poll', current_time.isoformat()))
            is_connected = (current_time - last_poll).seconds < self.POLLING_TIMEOUT
            
            robot_info[robot_id] = {
                'status': state.get('status', 'unknown'),
                'connected': is_connected,
                'last_poll': state.get('last_poll'),
                'message': state.get('message', '')
            }
        
        return {
            'robots': robot_info,
            'messages': self.messages[-10:]  # 最新10件のメッセージを返す
        }

    def update_robot_state(self, client_id: str, state: dict):
        logger.debug(f"Updating state for {client_id}: {state}")
        # 接続状態の更新時にconnected_cabotsに追加されているか確認
        self.connected_cabots[client_id] = {
            "id": client_id,
            "status": state.get("status", "unknown"),
            "last_poll": datetime.now().isoformat(),
            "message": state.get("message", ""),
            "connected": True
        }
        logger.debug(f"Updated connected_cabots: {self.connected_cabots}")

    def get_connected_cabots_list(self) -> list:
        """全てのCaBotのリストを取得（接続状態に関わらず）"""
        current_time = datetime.now()
        cabot_list = []
        
        logger.debug(f"Getting all cabots from: {self.connected_cabots}")
        
        for robot_id, robot_info in self.connected_cabots.items():
            try:
                # 最後のポーリングから経過時間を計算
                last_poll = datetime.fromisoformat(robot_info.get('last_poll', ''))
                time_since_last_poll = (current_time - last_poll).seconds
                is_connected = time_since_last_poll < self.POLLING_TIMEOUT  # タイムアウト時間を使用
                
                cabot_list.append({
                    'id': robot_id,
                    'status': robot_info.get('status', 'unknown'),
                    'last_poll': robot_info.get('last_poll'),
                    'message': robot_info.get('message', ''),
                    'connected': is_connected,
                    'time_since_last_poll': time_since_last_poll,
                    'polling_timeout': self.POLLING_TIMEOUT  # タイムアウト時間も含める
                })
                
                logger.debug(f"Added robot {robot_id} to list. Connected: {is_connected}, "
                           f"Last poll: {time_since_last_poll}s ago (timeout: {self.POLLING_TIMEOUT}s)")
                
            except Exception as e:
                logger.error(f"Error processing robot {robot_id}: {e}")
                # エラーの場合でもリストに追加（切断状態として）
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
        """ロボットにコマンドを送信"""
        if robot_id not in self.connected_cabots:
            raise ValueError(f"Robot {robot_id} not connected")
        
        # コマンド送信後も接続状態を維持
        self.connected_cabots[robot_id].update({
            'last_command': datetime.now().isoformat(),
            'last_command_type': command.get('type')
        })

    def add_message(self, client_id: str, message: str):
        """新しいメッセージを追加"""
        timestamp = datetime.now().isoformat()
        new_message = {
            "timestamp": timestamp,
            "client_id": client_id,
            "message": message
        }
        self.messages.append(new_message)
        
        # 最大数を超えた場合、古いメッセージを削除
        if len(self.messages) > self.MAX_MESSAGES:
            self.messages = self.messages[-self.MAX_MESSAGES:]

    def update_client_status(self, client_id: str, message: str):
        """クライアントのステータスを更新し、メッセージを記録"""
        if client_id in self.connected_cabots:
            self.connected_cabots[client_id].update({
                'message': message,
                'last_poll': datetime.now().isoformat(),
                'status': 'connected'
            })
            # メッセージを履歴に追加
            self.add_message(client_id, message)
            logger.debug(f"Updated status for {client_id}: {message}")
        else:
            logger.warning(f"Attempted to update status for unknown client: {client_id}")
            raise ValueError(f"Client {client_id} not found")

    def get_messages(self, limit: int = 100) -> list:
        """最新のメッセージを取得"""
        return self.messages[-limit:]