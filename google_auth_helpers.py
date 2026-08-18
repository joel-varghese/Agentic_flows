"""Shared Google OAuth auth-gate helpers for Drive and Calendar tools."""

from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from google_auth_flow import credentials_from_token_dict, get_auth_url
from token_store import delete_token, get_token, save_token



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


def build_auth_required(
    user_email: str,
    service: str = "Google Drive",
    *,
    revoke: bool = False,
) -> dict:
    if revoke:
        try:
            delete_token(user_email)
        except Exception:
            pass
    auth_url = get_auth_url(user_email)

    return {
        "type": "auth_required",
        "provider": "google",
        "service": service,
        "user_email": user_email,
        "auth_url": auth_url,
        "message": (
            f"{service} authentication is required. "
            "Please connect your Google account, then retry your request."
        ),
    }


def get_google_credentials(user_email: str):
    """
    Returns:

        (credentials, None)
            when credentials are valid

        (None, None)
            when no token exists

        (None, auth_payload)
            when the user needs OAuth
    """
    token_dict = get_token(user_email)
    if not token_dict:
        return None, build_auth_required(
            user_email,
            "Google Drive",
        )

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
                "expiry": (
                    creds.expiry.isoformat() 
                    if creds.expiry 
                    else None,
                ),
            },
        )
        return creds, None
    except Exception as e:

        if is_auth_failure(e):
            print(
                f"[AUTH] Google authentication failed for "
                f"{user_email}: {repr(e)}"
            )
            return None, build_auth_required(
                user_email, 
                "Google Drive",
                revoke=True
            )
        raise
