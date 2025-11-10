\# Google Drive Shared Folder Downloader



Python script to download all files from a shared Google Drive folder using the Drive API.



\## Usage

1\. Install dependencies:

pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib tqdm



markdown

Copy code

2\. Put your `credentials.json` in the same folder.

3\. Run:

python download\_shared\_folder.py <FOLDER\_ID>



ruby

Copy code



> ⚠️ Never commit `credentials.json` or `token.json` — they contain private keys.

