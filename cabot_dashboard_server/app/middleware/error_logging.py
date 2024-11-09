from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import RedirectResponse
from app.utils.logger import logger

class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except ValueError as e:
            if str(e) == "Authentication required":
                return RedirectResponse(url="/login")
            raise
        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            raise