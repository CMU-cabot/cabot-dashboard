import logging
from urllib.parse import urljoin, quote
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from msal import ConfidentialClientApplication
from app.config import settings
from app.services.auth import AuthService
import httpx

router = APIRouter(prefix="/auth/microsoft", tags=["auth"])

def get_auth_service():
    return AuthService()

def get_msal_app():
    authority = f"https://login.microsoftonline.com/{settings.microsoft_tenant_id}"
    return ConfidentialClientApplication(
        client_id=settings.microsoft_client_id,
        client_credential=settings.microsoft_client_secret,
        authority=authority
    )

@router.get("/signin")
async def microsoft_signin(request: Request):
    try:
        redirect_uri = str(request.base_url) + "auth/microsoft/callback"
        logging.info(f"Starting signin process with redirect_uri: {redirect_uri}")
        auth_url = (
            f"https://login.microsoftonline.com/{settings.microsoft_tenant_id}/oauth2/v2.0/authorize?"
            f"client_id={settings.microsoft_client_id}&"
            "response_type=code&"
            f"redirect_uri={quote(redirect_uri)}&"
            "scope=User.Read offline_access openid profile&"
            f"state={quote(str(request.base_url))}&"
            "prompt=select_account"
        )
        logging.info(f"Generated auth_url: {auth_url}")
        return RedirectResponse(auth_url)
    except Exception as e:
        logging.error(f"Error in signin: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/callback")
async def microsoft_callback(
    request: Request,
    code: str = None,
    error: str = None,
    state: str = None,
    auth_service: AuthService = Depends(get_auth_service)
):
    try:
        logging.info(f"Received callback with state: {state}")
        if error:
            logging.error(f"Error in callback: {error}")
            return RedirectResponse(url="/login?error=" + error)
        if not code:
            logging.error("No code received in callback")
            return RedirectResponse(url="/login?error=no_code")
        msal_app = get_msal_app()
        redirect_uri = urljoin(str(request.base_url), settings.microsoft_redirect_path)
        result = await _acquire_token(msal_app, code, redirect_uri)
        user_info = await _get_user_info(result['access_token'])
        email = user_info.get("userPrincipalName")
        if not email:
            logging.error("Email not found in user info")
            return RedirectResponse(url="/login?error=no_email")
        logging.info(f"Creating session for user: {email}")
        auth_service.register_microsoft_user(email)
        session_token = auth_service.create_session(email)
        response = RedirectResponse(url="/dashboard")
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=settings.use_secure_cookies, 
            samesite="lax"
        )
        return response
    except Exception as e:
        error_msg = f"Callback processing error: {str(e)}"
        logging.error(error_msg, exc_info=True)
        return RedirectResponse(url=f"/login?error={error_msg}")

async def _acquire_token(msal_app, code: str, redirect_uri: str):
    result = msal_app.acquire_token_by_authorization_code(
        code,
        scopes=["User.Read"],
        redirect_uri=redirect_uri
    )
    if "error" in result:
        error_msg = f"Token acquisition failed: {result.get('error_description', 'Unknown error')}"
        logging.error(error_msg)
        raise HTTPException(status_code=401, detail=error_msg)
    if "access_token" not in result:
        logging.error("No access token in result")
        raise HTTPException(status_code=401, detail="No access token received")
    return result

async def _get_user_info(access_token: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                'https://graph.microsoft.com/v1.0/me',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10.0
            )
            if response.status_code != 200:
                logging.error(f"Graph API error: Status {response.status_code}, Response: {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Failed to get user info")
            return response.json()
    except httpx.TimeoutException:
        logging.error("Timeout while fetching user info")
        raise HTTPException(status_code=504, detail="Request timeout")