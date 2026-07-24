"""Session refresh routes (issue #527)."""

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from codex.api.auth import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS, rotate_refresh_token
from codex.api.schemas import RefreshTokenRequest, TokenResponse
from codex.db.database import get_system_session

router = APIRouter()


@router.post("/refresh", response_model=TokenResponse)
async def refresh_session(
    response: Response,
    body: RefreshTokenRequest | None = None,
    refresh_token_cookie: str | None = Cookie(default=None, alias="refresh_token"),
    session: AsyncSession = Depends(get_system_session),
) -> TokenResponse:
    """Exchange a refresh token for a new access + refresh token pair.

    Accepts the refresh token either in the JSON body or the httponly
    `refresh_token` cookie set at login. The presented token is revoked
    (rotated) so it cannot be replayed.
    """
    plain_token = (body.refresh_token if body else None) or refresh_token_cookie
    if not plain_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    access_token, new_refresh_token = await rotate_refresh_token(plain_token, session)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
        path="/api/v1/auth/refresh",
    )

    return TokenResponse(access_token=access_token, token_type="bearer", refresh_token=new_refresh_token)
