# Google Drive Shared Folder Downloader

Two Python scripts to download an entire Google Drive folder (including Shared Drives) to your local machine.

- `download.network.py` — network-tuned version (timeouts, bigger chunks, CLI flags)
- `download_shared_folder.py` — simpler version with shortcut following and PDF export fallback

> **Important:** Never commit `credentials.json` or `token.json` to your repository.

---

## 1. Google Cloud Setup

Before using these scripts, you need a Google Cloud project with the **Google Drive API** enabled.

### Step 1: Create a Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Click **Select a project → New Project**.
3. Give it a name (for example, `DriveDownloader`) and click **Create**.

### Step 2: Enable the Google Drive API
1. In the sidebar, go to **APIs & Services → Library**.
2. Search for **Google Drive API**.
3. Click **Enable**.

### Step 3: Create OAuth Credentials
1. Go to **APIs & Services → Credentials**.
2. Click **Create Credentials → OAuth client ID**.
3. Choose **Desktop App** and give it a name (e.g., `Drive Downloader`).
4. After creation, click **Download JSON** — this is your client secrets file.

### Step 4: Rename and Place the File
Rename the downloaded file to:
credentials.json

yaml
Copy code
and place it in the same directory as the Python scripts.

> On first run, a browser window will open for authentication.  
> After signing in, a `token.json` file is generated locally to store your access token.

---

## 2. Prerequisites

- Python 3.9+ (works on Windows, macOS, or Linux)
- Active internet connection
- `credentials.json` from the Google Cloud setup above

---

## 3. Installation

```bash
# From the repository root
python -m venv .venv

# Activate the environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install --upgrade pip
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2 httplib2 tqdm
4. Which Script Should I Use?
Feature	download.network.py (recommended for speed/control)	download_shared_folder.py (safer exports)
Chunk size & timeouts	Configurable (--chunk, --timeout)	Fixed (1 MiB)
CLI flags (--list, --max, --out)	Yes	Minimal
Acknowledge abuse files	Yes	No
Follows Drive shortcuts	Not currently	Yes
Export fallback to PDF if Office export fails	No	Yes
Memory usage	Builds file list, then downloads	Streams during traversal

Use download_shared_folder.py if your folder contains Google Docs, Sheets, or Slides that must be exported even when Office export fails.
Use download.network.py if you want performance, better timeout control, and chunk tuning.

5. Quick Start
bash
Copy code
# Recommended: network version
python download.network.py <FOLDER_ID> --out SharedBackup
This creates:

php-template
Copy code
SharedBackup/<DriveFolderName>/
To list contents without downloading:

bash
Copy code
python download.network.py <FOLDER_ID> --list
6. Command Reference: download.network.py
bash
Copy code
python download.network.py <FOLDER_ID> [options]
Positional argument

<FOLDER_ID> — the ID from your Drive folder URL

Options

--out PATH — output directory (default: SharedBackup)

--list — list files without downloading

--max N — download at most N files (useful for testing)

--chunk BYTES — chunk size in bytes (default: 8 MiB)
Example: use --chunk 1048576 for slower or unstable connections

--timeout SECONDS — HTTP timeout (default: 120 seconds)

Examples

bash
Copy code
# List only
python download.network.py 1nBF5nJdKho3gW2yPkPNxuHd8616up010 --list

# Download a few files for testing
python download.network.py 1nBF5nJdKho3gW2yPkPNxuHd8616up010 --max 25 --out SharedTest

# Adjust for unstable connections
python download.network.py 1nBF5nJdKho3gW2yPkPNxuHd8616up010 --out SharedBackup --chunk 1048576 --timeout 60
7. Command Reference: download_shared_folder.py
bash
Copy code
python download_shared_folder.py [FOLDER_ID]
If [FOLDER_ID] is omitted, it uses the DEFAULT_FOLDER_ID in the script.

The output directory is OUTPUT_DIR (default: SharedBackup).

Follows shortcuts and attempts PDF export if Office format export fails.

Example

bash
Copy code
python download_shared_folder.py 1QmcPpP9XNJzB3ZiMdmigdOZT_JWMHkPB
8. File Structure
Both scripts create a mirrored local structure:

php-template
Copy code
<OUT_DIR>/<DriveFolderName>/
Existing files are renamed as name (1).ext, name (2).ext, etc.

To avoid duplicates, delete the existing folder before re-running.

9. Troubleshooting
The script appears to hang.
Use smaller chunks and shorter timeouts so requests retry more quickly:

bash
Copy code
python download.network.py <FOLDER_ID> --chunk 1048576 --timeout 60
Resuming downloads.
Re-run the command. Existing files are preserved (duplicates will be renamed).

Abuse-flagged files.
download.network.py uses acknowledgeAbuse=True to help download flagged content.

Google file exports.
Docs, Sheets, and Slides are exported to Office formats.
If conversion fails, download_shared_folder.py automatically tries PDF.

Shortcuts.
If the Drive folder contains shortcuts, use download_shared_folder.py (it resolves them).

10. Security
Keep credentials.json and token.json private and never commit them to Git.

.gitignore already excludes them.

These files grant API access to your Drive account.

11. Cleanup Instructions
To clear your OAuth token and force a fresh login, delete token.json.

To restart cleanly:

bash
Copy code
rm -rf SharedBackup
rm token.json
Then re-run the script; it will reauthenticate and rebuild the folder structure.

Credits
Built with google-api-python-client, google-auth, google-auth-oauthlib, google-auth-httplib2, httplib2, and tqdm.
