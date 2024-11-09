from fastapi import FastAPI, Depends
from fastapi.templating import Jinja2Templates
from app.middleware.error_logging import ErrorLoggingMiddleware
from app.routers import client, dashboard, auth
from app.config import settings
from app.utils.logger import logger
from app.services.robot_state import RobotStateManager

# FastAPIアプリケーションの作成
app = FastAPI(
    title="CaBot Dashboard",
    description="Dashboard for monitoring and controlling CaBots",
    version="1.0.0"
)

# テンプレートの設定
templates = Jinja2Templates(directory="templates")

# ミドルウェアの追加
app.add_middleware(ErrorLoggingMiddleware)

# グローバルなインスタンスを作成
robot_state_manager = RobotStateManager()

# 依存性注入用の関数
def get_robot_state_manager():
    return robot_state_manager

# ルーターの登録
app.include_router(auth.router)
app.include_router(
    client.router,
    prefix="/api/client",
    dependencies=[Depends(get_robot_state_manager)]
)
app.include_router(dashboard.router)

# ヘルスチェックエンドポイント
@app.get("/health")
async def health_check():
    return {"status": "OK"}

# アプリケーション起動時の処理
@app.on_event("startup")
async def startup_event():
    logger.info("Starting CaBot Dashboard server")
    logger.info(f"Environment: API_KEY={'*' * len(settings.api_key)}")
    logger.info(f"Max robots: {settings.max_robots}")

# アプリケーション終了時の処理
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down CaBot Dashboard server")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)