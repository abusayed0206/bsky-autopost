# bsky-autopost
A repo for bsky autopost action files.

## Overview
This repository contains Python scripts to automatically fetch and post beautiful wallpaper images to Bluesky:

- **Bing Wallpaper** - Daily Bing wallpaper of the day (1080p quality)
- **Windows Spotlight** - Windows Spotlight images (up to 4 images)
- **Windows LockScreen** - Windows LockScreen images (up to 4 images)

All images are automatically compressed to meet Bluesky's 1MB size limit while maintaining good quality.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Required packages:**
- `atproto` - Bluesky/AT Protocol SDK
- `requests` - HTTP library
- `Pillow` - Image processing (for compression)
- `python-dotenv` - Environment variables (optional, for local development)

### 2. Setup for GitHub Actions (Recommended)

See **[GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)** for complete instructions on:
- Setting up GitHub Secrets
- Enabling automated workflows
- Scheduling posts
- Troubleshooting

**Quick setup:**
1. Go to repository Settings → Secrets → Actions
2. Add `BSKY_USERNAME` (your Bluesky handle)
3. Add `BSKY_APP_PASSWORD` (generate at https://bsky.app/settings/app-passwords)
4. Workflows will run automatically on schedule!

### 3. Local Development Setup

Create a `.env` file in the root directory:

```env
BSKY_USERNAME=your-handle.bsky.social
BSKY_APP_PASSWORD=your-app-password
```

**Important:** Use an [App Password](https://bsky.app/settings/app-passwords), not your main account password!

## Usage

### Run Scripts Manually

```bash
# Post Bing wallpaper (1080p, auto-compressed)
python scripts/bing_bluesky.py

# Post Windows Spotlight images (up to 4, auto-compressed)
python scripts/spotlight_bluesky.py

# Post Windows LockScreen images (up to 4, auto-compressed)
python scripts/lockscreen_bluesky.py
```

### Automated Posting via GitHub Actions

The repository includes GitHub Actions workflows that run automatically:

- **Bing Wallpaper**: Daily at 5:47 AM GMT+6
- **Windows Spotlight**: Daily at 6:10 PM GMT+6
- **Windows LockScreen**: Daily at 2:29 AM GMT+6

See [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md) for setup instructions.

## Scripts

### `bing_bluesky.py`
Fetches the daily Bing wallpaper (1080p quality) and posts it to Bluesky with metadata including copyright information and region. Images are automatically compressed if needed.

### `spotlight_bluesky.py`
Fetches Windows Spotlight images (up to 4) from a random region and posts them as a media group to Bluesky. Each image is validated and compressed to meet size limits.

### `lockscreen_bluesky.py`
Fetches Windows LockScreen images (up to 4) from a random region and posts them as a media group to Bluesky. Includes automatic compression for large images.

## Features

- 🎨 High-quality image downloads (1080p for Bing)
- 🗜️ **Automatic image compression** to meet Bluesky's 1MB limit
- 🌍 Random region selection for diverse content
- 📝 Automatic caption generation with metadata
- 🖼️ Support for multiple images (up to 4 per post)
- ✅ Image validation before posting
- 🔐 Secure authentication using Bluesky App Passwords
- ⚙️ Works with GitHub Actions (scheduled posting)
- 🔄 Automatic .env file loading for local development

## Image Compression

All scripts include intelligent image compression:
- Images are automatically checked against Bluesky's 1MB limit
- Compression uses quality reduction first (85% → 40%)
- If needed, images are resized while maintaining aspect ratio
- Original quality is preserved when possible
- Compression happens transparently before upload

## Environment Variables

The scripts support two methods:

**1. For GitHub Actions (Production):**
- Set `BSKY_USERNAME` and `BSKY_APP_PASSWORD` as repository secrets
- Scripts will automatically use these values

**2. For Local Development:**
- Create a `.env` file with your credentials
- Scripts will automatically load it if present
- Falls back to system environment variables if `.env` doesn't exist

## Technologies

- **Python 3.9+**
- **atproto SDK** - Official Python SDK for AT Protocol / Bluesky
- **requests** - HTTP library for image downloading
- **Pillow (PIL)** - Image processing and compression
- **python-dotenv** - Environment variable management (optional)

## Testing

Run the test script to verify your setup:

```bash
python test_setup.py
```

This will check:
- Package installations
- Environment variables
- Bluesky login credentials
- Connection to Bluesky API

## GitHub Actions Workflows

Three automated workflows are included:

1. **bing-bluesky.yml** - Posts Bing wallpaper daily
2. **spotlight-bluesky.yml** - Posts Spotlight images daily
3. **lockscreen-bluesky.yml** - Posts LockScreen images daily

Each workflow:
- Runs on Ubuntu latest
- Uses Python 3.11
- Caches pip dependencies for speed
- Can be triggered manually or by schedule
- Uses repository secrets for credentials

## Notes

- Bluesky posts have a 300 character limit for text
- Images are limited to 1MB - automatically compressed if larger
- Up to 4 images can be posted in a single post
- Alt text is generated from image metadata for accessibility
- The `.env` file is ignored by git for security
- Workflows use repository secrets, not `.env` files

## Troubleshooting

**Image too large errors:**
- Make sure `Pillow` is installed: `pip install Pillow`
- The scripts will automatically compress images

**Login failures:**
- Use an App Password, not your main password
- Generate one at: https://bsky.app/settings/app-passwords
- Check your username format (e.g., `handle.bsky.social`)

**GitHub Actions not running:**
- Check repository secrets are set correctly
- Verify workflows are enabled in Actions tab
- Review workflow logs for specific errors

## License

See LICENSE file for details.
