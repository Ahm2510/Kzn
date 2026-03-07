# utils/security.py

from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import settings

_security_scheme = HTTPBearer(auto_error=False)

if settings.ENVIRONMENT == "production" and settings.ALLOW_INTERNAL_PUBLIC:
    raise RuntimeError(
        "Misconfiguration: ALLOW_INTERNAL_PUBLIC must never be enabled in production."
    )


async def require_internal_auth(
    x_internal_secret: Optional[str] = Header(None, alias="X-Internal-Secret"),
) -> bool:
    """
    Dependency to require internal endpoint authentication.

    Checks for X-Internal-Secret header matching INTERNAL_SECRET env var.
    Can be bypassed in dev by setting ALLOW_INTERNAL_PUBLIC=true.

    Trust boundary:
        Service B is an internal service and is not user-facing.
        Authentication for internal endpoints is enforced via X-Internal-Secret.
        User authentication and authorization are handled by Service A.

    Usage:
        @router.get("/internal/endpoint")
        async def internal_endpoint(auth: bool = Depends(require_internal_auth)):
            ...
    """
    # Allow public access in dev if explicitly enabled
    if settings.ALLOW_INTERNAL_PUBLIC and settings.ENVIRONMENT == "development":
        return True

    # Require INTERNAL_SECRET to be configured
    if not settings.INTERNAL_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal authentication not configured. Set INTERNAL_SECRET env var.",
        )

    # Validate secret
    if not x_internal_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing internal secret",
        )

    if str(x_internal_secret).strip() != str(settings.INTERNAL_SECRET).strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal secret",
        )

    return True


def verify_token(token: Optional[str]) -> Dict[str, Any]:
    """
    Very basic token verification placeholder.

    In dev: allows missing token if API_KEY_REQUIRED=False.
    In prod: token MUST be present.

    Design note:
        Service B is not a user-facing service. It is intended to be called by
        Service A via internal network boundaries and X-Internal-Secret.
        JWT/OAuth2 user auth is intentionally not used in Service B.
    """
    if not token:
        if settings.API_KEY_REQUIRED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials were not provided.",
            )
        # Dev / non-strict mode - return a default user with test workspace
        return {
            "user_id": "test-user",
            "workspace_id": "test-workspace",
            "is_authenticated": False,
        }

    # Token parsing is intentionally minimal; Service B is not user-facing.
    # For now, parse the token as user_id:workspace_id if it contains a colon.
    if ":" in token:
        user_id, workspace_id = token.split(":", 1)
        return {
            "user_id": user_id,
            "workspace_id": workspace_id,
            "is_authenticated": True,
        }

    # Fallback to using the token as user_id
    return {
        "user_id": token,
        "workspace_id": f"workspace-{token}",
        "is_authenticated": True,
    }


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security_scheme),
) -> Dict[str, Any]:
    """
    FastAPI dependency to get current user from Authorization: Bearer <token>.
    """
    token = credentials.credentials if credentials else None
    return verify_token(token)
