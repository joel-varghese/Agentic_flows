"""Handles storing and retrieving Google OAuth tokens from Supabase."""

import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv
 
load_dotenv()
 
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
TABLE = "google_tokens"

def _get_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise EnvironmentError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def get_token(user_email: str) -> dict | None:
    """
    Returns the stored Google OAuth token dict for the user, or None if not found.
    """
    client = _get_client()
    result = (
        client.table(TABLE)
        .select("token_json")
        .eq("user_email", user_email)
        .maybe_single()
        .execute()
    )
    if result is None or not result.data:
        return None
    return json.loads(result.data["token_json"])

def save_token(user_email: str, token_dict: dict) -> None:
    """
    Upserts (insert or update) the Google OAuth token for the user.
    """
    client = _get_client()
    response =client.table(TABLE).upsert(
        {
            "user_email": user_email,
            "token_json": json.dumps(token_dict),
        }
    ).execute()
    print(f">>> Token saved for {user_email}: {response.data}")

def delete_token(user_email: str) -> None:
    """
    Removes the stored token (e.g. on logout or revocation).
    """
    client = _get_client()
    client.table(TABLE).delete().eq("user_email", user_email).execute()