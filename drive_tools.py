from langchain_core.tools import tool
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth import dict_to_creds
import io
import os
import json

TOKEN_STORE = "user_token.json"

@tool
def search_and_download_doc_tool(file_name: str) -> str:
    """
    Searches Google Drive and downloads a document by name.
    """

    if not os.path.exists(TOKEN_STORE):
        return "User not authenticated. Please login first."

    with open(TOKEN_STORE, "r") as f:
        token_data = json.load(f)

    creds = dict_to_creds(token_data)
    service = build("drive", "v3", credentials=creds)

    results = service.files().list(
        q=f"name contains '{file_name}'",
        fields="files(id, name)"
    ).execute()

    items = results.get("files", [])

    if not items:
        return "No document found."

    file_id = items[0]["id"]
    request = service.files().get_media(fileId=file_id)

    file_path = f"./downloads/{items[0]['name']}"
    os.makedirs("downloads", exist_ok=True)

    fh = io.FileIO(file_path, "wb")
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()

    return f"Downloaded to {file_path}"
