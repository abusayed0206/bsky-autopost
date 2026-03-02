#!/usr/bin/env python3
"""
Fetch Bluesky account stats and update the README.md with them.
"""
import os
import re
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings('ignore', category=UserWarning, module='pydantic')

from atproto import Client

# Load environment variables from .env file (for local development)
try:
    from dotenv import load_dotenv
    root_dir = Path(__file__).parent.parent
    env_path = root_dir / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, will use system env vars


def fetch_stats(client, username):
    """Fetch account stats from Bluesky profile."""
    profile = client.get_profile(actor=username)
    return {
        'handle': profile.handle,
        'display_name': profile.display_name or profile.handle,
        'url': f"https://bsky.app/profile/{profile.handle}",
        'posts': profile.posts_count or 0,
        'followers': profile.followers_count or 0,
        'following': profile.follows_count or 0,
        'updated_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
    }


def update_readme(stats):
    """Replace content between BSKY-STATS markers in README.md."""
    root_dir = Path(__file__).parent.parent
    readme_path = root_dir / 'README.md'

    content = readme_path.read_text(encoding='utf-8')

    stats_block = (
        "<!-- BSKY-STATS:START -->\n"
        "| Stat | Value |\n"
        "|------|-------|\n"
        f"| 🔗 Profile | [{stats['handle']}]({stats['url']}) |\n"
        f"| 📝 Posts | {stats['posts']:,} |\n"
        f"| 👥 Followers | {stats['followers']:,} |\n"
        f"| 👤 Following | {stats['following']:,} |\n"
        f"| 🕒 Last Updated | {stats['updated_at']} |\n"
        "<!-- BSKY-STATS:END -->"
    )

    pattern = r'<!-- BSKY-STATS:START -->.*?<!-- BSKY-STATS:END -->'
    if re.search(pattern, content, re.DOTALL):
        new_content = re.sub(pattern, stats_block, content, flags=re.DOTALL)
    else:
        new_content = content + '\n\n' + stats_block + '\n'

    readme_path.write_text(new_content, encoding='utf-8')
    print("✅ README.md updated with Bluesky stats")


def main():
    """Main function."""
    username = os.environ.get('BSKY_USERNAME')
    app_password = os.environ.get('BSKY_APP_PASSWORD')

    if not username or not app_password:
        print("❌ Error: BSKY_USERNAME and BSKY_APP_PASSWORD must be set")
        sys.exit(1)

    print("🔐 Logging into Bluesky...")
    try:
        client = Client()
        client.login(username, app_password)
        print(f"✅ Logged in as @{username}")
    except Exception as e:
        print(f"❌ Error logging into Bluesky: {e}")
        sys.exit(1)

    print("📊 Fetching account stats...")
    stats = fetch_stats(client, username)

    print(f"  🔗 Profile: {stats['url']}")
    print(f"  📝 Posts: {stats['posts']:,}")
    print(f"  👥 Followers: {stats['followers']:,}")
    print(f"  👤 Following: {stats['following']:,}")

    print("📝 Updating README.md...")
    update_readme(stats)

    print("🎉 Done!")


if __name__ == "__main__":
    main()
