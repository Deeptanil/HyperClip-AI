# Autonomous Stickman Video Generator & Social Media Publisher

A 100% free, zero-cost, cloud-scheduled autonomous pipeline inspired by [Abhinavkumar-07/youtube-instagram-auto-uploader](https://github.com/Abhinavkumar-07/youtube-instagram-auto-uploader). It automatically generates ChainsFR-style stickman stop-motion videos and publishes them daily to **YouTube Shorts**, **Instagram Reels**, and **TikTok**.

---

## ⚡ Architecture

```
[GitHub Actions (Daily 2PM UTC Cron)]
                 │
  [1. Story & Script Generator (Gemini Flash / Built-in)]
                 │
  [2. Voice & Subtitles (edge-tts + Impact Karaoke ASS)]
                 │
  [3. 8 FPS Stop-Motion Engine (PIL + Line Boiling + Camera Zooms)]
                 │
  [4. SFX & FFmpeg 9:16 Video Assembly (~4s render)]
                 │
  [5. Multi-Platform Auto Publisher]
       ├── YouTube Shorts (YouTube Data API v3)
       ├── Instagram Reels (Meta Graph API / Instagrapi)
       └── TikTok (Playwright session cookies)
                 │
  [6. Update & Commit posted_log.json]
```

---

## 🚀 Running Free Forever on GitHub Actions

You do not need a paid server or your own computer running. GitHub Actions provides **unlimited runner minutes for public repos** and **2,000 minutes/month for private repos** (a daily 4-second render consumes < 1 minute/day).

### 1. Fork or Push this Repository to GitHub
```bash
git init
git add .
git commit -m "feat: automated stickman shorts generator"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### 2. Configure GitHub Secrets
Go to your repo: **Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Description | Where to get it |
| :--- | :--- | :--- |
| `YOUTUBE_CLIENT_ID` | Google OAuth Client ID | Google Cloud Console (APIs & Services) |
| `YOUTUBE_CLIENT_SECRET`| Google OAuth Client Secret | Google Cloud Console (APIs & Services) |
| `YOUTUBE_REFRESH_TOKEN`| Long-lived OAuth Refresh Token | Run `python tools/get_youtube_token.py <client_secrets.json>` |
| `INSTAGRAM_ACCOUNT_ID` | Instagram Creator/Business ID | Meta for Developers / Graph API Explorer |
| `META_ACCESS_TOKEN` | Long-lived System User Access Token | Meta for Developers Dashboard |
| `GEMINI_API_KEY` | *(Optional)* For custom AI scripts | Google AI Studio (Free) |

---

## 💻 Local Testing & Manual Runs

### Generate Video Locally:
```bash
python main.py --output my_short.mp4
```

### Run Full Auto-Poster Locally:
```bash
python auto_poster.py --platforms youtube instagram
```
