"""
Helper tool to generate YOUTUBE_REFRESH_TOKEN.
Run this once on your local machine to obtain your credentials for GitHub Secrets.
"""

import sys
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/get_youtube_token.py <path_to_client_secrets.json>")
        sys.exit(1)

    client_secrets_file = sys.argv[1]
    flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n" + "=" * 60)
    print("SUCCESS! Add these to your GitHub Repository Secrets:")
    print("=" * 60)
    print(f"YOUTUBE_CLIENT_ID:     {creds.client_id}")
    print(f"YOUTUBE_CLIENT_SECRET: {creds.client_secret}")
    print(f"YOUTUBE_REFRESH_TOKEN: {creds.refresh_token}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
