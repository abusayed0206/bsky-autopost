"""
Bangla Date Image Generator and Bluesky Poster
Generates a dark-themed image with Bangla date information and posts to Bluesky
"""

import os
import sys
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import bangla
from dotenv import load_dotenv
from atproto import Client
import requests
from io import BytesIO

# Add parent directory to path for importing load_env
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to load environment variables (for local development)
try:
    from scripts.load_env import load_env
    load_env()
except ImportError:
    # In GitHub Actions, environment variables are already set
    print("ℹ️  Running in GitHub Actions or .env not available")
except Exception as e:
    print(f"ℹ️  Could not load .env: {e}")


def get_fallback_font(size):
    """
    Try to get Hind Siliguri font from system or use default
    """
    fallback_fonts = [
        "Hind-Siliguri.ttf",
        "HindSiliguri-Regular.ttf",
        "NotoSansBengali-Regular.ttf",
        "Arial.ttf",
    ]
    
    for font_name in fallback_fonts:
        try:
            return ImageFont.truetype(font_name, size)
        except:
            continue
    
    # If all fails, use default font
    return ImageFont.load_default()


def load_fonts():
    """
    Load the Codepotro Ekush font with fallback to Hind Siliguri
    """
    font_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                             "fonts", "Ekush-Regular.ttf")
    
    try:
        title_font = ImageFont.truetype(font_path, 72)
        date_font = ImageFont.truetype(font_path, 80)  # Reduced from 96 to 80
        info_font = ImageFont.truetype(font_path, 52)  # Increased from 48 to 52
        small_font = ImageFont.truetype(font_path, 36)
        return title_font, date_font, info_font, small_font
    except Exception as e:
        print(f"Warning: Could not load primary font: {e}")
        print("Falling back to system fonts...")
        return (get_fallback_font(72), get_fallback_font(80), 
                get_fallback_font(52), get_fallback_font(36))


def get_bangla_date_info():
    """
    Get today's Bangla date information
    """
    # Get today's date
    today = datetime.now()
    
    # Get Bangla date with ordinal
    bangla_date = bangla.get_date(today.day, today.month, today.year, ordinal=True)
    
    # Get English date for reference
    english_date = today.strftime("%d %B %Y")
    
    return bangla_date, english_date, today


def get_profile_info():
    """
    Get profile information from Bluesky API
    """
    handle = os.getenv('BLUESKY_HANDLE', os.getenv('BSKY_USERNAME', 'sayed.page'))
    # Extract just the handle part (before @ if present)
    if '@' in handle:
        handle = handle.split('@')[0]
    
    try:
        # Fetch profile from Bluesky API
        api_url = f"https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile"
        response = requests.get(api_url, params={"actor": handle}, timeout=10)
        
        if response.status_code == 200:
            profile = response.json()
            return {
                'handle': profile.get('handle', handle),
                'displayName': profile.get('displayName', handle),
                'avatar': profile.get('avatar', None)
            }
        else:
            print(f"⚠️  Could not fetch profile from API: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Error fetching profile: {e}")
    
    # Fallback to basic info
    return {
        'handle': handle,
        'displayName': handle,
        'avatar': None
    }


def create_bangla_date_image(output_path="bangla_date.png"):
    """
    Create a dark-themed image with Bangla date information
    Similar styling to the reference React code with Bluesky embed style
    """
    # Image dimensions
    width, height = 1200, 800
    
    # Dark theme colors (similar to reference code)
    bg_color = "#0f172a"  # slate-950
    card_bg = "#1e293b"   # slate-900
    border_color = "#334155"  # slate-800
    text_primary = "#e7e9ea"  # light text
    text_secondary = "#71767b"  # gray text
    accent_color = "#0085ff"  # blue accent
    
    # Create image
    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    title_font, date_font, info_font, small_font = load_fonts()
    
    # Get Bangla date info
    bangla_date_info, english_date, today = get_bangla_date_info()
    
    # Get profile info from API
    profile = get_profile_info()
    
    # Draw card background with border
    card_margin = 60
    card_rect = [card_margin, card_margin, width - card_margin, height - card_margin]
    draw.rounded_rectangle(card_rect, radius=20, fill=card_bg, outline=border_color, width=2)
    
    # Header section with profile info and Bluesky logo
    header_y = 90
    header_padding = 100
    
    # Calculate text positions first to center avatar
    text_x = header_padding + 64 + 20  # avatar_size + spacing
    text_line1_y = header_y
    text_line2_y = text_line1_y + 36
    
    # Calculate avatar position to center it between the two text lines
    total_text_height = 72  # Approximate height of both lines
    avatar_size = 64
    avatar_x = header_padding
    avatar_y = header_y + (total_text_height - avatar_size) // 2
    
    # Profile photo (download and use real avatar or placeholder)
    if profile['avatar']:
        try:
            # Download avatar
            avatar_response = requests.get(profile['avatar'], timeout=10)
            avatar_img = Image.open(BytesIO(avatar_response.content))
            # Resize and make circular
            avatar_img = avatar_img.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
            # Create circular mask
            mask = Image.new('L', (avatar_size, avatar_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([0, 0, avatar_size, avatar_size], fill=255)
            # Apply mask and paste
            img.paste(avatar_img, (avatar_x, avatar_y), mask)
        except Exception as e:
            print(f"⚠️  Could not load avatar: {e}")
            # Draw placeholder circle
            draw.ellipse([avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size], 
                         fill=accent_color, outline=text_primary, width=2)
    else:
        # Draw placeholder circle
        draw.ellipse([avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size], 
                     fill=accent_color, outline=text_primary, width=2)
    
    # Display name and handle text next to avatar (Bluesky embed style)
    # Display name (bold)
    draw.text((text_x, text_line1_y), profile['displayName'], font=small_font, fill=text_primary)
    
    # Handle (below display name)
    handle_text = f"@{profile['handle']}"
    draw.text((text_x, text_line2_y), handle_text, font=small_font, fill=text_secondary)
    
    # Bluesky logo on the right (use local or download)
    logo_size = 60  # Logo size
    logo_x = width - header_padding - logo_size
    logo_y = header_y + (total_text_height - logo_size) // 2
    
    # Try to use local logo first, then download if needed
    logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                             "fonts", "bluesky_logo.png")
    
    logo_loaded = False
    
    # Try local file first
    if os.path.exists(logo_path):
        try:
            logo_img = Image.open(logo_path)
            # Resize to fit
            logo_img = logo_img.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            # Paste logo (with transparency if available)
            if logo_img.mode in ('RGBA', 'LA'):
                img.paste(logo_img, (logo_x, logo_y), logo_img)
            else:
                img.paste(logo_img, (logo_x, logo_y))
            logo_loaded = True
        except Exception as e:
            print(f"⚠️  Could not load local logo: {e}")
    
    # If local file didn't work, try downloading
    if not logo_loaded:
        try:
            logo_urls = [
                "https://bsky.app/static/apple-touch-icon.png",
            ]
            
            for logo_url in logo_urls:
                try:
                    logo_response = requests.get(logo_url, timeout=5)
                    if logo_response.status_code == 200:
                        logo_img = Image.open(BytesIO(logo_response.content))
                        logo_img = logo_img.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                        if logo_img.mode in ('RGBA', 'LA'):
                            img.paste(logo_img, (logo_x, logo_y), logo_img)
                        else:
                            img.paste(logo_img, (logo_x, logo_y))
                        logo_loaded = True
                        break
                except:
                    continue
        except Exception as e:
            print(f"⚠️  Could not download logo: {e}")
    
    # Fallback if nothing worked
    if not logo_loaded:
        print(f"⚠️  Using fallback circle logo")
        draw.ellipse(
            [logo_x, logo_y, logo_x + logo_size, logo_y + logo_size],
            fill=accent_color
        )
    
    # Content positioning - center vertically in the card
    content_y = 280
    
    # Main date - "২৩ কার্তিক, ১৪৩২ বঙ্গাব্দ" (Line 1 - centered)
    # Format: [date] [month], [year] বঙ্গাব্দ
    # Using date instead of ordinal for cleaner look
    date_text = f"{bangla_date_info['date']} {bangla_date_info['month']}, {bangla_date_info['year']} বঙ্গাব্দ"
    date_bbox = draw.textbbox((0, 0), date_text, font=date_font)
    date_width = date_bbox[2] - date_bbox[0]
    date_x = (width - date_width) // 2
    draw.text((date_x, content_y), date_text, font=date_font, fill=text_primary)
    
    content_y += 110
    
    # Weekday and Season in one line - "বারঃ শুক্রবার, ঋতুঃ হেমন্ত" (Line 2 - centered)
    weekday_season_text = f"বারঃ {bangla_date_info['weekday']}, ঋতুঃ {bangla_date_info['season']}"
    ws_bbox = draw.textbbox((0, 0), weekday_season_text, font=info_font)
    ws_width = ws_bbox[2] - ws_bbox[0]
    ws_x = (width - ws_width) // 2
    draw.text((ws_x, content_y), weekday_season_text, font=info_font, fill=text_secondary)
    
    # Save image
    img.save(output_path, 'PNG', quality=95)
    print(f"✅ Image saved successfully: {output_path}")
    
    return output_path, date_text



def post_to_bluesky(image_path, date_text):
    """
    Post the image to Bluesky
    """
    # Get credentials from environment
    handle = os.getenv('BLUESKY_HANDLE', os.getenv('BSKY_USERNAME'))
    password = os.getenv('BLUESKY_PASSWORD', os.getenv('BSKY_APP_PASSWORD'))
    
    if not handle or not password:
        print("⚠️  Bluesky credentials not found in environment variables")
        print("Skipping Bluesky post...")
        return False
    
    try:
        # Login to Bluesky
        client = Client()
        client.login(handle, password)
        print("✅ Logged in to Bluesky")
        
        # Read image
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # Upload image
        upload = client.upload_blob(image_data)
        print("✅ Image uploaded")
        
        # Create post text with hashtags
        # Using proper spacing for better readability on Bluesky
        post_text = f"{date_text}\n\n#Bangladesh #Bangla #বাংলাদেশ #বাংলা #বাংলাতারিখ #তারিখ #date #BanglaDate"
        
        # Create post with image
        post = client.send_post(
            text=post_text,
            embed={
                '$type': 'app.bsky.embed.images',
                'images': [{
                    'alt': f'আজকের বাংলা তারিখ: {date_text}',
                    'image': upload.blob
                }]
            }
        )
        
        print(f"✅ Posted to Bluesky: {post.uri}")
        return True
        
    except Exception as e:
        print(f"❌ Error posting to Bluesky: {e}")
        return False


def main():
    """
    Main function
    """
    print("🔄 Generating Bangla date image...")
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"bangla_date_{timestamp}.png")
    
    # Create image
    image_path, date_text = create_bangla_date_image(output_path)

    
    # Check if we should post to Bluesky
    if os.getenv('POST_TO_BLUESKY', 'false').lower() == 'true':
        print("\n🔄 Posting to Bluesky...")
        post_to_bluesky(image_path, date_text)
    else:
        print("\n⚠️  POST_TO_BLUESKY not set to 'true', skipping Bluesky post")
        print(f"📝 To post to Bluesky, set POST_TO_BLUESKY=true in your .env file")
    
    print("\n✨ Done!")


if __name__ == "__main__":
    main()
