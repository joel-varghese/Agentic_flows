import os
from urllib.parse import unquote
import secrets
import time
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from dotenv import load_dotenv

# Google may grant extra scopes (e.g. userinfo.profile with openid); relax strict checks.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")
oauth_session_store = {}

SESSION_TTL_SECONDS = 600

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid",
]


load_dotenv()

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")


def _normalize_state(state: str) -> str:
    return unquote(state or "").strip()


def _client_config() -> dict:
    """Builds the client config dict that google_auth_oauthlib expects."""
    return {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uris": [REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def get_auth_url(user_email: str) -> str:
    """
    Returns the Google OAuth consent-screen URL to redirect the user to.
    `state` can carry any context you want back in the callback (e.g. user_email).
    """

    flow = Flow.from_client_config(_client_config(), scopes=SCOPES)
    flow.redirect_uri = REDIRECT_URI

    state = secrets.token_urlsafe(32)
    
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )

    oauth_session_store[state] = {
        "user_email": user_email,
        "code_verifier": flow.code_verifier,
        "created_at": time.time()
    }

    return auth_url


def exchange_code_for_token(code: str, state: str) -> dict:
    """
    Exchanges an authorization code (from the OAuth callback) for credentials.
    Returns a JSON-serialisable token dict.
    """

    session = oauth_session_store.get(state)

    if not session:
        raise Exception("OAuth session expired or invalid state.")

    
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES)
    flow.redirect_uri = REDIRECT_URI
    flow.code_verifier = session["code_verifier"]
    flow.fetch_token(code=code)
    creds = flow.credentials

    user_email = session["user_email"]
    del oauth_session_store[state]

    return {
        "user_email": user_email,
        "token_dict": _creds_to_dict(creds)
    }


def credentials_from_token_dict(token_dict: dict) -> Credentials:
    """
    Re-hydrates a Credentials object from a stored token dict,
    refreshing automatically if the access token is expired.
    """
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
            print("Google refresh token is invalid or revoked.")
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
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }
