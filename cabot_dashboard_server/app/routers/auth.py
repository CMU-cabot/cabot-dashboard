from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.services.auth import AuthService
from app.dependencies import get_auth_service

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="templates")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Display login page"""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": None
    })

@router.post("/login")
async def login(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    # Add debug log
    print(f"Login attempt for user: {username}")  # For development only
    if auth_service.validate_user(username, password):
        session_token = auth_service.create_session(username)
        response = RedirectResponse(url="/dashboard", status_code=303)  # Override response object
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="strict"
        )
        return response  # Return modified response
        # return RedirectResponse(url="/dashboard", status_code=303)
    
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
    """Logout process"""
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
    """Root page"""
    try:
        if session_token and auth_service.validate_session(session_token, timeout=3600):
            return RedirectResponse(url="/dashboard")
    except ValueError:
        # Show login page on authentication error
        pass

    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": None
    })