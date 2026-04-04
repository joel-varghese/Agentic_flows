"""Handles the google OAuth 2.0 redirect callback"""

from google_auth_flow import exchange_code_for_token
from token_store import save_token

def handle_oauth_callback(code: str, state: str) -> dict:
    """
    Exchanges the OAuth authorization code for tokens and persists them.
 
    Args:
        code:  The `code` query parameter from the callback URL.
        state: The `state` parameter — we use it to carry the user's email.
 
    Returns:
        A dict with keys:
          - success (bool)
          - user_email (str)
          - message (str)
    """
    user_email = state  # we set state=user_email when building the auth URL
 
    if not code:
        return {"success": False, "user_email": user_email, "message": "No authorization code received."}
    if not user_email:
        return {"success": False, "user_email": "", "message": "No user email in OAuth state parameter."}
 
    # The instance where this would fail is when a user has mutiple auth flows created or
    # if there are multiple workers involved
    try:
        token_dict = exchange_code_for_token(code, state)
        save_token(user_email, token_dict)
        return {
            "success": True,
            "user_email": user_email,
            "message": f"✅ Google Drive access granted and token saved for {user_email}. You can now search your Drive.",
        }
    except Exception as e:
        return {
            "success": False,
            "user_email": user_email,
            "message": f"OAuth token exchange failed: {str(e)}",
        }
 