# コマンド仕様

## ロボット操作コマンド

ロボットに対して実行可能な操作コマンドは以下の通りです：

| 項番 | 操作 | Command | CommandOption |
|------|------|---------|-----------|
| 1 | ROS起動 | ros-start |  |
| 2 | ROS停止 | ros-stop |  |
| 3 | システム再起動 | system-reboot |  |
| 4 | システム電源OFF | system-poweroff |  |
| 5 | Debug1 | debug1 |  |
| 6 | Debug2 | debug2 |  |

## メッセージフォーマット

コマンドは以下のJSON形式で送信されます：

```json
{
  "target": ["cabot1", "cabot2"],
  "command": "restart",
  "commandOption": {"ProcessName": "ROS"},
  "timestamp": "2024-06-27T12:34:56Z"
}
```

### フィールド説明

- `target`: コマンドの対象となるロボットのID（配列）
- `command`: 実行するコマンド
- `commandOption`: コマンドのオプション（必要な場合のみ）
- `timestamp`: コマンド発行時のタイムスタンプ（ISO 8601形式） 