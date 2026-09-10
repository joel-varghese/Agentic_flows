import os
import secrets
import time
from urllib.parse import unquote

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from dotenv import load_dotenv

from token_store import save_oauth_state, get_oauth_state, delete_oauth_state


os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

load_dotenv()

SESSION_TTL_SECONDS = 600

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.send",

    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid",
]

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")


def _normalize_state(state: str) -> str:
    return unquote(state or "").strip()


def _client_config() -> dict:
    return {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uris": [REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def get_auth_url(
    user_id: str,
    service: str = "Google",
    thread_id: str | None = None,
) -> str:

    flow = Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
    )

    flow.redirect_uri = REDIRECT_URI

    state = secrets.token_urlsafe(32)

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )

    save_oauth_state(
        state=state,
        user_id=user_id,
        service=service,
        thread_id=thread_id,
        code_verifier=flow.code_verifier,
        created_at=time.time(),
    )

    return auth_url


def exchange_code_for_token(
    code: str,
    state: str,
) -> dict:

    state = _normalize_state(state)

    session = get_oauth_state(state)

    if not session:
        raise Exception(
            "OAuth session expired or invalid state."
        )

    flow = Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
    )

    flow.redirect_uri = REDIRECT_URI
    flow.code_verifier = session["code_verifier"]

    flow.fetch_token(code=code)

    creds = flow.credentials

    user_id = session["user_id"]
    thread_id = session.get("thread_id")

    delete_oauth_state(state)

    return {
        "user_id": user_id,
        "thread_id": thread_id,
        "token_dict": _creds_to_dict(creds),
    }


def credentials_from_token_dict(
    token_dict: dict,
) -> Credentials:

    creds = Credentials(
        token=token_dict.get("token"),
        refresh_token=token_dict.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=token_dict.get("scopes", SCOPES),
    )

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            print(
                "Google refresh token is invalid or revoked."
            )
            raise

    return creds


def _creds_to_dict(creds: Credentials) -> dict:
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or SCOPES),
        "expiry": (
            creds.expiry.isoformat()
            if creds.expiry
            else None
        ),
    }
