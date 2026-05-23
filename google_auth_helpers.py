"""Shared Google OAuth auth-gate helpers for Drive and Calendar tools."""

from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from google_auth_flow import credentials_from_token_dict, get_auth_url
from token_store import delete_token, get_token, save_token

AUTH_REQUIRED_PREFIX = "AUTH_REQUIRED::"


def is_auth_failure(exc: BaseException) -> bool:
    if isinstance(exc, RefreshError):
        return True
    if "invalid_grant" in str(exc).lower():
        return True
    if isinstance(exc, HttpError):
        status = exc.resp.status if exc.resp else None
        if status in (401, 403):
            return True
        if "invalid_grant" in str(exc).lower():
            return True
    return False


def auth_required_message(
    user_email: str,
    product: str = "Google",
    *,
    revoke: bool = False,
) -> str:
    if revoke:
        try:
            delete_token(user_email)
        except Exception:
            pass
    auth_url = get_auth_url(state=user_email)
    return (
        f"{AUTH_REQUIRED_PREFIX}{auth_url}\n"
        f"User {user_email} must sign in to grant {product} access. "
        f"Visit the URL above, then retry the request."
    )


def get_google_credentials(user_email: str):
    """
    Load and refresh stored credentials.
    Returns (credentials, None) on success, (None, None) if no token,
    or (None, auth_required_message) when re-authentication is needed.
    """
    token_dict = get_token(user_email)
    if not token_dict:
        return None, None

    try:
        creds = credentials_from_token_dict(token_dict)
        save_token(
            user_email,
            {
                "token": creds.token,
                "refresh_token": (
                    creds.refresh_token
                    or token_dict.get("refresh_token")
                ),
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": list(creds.scopes or []),
                "expiry": creds.expiry.isoformat() if creds.expiry else None,
            },
        )
        return creds, None
    except Exception as e:
        if is_auth_failure(e):
            return None, auth_required_message(user_email, "Google", revoke=True)
        raise
