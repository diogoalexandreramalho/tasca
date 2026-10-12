from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from core.config import get_settings
from schemas.auth import Token
from services import auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=Token)
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    """OAuth2 password flow: form fields `username` and `password`."""
    token = auth.login(username=form.username, password=form.password)
    return Token(access_token=token, expires_in=get_settings().jwt_access_token_expire_minutes * 60)
