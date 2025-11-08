#!/usr/bin/env python3
"""
Post year progress to Bluesky and reply to the docs post
"""
import os
import sys
import warnings
from datetime import datetime, timezone

# Suppress atproto library warnings
warnings.filterwarnings('ignore', category=UserWarning, module='pydantic')

from atproto import Client, models

# Load environment variables from .env file (for local development)
try:
    from dotenv import load_dotenv
    from pathlib import Path
    root_dir = Path(__file__).parent.parent
    env_path = root_dir / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, will use system env vars

# ============================================================================
# Year Progress Bar Functions (merged from year_progres.py)
# ============================================================================

def generate_progress_bar(value, max_value, bar_length=20):
    """Generate a Unicode progress bar for given value and max"""
    cutup = value / max_value
    # doesn't run if the percentage is over 100%
    if cutup > 1:
        return None, None
    
    percentage = cutup * 100
    # Scale to bar_length instead of 100
    repeat_amount = (percentage / 100) * bar_length
    looptimes = 1
    barstring = '█'
    # adds filled sections to progress bar (using solid blocks for better visibility)
    while looptimes < repeat_amount:
        barstring = barstring + '█'
        looptimes += 1
    # gets the decimal value
    decimal_part = repeat_amount % 1
    # adds a slight transparency depending on how much of the decimal value is there
    if decimal_part != 0:
        if decimal_part < 0.5:
            barstring = barstring + '▒'
        else:
            barstring = barstring + '▓'
    # counts the number of characters in the bar
    character_count = 0
    for char in barstring:
        character_count += 1
    empty_repeat_amount = bar_length - character_count
    # adds the blank space to the bar
    looptimes = 0
    while looptimes < empty_repeat_amount:
        barstring = barstring + '░'
        looptimes += 1
    
    return barstring, percentage

def get_year_progress():
    """Calculate year progress and return progress bar + percentage"""
    now = datetime.now(timezone.utc)
    year = now.year
    
    # Start of year (UTC)
    year_start = datetime(year, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    # Start of next year (UTC)
    year_end = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    # Calculate elapsed time
    year_total = (year_end - year_start).total_seconds()
    year_elapsed = (now - year_start).total_seconds()
    
    # Generate progress bar
    bar, percentage = generate_progress_bar(year_elapsed, year_total)
    
    if bar is None:
        return None, None, None
    
    remaining = 100 - percentage
    
    return bar, percentage, remaining

# ============================================================================
# Bluesky Posting Functions
# ============================================================================

def post_year_progress(client, test_mode=False):
    """Post year progress to Bluesky"""
    try:
        # Get year progress
        bar, percentage, remaining = get_year_progress()
        
        if bar is None:
            print("❌ Error: Could not calculate year progress")
            sys.exit(1)
        
        year = datetime.now(timezone.utc).year
        
        # Create post text with single-line progress bar and percentage
        post_text = f"📅 Year {year} Progress\n{bar} {percentage:.2f}%"
        
        print(f"📝 Post text ({len(post_text)} chars):")
        print(post_text)
        print()
        
        if test_mode:
            print("🧪 TEST MODE: Not posting to Bluesky")
            print(f"📊 Percentage: {percentage:.1f}%")
            print(f"📊 Remaining: {remaining:.1f}%")
            return None
        
        # Post to Bluesky
        print(f"📤 Posting to Bluesky...")
        response = client.send_post(text=post_text)
        
        print(f"✅ Successfully posted year progress!")
        print(f"Post URI: {response.uri}")
        
        return response
        
    except Exception as e:
        print(f"❌ Error posting year progress: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def reply_to_own_post(client, parent_post_response, test_mode=False):
    """Reply to the newly created year progress post with remaining percentage"""
    try:
        # Get year progress for remaining calculation
        bar, percentage, remaining = get_year_progress()
        
        if bar is None:
            print("❌ Error: Could not calculate remaining percentage")
            return
        
        year = datetime.now(timezone.utc).year
        
        # Create reply text - show exact remaining percentage with 2 decimals
        reply_text = f"{remaining:.2f}% of {year} is remaining."
        
        print(f"💬 Reply text: {reply_text}")
        
        if test_mode:
            print("🧪 TEST MODE: Not replying to own post")
            return
        
        # Create reply reference using create_strong_ref
        # Both parent and root point to the same post (our year progress post)
        parent_ref = models.AppBskyFeedPost.ReplyRef(
            parent=models.create_strong_ref(parent_post_response),
            root=models.create_strong_ref(parent_post_response)
        )
        
        # Send reply
        print(f"💬 Replying to year progress post...")
        reply_response = client.send_post(
            text=reply_text,
            reply_to=parent_ref
        )
        
        print(f"✅ Successfully replied to year progress post!")
        print(f"Reply URI: {reply_response.uri}")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not reply to own post: {e}")
        import traceback
        traceback.print_exc()
        # Don't exit on reply failure - main post was successful

def main():
    """Main function"""
    # Check for test mode
    test_mode = '--test' in sys.argv or os.environ.get('TEST_MODE', '').lower() == 'true'
    
    if test_mode:
        print("🧪 Running in TEST MODE")
        print()
    
    # Get environment variables
    username = os.environ.get('BSKY_USERNAME')
    app_password = os.environ.get('BSKY_APP_PASSWORD')
    
    if not test_mode and (not username or not app_password):
        print("❌ Error: BSKY_USERNAME and BSKY_APP_PASSWORD must be set")
        print("💡 For local testing, use: python year_progress_bluesky.py --test")
        sys.exit(1)
    
    if test_mode:
        # Test mode - just show what would be posted
        print("📊 Calculating year progress...")
        post_year_progress(None, test_mode=True)
        print()
        
        # Show what the reply would be
        reply_to_own_post(None, None, test_mode=True)
        print()
        
        print("✅ Test complete! Run without --test flag to actually post.")
        return
    
    # Initialize Bluesky client
    print("🔐 Logging into Bluesky...")
    try:
        client = Client()
        client.login(username, app_password)
        print(f"✅ Logged in as @{username}")
        print()
    except Exception as e:
        print(f"❌ Error logging into Bluesky: {e}")
        sys.exit(1)
    
    # Post year progress
    response = post_year_progress(client, test_mode=False)
    print()
    
    # Reply to own post with remaining percentage
    if response:
        reply_to_own_post(client, response, test_mode=False)
        print()
    
    print("🎉 Done!")

if __name__ == "__main__":
    main()
