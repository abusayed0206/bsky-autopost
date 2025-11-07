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
        date_font = ImageFont.truetype(font_path, 110)  # Increased from 80 to 110
        info_font = ImageFont.truetype(font_path, 68)  # Increased from 52 to 68
        small_font = ImageFont.truetype(font_path, 36)
        return title_font, date_font, info_font, small_font
    except Exception as e:
        print(f"Warning: Could not load primary font: {e}")
        print("Falling back to system fonts...")
        return (get_fallback_font(72), get_fallback_font(110), 
                get_fallback_font(68), get_fallback_font(36))


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
    # Image dimensions - 1080x1080 square
    width, height = 1080, 1080
    
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
    
    # Content positioning - center block in the middle
    # We'll render 3 lines:
    # 1) "২৩ কার্তিক," (date + month, with comma)
    # 2) "১৪৩২ বঙ্গাব্দ" (year + বঙ্গাব্দ)
    # 3) "বারঃ রবিবার, ঋতুঃ হেমন্ত" with weekday and season highlighted
    center_x = width // 2
    # Calculate total height needed for the 3 lines with spacing
    line_height_date = int(date_font.size * 1.2)
    line_height_info = int(info_font.size * 1.2)
    extra_spacing = 30  # Extra space between line 2 and 3
    total_height = line_height_date + line_height_date + extra_spacing + line_height_info
    # Center the block vertically
    block_top = (height - total_height) // 2

    # Line 1: date + month with trailing comma
    line1 = f"{bangla_date_info['date']} {bangla_date_info['month']},"
    b1 = draw.textbbox((0, 0), line1, font=date_font)
    w1 = b1[2] - b1[0]
    x1 = center_x - w1 // 2
    y1 = block_top
    draw.text((x1, y1), line1, font=date_font, fill=text_primary)

    # Line 2: year + বঙ্গাব্দ
    line2 = f"{bangla_date_info['year']} বঙ্গাব্দ"
    b2 = draw.textbbox((0, 0), line2, font=date_font)
    w2 = b2[2] - b2[0]
    x2 = center_x - w2 // 2
    y2 = y1 + line_height_date
    draw.text((x2, y2), line2, font=date_font, fill=text_primary)

    # Line 3: combined weekday and season with highlights (with extra spacing)
    prefix1 = "বারঃ "
    weekday = bangla_date_info['weekday']
    comma = ", "
    prefix2 = "ঋতুঃ "
    season = bangla_date_info['season']

    # Measure segments
    p1_box = draw.textbbox((0, 0), prefix1, font=info_font)
    p1_w = p1_box[2] - p1_box[0]
    wd_box = draw.textbbox((0, 0), weekday, font=info_font)
    wd_w = wd_box[2] - wd_box[0]
    comma_box = draw.textbbox((0, 0), comma, font=info_font)
    comma_w = comma_box[2] - comma_box[0]
    p2_box = draw.textbbox((0, 0), prefix2, font=info_font)
    p2_w = p2_box[2] - p2_box[0]
    season_box = draw.textbbox((0, 0), season, font=info_font)
    season_w = season_box[2] - season_box[0]

    total_w = p1_w + wd_w + comma_w + p2_w + season_w
    x_start = center_x - total_w // 2
    y3 = y2 + line_height_date + extra_spacing

    # Draw prefix1
    draw.text((x_start, y3), prefix1, font=info_font, fill=text_secondary)
    x_cursor = x_start + p1_w

    # Draw weekday (highlight)
    draw.text((x_cursor, y3), weekday, font=info_font, fill=accent_color)
    x_cursor += wd_w

    # Draw comma
    draw.text((x_cursor, y3), comma, font=info_font, fill=text_secondary)
    x_cursor += comma_w

    # Draw prefix2
    draw.text((x_cursor, y3), prefix2, font=info_font, fill=text_secondary)
    x_cursor += p2_w

    # Draw season (highlight)
    draw.text((x_cursor, y3), season, font=info_font, fill=accent_color)

    
    # Save image
    img.save(output_path, 'PNG', quality=95)
    print(f"✅ Image saved successfully: {output_path}")
    
    # Compose date_text for caption (multi-line)
    caption_date_lines = f"{line1}\n{line2}\n{prefix1}{weekday}, {prefix2}{season}"
    return output_path, caption_date_lines, bangla_date_info



def post_to_bluesky(image_path, date_text, bangla_date_info):
    """
    Post the image to Bluesky with rich text facets for hashtags
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
        
        # Create post text with new format
        # Format:
        # আজ রোজ শুক্রবার,
        # ২৩ কার্তিক, ১৪৩২ বঙ্গাব্দ
        # এবং হেমন্তকাল
        # 
        # [hashtags]
        
        post_text = f"আজ রোজ {bangla_date_info['weekday']},\n{date_text}\nএবং {bangla_date_info['season']}কাল\n\n#Bangladesh #Bangla #বাংলাদেশ #বাংলা #বাংলাতারিখ #তারিখ #date #BanglaDate"
        
        # Calculate byte positions for hashtags (rich text facets)
        # We need to use UTF-8 byte offsets
        post_text_bytes = post_text.encode('utf-8')
        
        # Find the start of hashtags section (after the double newline)
        hashtag_section_start = post_text.find('\n\n#')
        if hashtag_section_start != -1:
            hashtag_section_start += 2  # Skip the \n\n
        
        # Create facets for each hashtag
        facets = []
        hashtags = ['#Bangladesh', '#Bangla', '#বাংলাদেশ', '#বাংলা', '#বাংলাতারিখ', '#তারিখ', '#Date', '#BanglaDate']
        
        current_pos = hashtag_section_start
        for hashtag in hashtags:
            # Find the hashtag in the text starting from current position
            hashtag_pos = post_text.find(hashtag, current_pos)
            if hashtag_pos != -1:
                # Calculate UTF-8 byte offsets
                byte_start = len(post_text[:hashtag_pos].encode('utf-8'))
                byte_end = len(post_text[:hashtag_pos + len(hashtag)].encode('utf-8'))
                
                # Create facet for this hashtag
                facets.append({
                    'index': {
                        'byteStart': byte_start,
                        'byteEnd': byte_end
                    },
                    'features': [{
                        '$type': 'app.bsky.richtext.facet#tag',
                        'tag': hashtag[1:]  # Remove the # symbol
                    }]
                })
                
                current_pos = hashtag_pos + len(hashtag)
        
        # Create post with image and facets
        post = client.send_post(
            text=post_text,
            facets=facets if facets else None,
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
        import traceback
        traceback.print_exc()
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
    image_path, date_text, bangla_date_info = create_bangla_date_image(output_path)

    
    # Check if we should post to Bluesky
    if os.getenv('POST_TO_BLUESKY', 'false').lower() == 'true':
        print("\n🔄 Posting to Bluesky...")
        post_to_bluesky(image_path, date_text, bangla_date_info)
    else:
        print("\n⚠️  POST_TO_BLUESKY not set to 'true', skipping Bluesky post")
        print(f"📝 To post to Bluesky, set POST_TO_BLUESKY=true in your .env file")
    
    print("\n✨ Done!")


if __name__ == "__main__":
    main()
