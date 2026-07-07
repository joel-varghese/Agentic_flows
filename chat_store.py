import os
from supabase import create_client

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"]
)

def save_message(user_id: str, role: str, content: str):
    supabase.table("chat_messages").insert({
        "user_id": user_id,
        "role": role,
        "content": content
    }).execute()

def load_history(user_id: str):
    result = (
        supabase.table("chat_messages")
        .select("role, content")
        .eq("user_id", user_id)
        .order("created_at")
        .execute()
    )

    return result.data