import io
import os
import json
from langchain_core.tools import tool
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
 
from supabase_auth import get_token, save_token
from google_auth_flow import credentials_from_token_dict, get_auth_url

AUTH_REQUIRED_PREFIX = "AUTH_REQUIRED::"
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/tmp/drive_downloads")

def _drive_service(user_email: str):
    """Returns an auth Drive service"""
    token_dict = get_token(user_email)
    if not token_dict:
        return None
    creds = credentials_from_token_dict(token_dict)
    # Persist refreshed token back to Supabase
    save_token(user_email, {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or []),
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    })
    return build("drive", "v3", credentials=creds)

def _search_files(service, query: str, max_results: int = 5) -> list[dict]:
    """Full-text search across Drive files."""
    results = service.files().list(
        q=f"fullText contains '{query}' and trashed=false",
        pageSize=max_results,
        fields="files(id, name, mimeType, webViewLink, size)",
    ).execute()
    return results.get("files", [])

def _download_file(service, file_id: str, file_name: str, mime_type: str) -> str:
    """Downloads a file and returns local path."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    local_path = os.path.join(DOWNLOAD_DIR, file_name)
    
    # Google Workspace docs must be exported; regular files use get_media
    export_map = {
        "application/vnd.google-apps.document":
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.google-apps.spreadsheet":
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.google-apps.presentation":
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }

    fh = io.BytesIO()
    if mime_type in export_map:
        export_mime = export_map[mime_type]
        request = service.files().export_media(fileId=file_id, mimeType=export_mime)
        ext_map = {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
        }
        local_path += ext_map.get(export_mime, "")
    else:
        request = service.files().get_media(fileId=file_id)
 
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
 
    with open(local_path, "wb") as f:
        f.write(fh.getvalue())
 
    return local_path



@tool
def search_and_download_doc_tool(user_email: str, query: str) -> str:
    """
    Searches Google Drive and downloads a document by name.
    """

    service = _drive_service(user_email)
    if service is None:
        auth_url = get_auth_url(state=user_email)          # state carries email through OAuth
        return (
            f"{AUTH_REQUIRED_PREFIX}{auth_url}\n"
            f"User {user_email} is not authenticated with Google Drive. "
            f"They must visit the URL above to grant access."
        )
    try:
        files = _search_files(service, query)
    except HttpError as e:
        return f"Drive search failed: {e}"
 
    if not files:
        return f"No files found on Google Drive matching '{query}'."
 
    # Pick the first (most relevant) result
    best = files[0]
    file_id   = best["id"]
    file_name = best["name"]
    mime_type = best["mimeType"]
    view_link = best.get("webViewLink", "N/A")
 
    other_matches = [f["name"] for f in files[1:]]
    other_str = (
        f"\n\nOther matches: {', '.join(other_matches)}" if other_matches else ""
    )
 
    # ── 3. Download ────────────────────────────────────────────────────────────
    try:
        local_path = _download_file(service, file_id, file_name, mime_type)
        return (
            f"✅ Found and downloaded '{file_name}'.\n"
            f"Saved to: {local_path}\n"
            f"View online: {view_link}"
            f"{other_str}"
        )
    except HttpError as e:
        return (
            f"Found '{file_name}' on Drive but download failed: {e}\n"
            f"View online: {view_link}"
        )
