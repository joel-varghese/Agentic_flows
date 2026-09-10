"""
Stores Google OAuth connections and OAuth state in Supabase.
"""

import os
import json

from supabase import create_client, Client
from dotenv import load_dotenv


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

GOOGLE_CONNECTIONS_TABLE = "google_connections"
OAUTH_STATES_TABLE = "oauth_states"


def _get_client() -> Client:

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise EnvironmentError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY "
            "must be set."
        )

    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
    )


# ============================================================
# GOOGLE CONNECTIONS
# ============================================================

def get_token(user_id: str) -> dict | None:
    """
    Returns the user's Google OAuth token.
    """

    client = _get_client()

    result = (
        client
        .table(GOOGLE_CONNECTIONS_TABLE)
        .select("token_json")
        .eq("user_id", user_id)
        .eq("provider", "google")
        .maybe_single()
        .execute()
    )

    if not result or not result.data:
        return None

    return json.loads(
        result.data["token_json"]
    )


def save_token(
    user_id: str,
    token_dict: dict,
    google_email: str | None = None,
) -> None:
    """
    Saves or updates the user's Google OAuth connection.
    """

    client = _get_client()

    data = {
        "user_id": user_id,
        "provider": "google",
        "token_json": json.dumps(token_dict),
    }

    if google_email:
        data["google_email"] = google_email

    response = (
        client
        .table(GOOGLE_CONNECTIONS_TABLE)
        .upsert(
            data,
            on_conflict="user_id,provider",
        )
        .execute()
    )

    print(
        ">>> Google token saved:",
        response.data,
    )


def delete_token(user_id: str) -> None:
    """
    Removes the user's Google connection.
    """

    client = _get_client()

    (
        client
        .table(GOOGLE_CONNECTIONS_TABLE)
        .delete()
        .eq("user_id", user_id)
        .eq("provider", "google")
        .execute()
    )


# ============================================================
# OAUTH STATE
# ============================================================

def save_oauth_state(
    state: str,
    user_id: str,
    service: str,
    thread_id: str | None,
    code_verifier: str,
    created_at: float,
) -> None:

    client = _get_client()

    client.table(OAUTH_STATES_TABLE).insert({
        "state": state,
        "user_id": user_id,
        "service": service,
        "thread_id": thread_id,
        "code_verifier": code_verifier,
        "created_at": created_at,
    }).execute()


def get_oauth_state(
    state: str,
) -> dict | None:

    client = _get_client()

    result = (
        client
        .table(OAUTH_STATES_TABLE)
        .select("*")
        .eq("state", state)
        .maybe_single()
        .execute()
    )

    if not result or not result.data:
        return None

    return result.data


def delete_oauth_state(
    state: str,
) -> None:

    client = _get_client()

    (
        client
        .table(OAUTH_STATES_TABLE)
        .delete()
        .eq("state", state)
        .execute()
    )
