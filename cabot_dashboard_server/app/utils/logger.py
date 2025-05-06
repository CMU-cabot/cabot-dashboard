import logging
import os

def setup_logger():
    # 現在の実効レベルを確認
    logger = logging.getLogger("app.utils.logger")
    
    # 環境変数からログレベルを取得
    log_level_str = os.getenv("CABOT_DASHBOARD_LOG_LEVEL", "INFO")
    
    # ログレベルを設定
    log_level = getattr(logging, log_level_str.upper())
    
    # ルートロガーのレベルも設定
    logging.getLogger().setLevel(log_level)
    logger.setLevel(log_level)
    
    # ハンドラーの設定
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message).200s ...') # 200文字まで表示
    handler.setFormatter(formatter)
    handler.setLevel(log_level)  # ハンドラーにもログレベルを設定
    logger.addHandler(handler)
    
    # 設定確認用のデバッグ出力
    print(f"Log level set to: {log_level_str}")
    print(f"Logger effective level: {logger.getEffectiveLevel()}")
    print(f"Root logger level: {logging.getLogger().getEffectiveLevel()}")
    
    return logger

# グローバルロガーのインスタンス
logger = setup_logger()

def get_logger(name: str = None) -> logging.Logger:
    """
    指定された名前のロガーを取得する
    Args:
        name: ロガー名（デフォルトはNone）
    Returns:
        logging.Logger: 設定済みのロガーインスタンス
    """
    if name:
        return logging.getLogger(name)
    return logger