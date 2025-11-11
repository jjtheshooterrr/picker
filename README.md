\# Google Drive Shared Folder Downloader



Python script to download all files from a shared Google Drive folder using the Drive API.



\## Usage

1\. Install dependencies:

pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib tqdm



markdown

Copy code

2\. Put your `credentials.json` in the same folder.
in this format {"installed":{"client_id":"85654645-ac9iip19lfjj7pniopghgfhgf.apps.googleusercontent.com","project_id":"gogolepicker","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_secret":"fgfgzdX-fhgfggfk_ghfxhghxfhL-qghh","redirect_uris":["http://localhost"]}}
3\. Run:

python download\_shared\_folder.py <FOLDER\_ID>



ruby

Copy code



> ⚠️ Never commit `credentials.json` or `token.json` — they contain private keys.

