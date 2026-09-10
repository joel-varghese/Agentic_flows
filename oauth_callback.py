"""
Handles Google OAuth 2.0 redirect callback.
"""

from google_auth_flow import (
    exchange_code_for_token,
)

from token_store import save_token


def handle_oauth_callback(
    code: str,
    state: str,
) -> dict:

    if not code:

        return {
            "success": False,
            "user_id": "",
            "message": (
                "No authorization code received."
            ),
        }

    if not state:

        return {
            "success": False,
            "user_id": "",
            "message": (
                "No OAuth state received."
            ),
        }

    try:

        result = exchange_code_for_token(
            code=code,
            state=state,
        )

        user_id = result["user_id"]

        token_dict = result["token_dict"]

        save_token(
            user_id=user_id,
            token_dict=token_dict,
        )

        return {
            "success": True,
            "user_id": user_id,
            "thread_id": result.get(
                "thread_id"
            ),
            "message": (
                "Google access granted. "
                "You can continue your request."
            ),
        }

    except Exception as e:

        print(
            f"[OAUTH CALLBACK] "
            f"{repr(e)}"
        )

        return {
            "success": False,
            "user_id": "",
            "message": (
                f"OAuth token exchange failed: "
                f"{str(e)}"
            ),
        }
