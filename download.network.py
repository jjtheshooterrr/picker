# download_shared_folder.py
import os, io, sys, time, argparse, pathlib
from typing import Dict, Tuple, Iterable, Optional
from tqdm import tqdm

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google_auth_httplib2 import AuthorizedHttp
import httplib2

# ---- CONFIG ----
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
EXPORT_MAP = {
    "application/vnd.google-apps.document": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"
    ),
    "application/vnd.google-apps.spreadsheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"
    ),
    "application/vnd.google-apps.presentation": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx"
    ),
    "application/vnd.google-apps.drawing": ("image/png", ".png"),
}
FALLBACK_EXPORT = ("application/pdf", ".pdf")

# ---- AUTH ----
def get_service(timeout: int = 120):
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

    http = AuthorizedHttp(creds, http=httplib2.Http(timeout=timeout))
    return build("drive", "v3", http=http, cache_discovery=False)

# ---- HELPERS ----
def list_children(svc, folder_id):
    q = f"'{folder_id}' in parents and trashed=false"
    fields = "nextPageToken, files(id,name,mimeType,shortcutDetails)"
    token = None
    while True:
        resp = svc.files().list(
            q=q,
            fields=fields,
            pageSize=1000,
            pageToken=token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        for f in resp.get("files", []):
            yield f
        token = resp.get("nextPageToken")
        if not token:
            break

def get_item(svc, fid):
    return svc.files().get(fileId=fid, fields="id,name,mimeType", supportsAllDrives=True).execute()

def dedupe_path(path: pathlib.Path) -> pathlib.Path:
    if not path.exists():
        return path
    i = 1
    while True:
        p2 = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not p2.exists():
            return p2
        i += 1

def _retry_sleep(a): time.sleep(0.8 * (2 ** a))

def download_file(svc, fid, dest, chunk=8 * 1024 * 1024):
    for a in range(8):
        try:
            req = svc.files().get_media(fileId=fid, acknowledgeAbuse=True)
            with io.FileIO(dest, "wb") as fh:
                downloader = MediaIoBaseDownload(fh, req, chunksize=chunk)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
            return
        except HttpError as e:
            code = getattr(e.resp, "status", None)
            if code in (403, 429, 500, 502, 503, 504):
                _retry_sleep(a)
                continue
            raise
    raise RuntimeError(f"Failed to download {fid}")

def export_google_file(svc, fid, mime, dest, chunk=8 * 1024 * 1024):
    for a in range(8):
        try:
            req = svc.files().export_media(fileId=fid, mimeType=mime)
            with io.FileIO(dest, "wb") as fh:
                dl = MediaIoBaseDownload(fh, req, chunksize=chunk)
                done = False
                while not done:
                    _, done = dl.next_chunk()
            return
        except HttpError as e:
            code = getattr(e.resp, "status", None)
            if code in (403, 429, 500, 502, 503, 504):
                _retry_sleep(a)
                continue
            raise

# ---- MAIN ----
def crawl(folder_id, outdir, list_only=False, max_files=None, chunk=8 * 1024 * 1024, timeout=120):
    svc = get_service(timeout)
    root = get_item(svc, folder_id)
    if root["mimeType"] != "application/vnd.google-apps.folder":
        raise ValueError("Provided ID is not a folder.")
    base = outdir / root["name"]
    base.mkdir(parents=True, exist_ok=True)

    def walk(fid, path):
        stack = [(fid, path)]
        while stack:
            fid, path = stack.pop()
            for child in list_children(svc, fid):
                mime = child["mimeType"]
                cid = child["id"]
                name = child["name"]
                if mime == "application/vnd.google-apps.folder":
                    sub = path / name
                    sub.mkdir(parents=True, exist_ok=True)
                    stack.append((cid, sub))
                else:
                    yield path, {"id": cid, "name": name, "mimeType": mime}

    items = list(walk(folder_id, base))
    if list_only:
        print(f"{len(items)} items in '{root['name']}'")
        for i, (_, m) in enumerate(items[:50], 1):
            print(f"{i:3d}. {m['name']}  [{m['mimeType']}]")
        if len(items) > 50:
            print(f"...and {len(items)-50} more")
        return

    done = 0
    for here, meta in tqdm(items, desc="Downloading", unit="file"):
        name, mime, fid = meta["name"], meta["mimeType"], meta["id"]
        dest = dedupe_path(here / name)
        try:
            if mime.startswith("application/vnd.google-apps."):
                m, ext = EXPORT_MAP.get(mime, FALLBACK_EXPORT)
                dest = dest.with_suffix(ext)
                export_google_file(svc, fid, m, dest, chunk)
            else:
                download_file(svc, fid, dest, chunk)
        except Exception as e:
            print(f"Failed: {name} -> {e}")
        done += 1
        if max_files and done >= max_files:
            break
    print(f"\nDone. Saved to {base.resolve()}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("folder_id")
    p.add_argument("--list", action="store_true")
    p.add_argument("--out", default="SharedBackup")
    p.add_argument("--max", type=int, default=0)
    p.add_argument("--chunk", type=int, default=8 * 1024 * 1024)
    p.add_argument("--timeout", type=int, default=120)
    a = p.parse_args()

    outdir = pathlib.Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)

    crawl(a.folder_id, outdir, a.list, (a.max if a.max > 0 else None), a.chunk, a.timeout)
