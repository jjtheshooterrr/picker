Google Drive Shared Folder Downloader

Two Python scripts to download an entire Google Drive folder (including Shared Drives) to your local machine.

download.network.py – network-tuned version (timeouts, bigger chunks, CLI flags).

download_shared_folder.py – simpler version with shortcut following & PDF export fallback.

⚠️ Never commit credentials.json or token.json.

1) Prerequisites

Python 3.9+ (works on Windows/macOS/Linux)

A Google Cloud project with Google Drive API enabled

An OAuth Desktop client and its credentials.json

Place credentials.json in the repo root (same folder as the scripts).
On first run you’ll authenticate in the browser; a token.json is then created locally.

2) Install
# from repo root
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install --upgrade pip
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2 httplib2 tqdm

3) Which script should I use?
Feature	download.network.py (recommended for speed/control)	download_shared_folder.py (safer exports)
Chunk size & timeouts	✅ configurable (--chunk, --timeout)	❌ fixed (1 MiB)
CLI flags (--list, --max, --out)	✅ yes	❌ minimal
Acknowledge abuse files	✅ yes	❌ no
Follows Drive shortcuts	❌ not currently	✅ yes
Export fallback to PDF if Office export fails	❌ no	✅ yes
Memory usage	Builds file list, then downloads	Streams during traversal

If you have lots of Google Docs/Sheets/Slides that must be exported even when Office export fails → use download_shared_folder.py.
If you want performance & robust networking → use download.network.py.

4) Quick Start
# Network version (recommended)
python download.network.py <FOLDER_ID> --out SharedBackup


This creates:

SharedBackup/<DriveFolderName>/


…matching the Drive folder’s name and layout.

To just list what’s inside:

python download.network.py <FOLDER_ID> --list

5) Command Reference (download.network.py)
python download.network.py <FOLDER_ID> [options]


Positional

<FOLDER_ID> – the ID from your Drive folder URL

Options

--out PATH — output base directory (default: SharedBackup)

--list — list files without downloading

--max N — download at most N files (useful to test)

--chunk BYTES — download chunk size (default: 8388608 = 8 MiB)
If your network hangs, try smaller: --chunk 1048576

--timeout SECONDS — network timeout per HTTP request (default: 120)

Examples

# List only
python download.network.py 1nBF5nJdKho3gW2yPkPNxuHd8616up010 --list

# Download a few first
python download.network.py 1nBF5nJdKho3gW2yPkPNxuHd8616up010 --max 25 --out SharedTest

# Tweak network behavior for unstable links
python download.network.py 1nBF5nJdKho3gW2yPkPNxuHd8616up010 --out SharedBackup --chunk 1048576 --timeout 60

6) Command Reference (download_shared_folder.py)
python download_shared_folder.py [FOLDER_ID]


If [FOLDER_ID] is omitted, it uses the DEFAULT_FOLDER_ID in the script.

Output base directory: OUTPUT_DIR in the script (default SharedBackup).

Follows shortcuts; if Office export fails, it tries PDF as a fallback.

Examples

python download_shared_folder.py 1QmcPpP9XNJzB3ZiMdmigdOZT_JWMHkPB

7) Where do files go?

Both scripts create a local mirror under the output directory:

<OUT_DIR>/<DriveFolderName>/


Existing filenames are deduped as name (1).ext, name (2).ext, …

To avoid duplicates when re-running, delete the prior folder or keep it and accept deduping.

8) Tips & Troubleshooting

It “hangs” on a file (Windows shows KeyboardInterrupt after a while)

Use smaller chunks and shorter timeouts so requests fail fast and retry:

python download.network.py <FOLDER_ID> --chunk 1048576 --timeout 60


Want to resume later?

Just re-run. Existing files will be saved as (1), (2), etc.
(If you prefer skip-if-exists behavior, see the note below.)

Abuse-flagged files

download.network.py uses acknowledgeAbuse=True, which often helps.

Exports

Google Docs/Sheets/Slides export to Office formats by default.

If that fails, only download_shared_folder.py will try PDF automatically.

Shortcuts

If your Drive has shortcuts pointing elsewhere, use download_shared_folder.py (follows them).

9) Security

Keep credentials.json and token.json out of git (.gitignore already covers these).

They grant access to your Drive data on this machine.
