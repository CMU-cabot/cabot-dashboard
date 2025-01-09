from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.services.auth import AuthService
from app.dependencies import get_auth_service
from pathlib import Path
from app.utils.logger import logger


router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory=Path(__file__).parent.parent.parent / "templates")

@router.get("/login")
async def login_page(request: Request):
    error = request.query_params.get('error')
    error_message = None
    
    if error == 'unauthorized_account':
        error_message = 'unauthorized_account'
    elif error:
        error_message = error

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error_message": error_message}
    )

@router.get("/auth/callback")
async def auth_callback(request: Request):
    try:
        request.session["authenticated"] = True
        return RedirectResponse(url="/dashboard")
    except Exception as e:
        request.session["error_message"] = "Login failed. Please try again."
    return RedirectResponse(url="/login")

@router.post("/login")
async def login(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    logger.info(f"Login attempt for user: {username}")
    if auth_service.validate_user(username, password):
        session_token = auth_service.create_session(username)
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="strict"
        )
        return response
    
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Invalid username or password"}
    )

@router.post("/logout")
async def logout(
    response: Response,
    session_token: str = Cookie(None),
    auth_service: AuthService = Depends(get_auth_service)
):
    if session_token:
        auth_service.remove_session(session_token)
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="session_token")
    return response

@router.get("/", response_class=HTMLResponse)
async def root(
    request: Request,
    session_token: str = Cookie(None),
    auth_service: AuthService = Depends(get_auth_service)
):
    try:
        if session_token and auth_service.validate_session(session_token, timeout=3600):
            return RedirectResponse(url="/dashboard")
    except ValueError:
        pass

    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": None
    })