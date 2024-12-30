from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from app.middleware.error_logging import ErrorLoggingMiddleware
from app.routers import client, dashboard, auth
from app.config import settings
from app.utils.logger import logger
from app.services.robot_state import RobotStateManager
from fastapi.middleware.cors import CORSMiddleware

# Create FastAPI application
app = FastAPI(
    title="CaBot Dashboard",
    description="Dashboard for monitoring and controlling CaBots",
    version="1.0.0"
)

root_dir = Path(__file__).parent.parent
app.mount("/static", StaticFiles(directory=root_dir / "static", html=True), name="static")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "upgrade-insecure-requests"
    return response

templates = Jinja2Templates(directory=root_dir / "templates")

app.add_middleware(ErrorLoggingMiddleware)

robot_state_manager = RobotStateManager()

def get_robot_state_manager():
    return robot_state_manager

app.include_router(auth.router)
app.include_router(
    client.router,
    prefix="/api/client",
    dependencies=[Depends(get_robot_state_manager)]
)
app.include_router(dashboard.router)

@app.get("/health")
async def health_check():
    return {"status": "OK"}

@app.on_event("startup")
async def startup_event():
    logger.info("Starting CaBot Dashboard server")
    logger.info(f"Environment: API_KEY={'*' * len(settings.api_key)}")
    logger.info(f"Max robots: {settings.max_robots}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down CaBot Dashboard server")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)