# Bluesky Auto-Post Scripts

Automated scripts to fetch and post beautiful wallpapers to Bluesky from various Microsoft sources.

## 📜 Scripts

### 🖼️ Bing Wallpaper (`bing_bluesky.py`)

Fetches and posts the daily Bing wallpaper of the day.

**Features:**
- Downloads Bing's daily wallpaper in 1080p quality (1920x1080)
- Random region selection from 14 regions (US, JP, AU, GB, DE, NZ, CA, IN, FR, IT, ES, BR, etc.)
- Automatic image compression using quality reduction (100%→95%→90%...→20%)
- No image resizing - maintains original dimensions
- Smart caption with 300 character limit handling:
  - Full caption with copyright, region, and hashtags
  - Auto-drops region if over 300 chars
  - Auto-drops hashtags if still over 300 chars
- Rich text hashtags (clickable): `#BingWallpaper #DailyWallpaper #Photography #NaturePhotography #Wallpaper`
- Posts single image with detailed copyright info

---

### 🌟 Windows Spotlight (`spotlight_bluesky.py`)

Fetches and posts Windows Spotlight lock screen images (up to 4 images per post).

**Features:**
- Downloads up to 4 Windows Spotlight images in highest available quality
- Random locale selection from 12 locales (US, JP, AU, GB, DE, NZ, CA, IN, FR, IT, ES, BR)
- Automatic image compression using quality reduction (100%→95%→90%...→20%)
- No image resizing - maintains original dimensions
- Telegram-style captions with titles only in main post
- Copyright and attribution details included in each image's alt text
- Smart caption with 300 character limit handling
- Rich text hashtags (clickable): `#WindowsSpotlight #Spotlight #Wallpaper #Microsoft #Photography`
- Supports both single and multi-image posts (1-4 images)

---

### 🔒 Windows LockScreen (`lockscreen_bluesky.py`)

Fetches and posts Windows LockScreen images (up to 4 images per post).

**Features:**
- Downloads up to 4 Windows LockScreen images in highest available quality
- Random locale selection from 12 locales (US, JP, AU, GB, DE, NZ, CA, IN, FR, IT, ES, BR)
- Automatic image compression using quality reduction (100%→95%→90%...→20%)
- No image resizing - maintains original dimensions
- Telegram-style captions with titles only in main post
- Copyright and attribution details included in each image's alt text
- Smart caption with 300 character limit handling
- Rich text hashtags (clickable): `#WindowsLockScreen #LockScreen #Wallpaper #Microsoft #Photography`
- Supports both single and multi-image posts (1-4 images)

---
