from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form, Cookie, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from app.services.auth import AuthService, Token, User
from app.dependencies import get_auth_service
from app.config import settings

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="templates")
auth_service = AuthService()

class ClientCredentialsRequestForm:
    def __init__(
        self,
        grant_type: str = Form(None),
        client_id: str = Form(...),
        client_secret: str = Form(...),
    ):
        self.grant_type = grant_type
        self.client_id = client_id
        self.client_secret = client_secret

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
    
    user = auth_service.authenticate_user(username, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password"}
        )

    access_token = auth_service.create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key="session_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="strict"
    )
    return response

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
    """Root page"""
    try:
        if session_token and await auth_service.validate_token(session_token):
            return RedirectResponse(url="/dashboard")
    except ValueError:
        # Show login page on authentication error
        pass

    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": None
    })

@router.post("/oauth/token", response_model=Token)
async def client_token(
    form_data: ClientCredentialsRequestForm = Depends(),
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