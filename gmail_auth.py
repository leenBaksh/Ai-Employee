from google_auth_oauthlib.flow import InstalledAppFlow
from pathlib import Path
import urllib.parse

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
]

flow = InstalledAppFlow.from_client_secrets_file(
    '/mnt/d/Hackathon-00/Ai-Employee/secrets/gmail_credentials.json', SCOPES
)
flow.redirect_uri = 'http://localhost:8085/'
auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

print()
print('1. Open this URL in your browser:')
print(auth_url)
print()
print('2. Sign in and click Allow')
print('3. Browser shows "This site cant be reached" - thats OK')
print('4. Copy the FULL URL from the address bar and paste below')
print()

redirect = input('Paste the full redirect URL: ')
code = urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)['code'][0]
flow.fetch_token(code=code)
Path('/mnt/d/Hackathon-00/Ai-Employee/secrets/gmail_token.json').write_text(
    flow.credentials.to_json()
)
print('Token saved!')
