"""
Helper tool to generate YOUTUBE_REFRESH_TOKEN.
Opens authorization flow and automatically saves YOUTUBE_REFRESH_TOKEN into .env.
"""

import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def update_env_file(refresh_token):
    env_path = os.path.abspath(".env")
    if not os.path.exists(env_path):
        with open(env_path, "w") as f:
            f.write(f"YOUTUBE_REFRESH_TOKEN={refresh_token}\n")
        return

    with open(env_path, "r") as f:
        lines = f.readlines()

    updated = False
    new_lines = []
    for line in lines:
        if line.startswith("YOUTUBE_REFRESH_TOKEN="):
            new_lines.append(f"YOUTUBE_REFRESH_TOKEN={refresh_token}\n")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"YOUTUBE_REFRESH_TOKEN={refresh_token}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)
    print(f"[+] Successfully saved YOUTUBE_REFRESH_TOKEN to {env_path}", flush=True)

def main():
    secrets_file = "client_secrets.json"
    if len(sys.argv) > 1:
        secrets_file = sys.argv[1]

    if not os.path.exists(secrets_file):
        print(f"[-] Error: {secrets_file} not found.", flush=True)
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)
    print("[*] Starting local OAuth server...", flush=True)
    
    # access_type='offline' and prompt='consent' forces Google to issue a refresh_token
    creds = flow.run_local_server(
        port=0,
        open_browser=True,
        access_type="offline",
        prompt="consent"
    )

    print("\n" + "=" * 60, flush=True)
    print("SUCCESSFULLY AUTHORIZED!", flush=True)
    print(f"REFRESH_TOKEN: {creds.refresh_token}", flush=True)
    print("=" * 60 + "\n", flush=True)

    if creds.refresh_token:
        update_env_file(creds.refresh_token)

if __name__ == "__main__":
    main()
