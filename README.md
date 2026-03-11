# Bluesky Auto-Post Scripts

Automated scripts to fetch and post beautiful wallpapers and Bangla date images to Bluesky from various Microsoft sources and cultural data.

## 📊 Bluesky Account Stats

<!-- BSKY-STATS:START -->
| Stat | Value |
|------|-------|
| 🔗 Profile | [sayed.app](https://bsky.app/profile/sayed.app) |
| 📝 Posts | 1,846 |
| 👥 Followers | 22 |
| 👤 Following | 9 |
| 🕒 Last Updated | 2026-03-11 02:42 UTC |
<!-- BSKY-STATS:END -->

## 📜 Scripts

### 🗓️ Bangla Date (`bangla_date_bluesky.py`)

Generates and posts a beautiful dark-themed image with today's Bangla date information.

**Features:**
- Fetches real-time Bangla calendar data using the `bangla` library
- Displays date in Bangla numerals (e.g., ২৩ কার্তিক, ১৪৩২ বঙ্গাব্দ)
- Shows weekday and season information (বারঃ শুক্রবার, ঋতুঃ হেমন্ত)
- Dark theme design with Bluesky embed style
- Fetches user profile (avatar, display name, handle) from Bluesky API
- Uses custom Codepotro Ekush Bangla font (downloaded from codepotro.com)
- Official Bluesky butterfly logo in header
- Automatic daily posting at 5:00 AM UTC+6 (Bangladesh Time)
- Rich text hashtags: `#Bangladesh #Bangla #বাংলাদেশ #বাংলা #বাংলাতারিখ #তারিখ #date #BanglaDate`
- GitHub Actions workflow for automated daily posts
- All assets (font, logo) downloaded dynamically - no repo storage needed

---

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
