from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form, Cookie, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime
from app.services.auth import AuthService, Token, User
from app.dependencies import get_auth_service
from app.config import settings
from pathlib import Path
from app.utils.logger import logger

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory=Path(__file__).parent.parent.parent / "templates")
auth_service = AuthService()

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

@router.post("/login")
async def login(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    try:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        logger.info(f"Login attempt for user: {username}")
        
        user = auth_service.authenticate_user(username, password)
        if not user:
            logger.warning(f"Authentication failed for user: {username}")
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Invalid username or password"}
            )

        logger.info(f"Creating access token for user: {username}")
        access_token = auth_service.create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
        )
        logger.info(f"Access token created: {access_token[:10]}...")

        # Create response with cookie
        response = RedirectResponse(url="/dashboard", status_code=303)
        
        # Calculate cookie expiration
        max_age = settings.access_token_expire_minutes * 60  # Convert minutes to seconds
        expires = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        
        # Set cookie
        response.set_cookie(
            key="session_token",
            value=access_token,
            max_age=max_age,
            expires=expires,  # Use datetime object for expiration
            domain=None,  # Use the current domain
            httponly=False,  # Allow JavaScript access for WebSocket
            secure=False,  # Development environment uses HTTP
            samesite="lax",
            path="/"
        )
        
        # Log cookie setting
        logger.info(f"Setting cookie session_token for user: {username}")
        logger.info(f"Cookie max age: {max_age} seconds")
        logger.info(f"Cookie expires: {expires}")
        logger.info(f"Cookie path: /")
        logger.info(f"Cookie secure: False")
        logger.info(f"Cookie httponly: False")
        logger.info(f"Cookie samesite: lax")
        
        return response
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "An error occurred during login"}
        )

@router.post("/logout")
async def logout(response: Response):
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="session_token")
    return response

@router.get("/", response_class=HTMLResponse)
async def root(
    request: Request,
    session_token: str = Cookie(None),
    auth_service: AuthService = Depends(get_auth_service)
):
    try:
        if session_token and await auth_service.validate_token(session_token):
            return RedirectResponse(url="/dashboard")
    except ValueError:
        pass

    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": None
    })

@router.post("/oauth/token", response_model=Token)
async def client_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service)
):
    authenticated = await auth_service.authenticate_client(
        form_data.client_id,
        form_data.client_secret
    )
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await auth_service.create_client_token(form_data.client_id)