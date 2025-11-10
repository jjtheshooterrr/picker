# download_shared_folder.py
import os
import io
import sys
import time
import pathlib
from typing import Dict, Tuple
from tqdm import tqdm

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# -------- CONFIG --------
DEFAULT_FOLDER_ID = "1eYkGatkta7R7nuJDEGOwU9qStPLvkxnc"  # can override via CLI arg
OUTPUT_DIR = "SharedBackup"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Export mapping for Google-native files
EXPORT_MAP: Dict[str, Tuple[str, str]] = {
    "application/vnd.google-apps.document": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".docx",
    ),
    "application/vnd.google-apps.spreadsheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xlsx",
    ),
    "application/vnd.google-apps.presentation": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".pptx",
    ),
    "application/vnd.google-apps.drawing": ("image/png", ".png"),
}
FALLBACK_EXPORT = ("application/pdf", ".pdf")
CHUNK_SIZE = 1024 * 1024  # 1 MiB
MAX_RETRIES = 8
BASE_BACKOFF = 0.8  # seconds

# -------- AUTH --------
def get_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())
    return build("drive", "v3", credentials=creds, cache_discovery=False)

# -------- DRIVE HELPERS --------
def get_item(svc, file_id):
    return svc.files().get(
        fileId=file_id,
        fields="id,name,mimeType,parents",
        supportsAllDrives=True
    ).execute()

def list_children(svc, folder_id):
    q = f"'{folder_id}' in parents and trashed=false"
    fields = "nextPageToken, files(id,name,mimeType,shortcutDetails)"
    page_token = None
    while True:
        resp = svc.files().list(
            q=q,
            fields=fields,
            pageSize=1000,
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        for f in resp.get("files", []):
            yield f
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

def _retry_sleep(attempt: int):
    time.sleep(BASE_BACKOFF * (2 ** attempt))

def download_binary_with_retries(svc, file_id, dest_path: pathlib.Path):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(MAX_RETRIES):
        try:
            req = svc.files().get_media(fileId=file_id)
            with io.FileIO(dest_path, "wb") as fh:
                downloader = MediaIoBaseDownload(fh, req, chunksize=CHUNK_SIZE)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
            return
        except HttpError as e:
            status = getattr(e, "status_code", None) or (e.resp.status if hasattr(e, "resp") and e.resp else None)
            if status in (403, 429, 500, 502, 503, 504):
                _retry_sleep(attempt)
                continue
            raise
        except Exception:
            _retry_sleep(attempt)
    raise RuntimeError(f"Failed to download file {file_id} after {MAX_RETRIES} retries")

def export_google_file_with_retries(svc, file_id, export_mime, dest_path: pathlib.Path):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(MAX_RETRIES):
        try:
            req = svc.files().export_media(fileId=file_id, mimeType=export_mime)
            with io.FileIO(dest_path, "wb") as fh:
                downloader = MediaIoBaseDownload(fh, req, chunksize=CHUNK_SIZE)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
            return
        except HttpError as e:
            status = getattr(e, "status_code", None) or (e.resp.status if hasattr(e, "resp") and e.resp else None)
            if status in (403, 429, 500, 502, 503, 504):
                _retry_sleep(attempt)
                continue
            raise
        except Exception:
            _retry_sleep(attempt)
    raise RuntimeError(f"Failed to export file {file_id} after {MAX_RETRIES} retries")

def dedupe_path(path: pathlib.Path) -> pathlib.Path:
    if not path.exists():
        return path
    i = 1
    stem, suffix = path.stem, path.suffix
    while True:
        candidate = path.with_name(f"{stem} ({i}){suffix}")
        if not candidate.exists():
            return candidate
        i += 1

# -------- CRAWL --------
def crawl_shared_folder(folder_id: str, out_root: pathlib.Path):
    svc = get_service()
    root = get_item(svc, folder_id)
    if root["mimeType"] != "application/vnd.google-apps.folder":
        raise ValueError("The provided ID is not a folder. Use a folder link/ID.")

    base = out_root / root["name"]
    base.mkdir(parents=True, exist_ok=True)

    stack = [(root["id"], base)]
    pbar = tqdm(total=0, unit="file", desc="Downloading", dynamic_ncols=True)
    count = 0

    while stack:
        fid, here = stack.pop()
        for child in list_children(svc, fid):
            name = child["name"]
            mime = child["mimeType"]
            cid = child["id"]

            # Follow shortcuts
            if mime == "application/vnd.google-apps.shortcut":
                sd = child.get("shortcutDetails", {})
                target_id = sd.get("targetId")
                target_mime = sd.get("targetMimeType")
                if not target_id:
                    continue
                cid, mime = target_id, (target_mime or mime)

            if mime == "application/vnd.google-apps.folder":
                subdir = here / name
                subdir.mkdir(parents=True, exist_ok=True)
                stack.append((cid, subdir))
                continue

            dest = here / name
            if mime.startswith("application/vnd.google-apps."):
                export_mime, ext = EXPORT_MAP.get(mime, FALLBACK_EXPORT)
                dest = dest.with_suffix(ext)
                dest = dedupe_path(dest)
                try:
                    export_google_file_with_retries(svc, cid, export_mime, dest)
                except Exception:
                    if export_mime != FALLBACK_EXPORT[0]:
                        try:
                            dest_pdf = dedupe_path(here / (pathlib.Path(name).stem + ".pdf"))
                            export_google_file_with_retries(svc, cid, FALLBACK_EXPORT[0], dest_pdf)
                        except Exception as e2:
                            print(f"Failed to export {name}: {e2}")
                    else:
                        print(f"Failed to export {name}")
            else:
                dest = dedupe_path(dest)
                try:
                    download_binary_with_retries(svc, cid, dest)
                except Exception as e:
                    print(f"Failed to download {name}: {e}")

            count += 1
            pbar.total = count
            pbar.update(1)

    pbar.close()
    print(f"\nDone. Saved to: {base.resolve()}")

# -------- MAIN --------
if __name__ == "__main__":
    folder_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FOLDER_ID
    outdir = pathlib.Path(OUTPUT_DIR)
    outdir.mkdir(parents=True, exist_ok=True)
    crawl_shared_folder(folder_id, outdir)
