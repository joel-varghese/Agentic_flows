import io
import os
from langchain_core.tools import tool
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from google_auth_helpers import (
    AUTH_REQUIRED_PREFIX,
    auth_required_message,
    get_google_credentials,
    is_auth_failure,
)

DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/tmp/drive_downloads")


def _drive_service(user_email: str):
    """
    Returns (Drive service, auth_message).
    auth_message is set when the user must re-authenticate.
    """
    try:
        creds, auth_msg = get_google_credentials(user_email)

    except RefreshError as e:
        print(
            f"Unexpected Google refresh failure for {user_email}: "
            f"{repr(e)}"
        )

        return None, auth_required_message(
            user_email,
            "Google Drive",
            revoke=True
        )
    
    if auth_msg:
        return None, auth_msg
    if creds is None:
        return None, auth_required_message(user_email, "Google Drive")

    return build("drive", "v3", credentials=creds), None


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

    service, auth_msg = _drive_service(user_email)
    if auth_msg:
        return auth_msg

    try:
        files = _search_files(service, query)

    except RefreshError as e:
        print(
            f"[DRIVE AUTH] RefreshError while searching Drive "
            f"for {user_email}: {repr(e)}"
        )

        return auth_required_message(
            user_email,
            "Google Drive",
            revoke=True,
        )

    
    except HttpError as e:

        print(
            f"[DRIVE] HttpError while searching Drive "
            f"for {user_email}: {repr(e)}"
        )
        if is_auth_failure(e):
            return auth_required_message(user_email, "Google Drive", revoke=True)
        return f"Drive search failed: {e}"

    if not files:
        return f"No files found on Google Drive matching '{query}'."

    best = files[0]
    file_id = best["id"]
    file_name = best["name"]
    mime_type = best["mimeType"]
    view_link = best.get("webViewLink", "N/A")

    other_matches = [f["name"] for f in files[1:]]
    other_str = (
        f"\n\nOther matches: {', '.join(other_matches)}" if other_matches else ""
    )

    try:
        local_path = _download_file(service, file_id, file_name, mime_type)
        return (
            f"✅ Found and downloaded '{file_name}'.\n"
            f"Saved to: {local_path}\n"
            f"View online: {view_link}"
            f"{other_str}"
        )

    except RefreshError as e:
        print(
            f"[DRIVE AUTH] RefreshError while downloading "
            f"{file_name} for {user_email}: {repr(e)}"
        )

        return auth_required_message(
            user_email,
            "Google Drive",
            revoke=True,
        )
    except HttpError as e:
        print(
            f"[DRIVE] HttpError while downloading "
            f"{file_name} for {user_email}: {repr(e)}"
        )

        if is_auth_failure(e):
            return auth_required_message(
                user_email,
                "Google Drive",
                revoke=True,
            )

        return (
            f"Found '{file_name}' on Drive but download failed: {e}\n"
            f"View online: {view_link}"
        )
