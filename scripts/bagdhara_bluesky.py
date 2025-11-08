#!/usr/bin/env python3
"""
Bangla Bagdhara (Idiom) Image Generator and Bluesky Poster
Fetches random idiom from GitHub, creates an image, and posts to Bluesky
"""

import os
import sys
import random
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from atproto import Client
from io import BytesIO

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to load environment variables (for local development)
try:
    from scripts.load_env import load_env
    load_env()
except ImportError:
    print("ℹ️  Running in GitHub Actions or .env not available")
except Exception as e:
    print(f"ℹ️  Could not load .env: {e}")


def fetch_bagdhara_data():
    """Fetch bagdhara JSON from local file or GitHub"""
    # Try local file first
    local_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "files",
        "bangla_bagdhara.json"
    )
    
    if os.path.exists(local_path):
        try:
            print("🔍 Loading bagdhara data from local file...")
            with open(local_path, 'r', encoding='utf-8') as f:
                import json
                data = json.load(f)
            print(f"✅ Loaded {len(data)} bagdhara entries from local file")
            return data
        except Exception as e:
            print(f"⚠️  Error loading local file: {e}")
    
    # Fallback to GitHub (when file is pushed to repo)
    url = "https://raw.githubusercontent.com/abusayed0206/bsky-autopost/main/files/bangla_bagdhara.json"
    
    try:
        print("🔍 Fetching bagdhara data from GitHub...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        print(f"✅ Fetched {len(data)} bagdhara entries from GitHub")
        return data
    except Exception as e:
        print(f"❌ Error fetching bagdhara data: {e}")
        sys.exit(1)


def select_random_bagdhara(data):
    """Select a random bagdhara from the data"""
    bagdhara = random.choice(data)
    print(f"🎲 Selected: {bagdhara['phrase']} - {bagdhara['meaning']}")
    return bagdhara


def get_fallback_font(size):
    """Try to get Hind Siliguri font or use default"""
    fallback_fonts = [
        "HindSiliguri-Regular.ttf",
        "Hind-Siliguri.ttf",
        "NotoSansBengali-Regular.ttf",
        "Arial.ttf",
    ]
    
    for font_name in fallback_fonts:
        try:
            return ImageFont.truetype(font_name, size)
        except:
            continue
    
    return ImageFont.load_default()


def load_font_for_size(font_path, size):
    """Load a specific font at a given size"""
    try:
        return ImageFont.truetype(font_path, size)
    except:
        return get_fallback_font(size)


def download_font():
    """Download Shohid Shafkat Samir font from lipighor.com"""
    font_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")
    os.makedirs(font_dir, exist_ok=True)
    
    font_path = os.path.join(font_dir, "ShohidShafkatSamir-Regular.ttf")
    
    # If font already exists, return it
    if os.path.exists(font_path):
        return font_path
    
    # Download and extract font
    try:
        print("⬇️  Downloading Shohid Shafkat Samir font...")
        font_url = "https://lipighor.com/download/ShohidShafkatSamir.zip"
        
        response = requests.get(font_url, timeout=30)
        response.raise_for_status()
        
        # Save zip file
        zip_path = os.path.join(font_dir, "ShohidShafkatSamir.zip")
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        
        # Extract zip file
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract all files
            zip_ref.extractall(font_dir)
        
        # Find the regular font in Unicode folder (correct path after unzipping)
        unicode_font_path = os.path.join(font_dir, "Unicode", "Li Shohid Shafkat Samir Unicode.ttf")
        
        if os.path.exists(unicode_font_path):
            # Copy to fonts directory
            import shutil
            shutil.copy(unicode_font_path, font_path)
            print(f"✅ Font extracted: {font_path}")
        else:
            print(f"⚠️  Could not find font at: {unicode_font_path}")
            # Try to find any .ttf file in Unicode folder
            import glob
            ttf_files = glob.glob(os.path.join(font_dir, "Unicode", "*.ttf"), recursive=False)
            if ttf_files:
                import shutil
                shutil.copy(ttf_files[0], font_path)
                print(f"✅ Font found and copied: {ttf_files[0]} -> {font_path}")
            else:
                print(f"⚠️  Could not find any .ttf font in Unicode folder")
                return None
        
        # Clean up zip file
        os.remove(zip_path)
        
        return font_path
        
    except Exception as e:
        print(f"⚠️  Could not download font: {e}")
        import traceback
        traceback.print_exc()
        return None


def load_fonts():
    """Load Shohid Shafkat Samir font"""
    # Try to download font from lipighor.com
    font_path = download_font()
    
    if font_path and os.path.exists(font_path):
        try:
            # Line 1: Header - slightly smaller (52px)
            header_font = ImageFont.truetype(font_path, 52)
            # Line 2: Phrase - more bigger (110px)
            phrase_font = ImageFont.truetype(font_path, 110)
            # Line 3: Meaning - slightly bigger (68px)
            meaning_font = ImageFont.truetype(font_path, 68)
            # Profile font - larger (60px)
            profile_font = ImageFont.truetype(font_path, 60)
            print(f"✅ Loaded font: ShohidShafkatSamir-Regular.ttf")
            return header_font, phrase_font, meaning_font, profile_font, font_path
        except Exception as e:
            print(f"⚠️  Error loading downloaded font: {e}")
    
    # Try system fonts
    font_names = [
        "HindSiliguri-Regular.ttf",
        "Hind-Siliguri.ttf",
        "HindSiliguri-Medium.ttf",
        "NotoSansBengali-Regular.ttf"
    ]
    
    for font_name in font_names:
        try:
            header_font = ImageFont.truetype(font_name, 52)
            phrase_font = ImageFont.truetype(font_name, 110)
            meaning_font = ImageFont.truetype(font_name, 68)
            profile_font = ImageFont.truetype(font_name, 60)
            print(f"✅ Loaded system font: {font_name}")
            return header_font, phrase_font, meaning_font, profile_font, None
        except:
            continue
    
    # Fallback
    print("⚠️  Using fallback fonts")
    return (get_fallback_font(52), get_fallback_font(110), get_fallback_font(68), get_fallback_font(60), None)


def get_profile_info():
    """Get profile information from Bluesky API"""
    handle = os.getenv('BLUESKY_HANDLE', os.getenv('BSKY_USERNAME', 'sayed.app'))
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


def create_bagdhara_image(bagdhara, output_path="bagdhara.png"):
    """Create a 1080x1080 image with bagdhara information"""
    # Image dimensions
    width, height = 1080, 1080
    
    # Dark theme colors (matching bangla_date_bluesky.py)
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
    header_font, phrase_font, meaning_font, profile_font, font_path = load_fonts()
    
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
    avatar_size = 128  # Increased from 64 to 128
    text_x = header_padding + avatar_size + 20  # avatar_size + spacing
    text_line1_y = header_y
    text_line2_y = text_line1_y + 70  # Increased spacing for larger font
    
    # Calculate avatar position to center it between the two text lines
    total_text_height = 130  # Approximate height of both lines with larger font
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
    draw.text((text_x, text_line1_y), profile['displayName'], font=profile_font, fill=text_primary)
    
    # Handle (below display name)
    handle_text = f"@{profile['handle']}"
    draw.text((text_x, text_line2_y), handle_text, font=profile_font, fill=text_secondary)
    
    # Bluesky logo on the right (download only, no local dependency)
    logo_size = 128  # Increased from 60 to 128
    logo_x = width - header_padding - logo_size
    logo_y = header_y + (total_text_height - logo_size) // 2
    
    logo_loaded = False
    
    # Download Bluesky logo
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
    
    # Content - 3 lines centered in the middle
    center_x = width // 2
    
    # Line 1: Header "আজকের বাগধারা" (smaller - 52px)
    line1 = "আজকের বাগধারা"
    
    # Line 2: Phrase (more bigger - 110px, but may need to shrink)
    line2 = bagdhara['phrase']
    
    # Line 3: Meaning (slightly bigger - 68px, but may need to shrink)
    line3 = bagdhara['meaning']
    
    # Available width for text (with margins)
    available_width = width - (card_margin * 2) - 80  # Extra padding inside card
    
    # Dynamic font sizing for Line 2 (Phrase)
    phrase_size = 110
    phrase_font_dynamic = phrase_font
    while phrase_size > 30:  # Minimum size
        b2_test = draw.textbbox((0, 0), line2, font=phrase_font_dynamic)
        w2_test = b2_test[2] - b2_test[0]
        if w2_test <= available_width:
            break
        phrase_size -= 5
        if font_path:
            phrase_font_dynamic = load_font_for_size(font_path, phrase_size)
        else:
            phrase_font_dynamic = get_fallback_font(phrase_size)
    
    if phrase_size < 110:
        print(f"ℹ️  Phrase font reduced to {phrase_size}px to fit")
    
    # Dynamic font sizing for Line 3 (Meaning)
    meaning_size = 68
    meaning_font_dynamic = meaning_font
    while meaning_size > 24:  # Minimum size
        b3_test = draw.textbbox((0, 0), line3, font=meaning_font_dynamic)
        w3_test = b3_test[2] - b3_test[0]
        if w3_test <= available_width:
            break
        meaning_size -= 4
        if font_path:
            meaning_font_dynamic = load_font_for_size(font_path, meaning_size)
        else:
            meaning_font_dynamic = get_fallback_font(meaning_size)
    
    if meaning_size < 68:
        print(f"ℹ️  Meaning font reduced to {meaning_size}px to fit")
    
    # Calculate heights for vertical centering
    line_height_header = int(header_font.size * 1.3)
    line_height_phrase = int(phrase_font_dynamic.size * 1.3)
    line_height_meaning = int(meaning_font_dynamic.size * 1.3)
    
    spacing_1 = 50  # Space between line 1 and 2
    spacing_2 = 35  # Space between line 2 and 3
    
    total_height = line_height_header + spacing_1 + line_height_phrase + spacing_2 + line_height_meaning
    
    # Start position (vertically centered)
    block_top = (height - total_height) // 2
    
    # Draw Line 1: Header (in accent color)
    b1 = draw.textbbox((0, 0), line1, font=header_font)
    w1 = b1[2] - b1[0]
    x1 = center_x - w1 // 2
    y1 = block_top
    draw.text((x1, y1), line1, font=header_font, fill=accent_color)
    
    # Draw Line 2: Phrase (in primary text, dynamically sized)
    b2 = draw.textbbox((0, 0), line2, font=phrase_font_dynamic)
    w2 = b2[2] - b2[0]
    x2 = center_x - w2 // 2
    y2 = y1 + line_height_header + spacing_1
    draw.text((x2, y2), line2, font=phrase_font_dynamic, fill=text_primary)
    
    # Draw Line 3: Meaning (in secondary text, dynamically sized)
    b3 = draw.textbbox((0, 0), line3, font=meaning_font_dynamic)
    w3 = b3[2] - b3[0]
    x3 = center_x - w3 // 2
    y3 = y2 + line_height_phrase + spacing_2
    draw.text((x3, y3), line3, font=meaning_font_dynamic, fill=text_secondary)
    
    # Save image
    img.save(output_path, 'PNG', quality=95)
    print(f"✅ Image saved: {output_path}")
    
    return output_path


def post_to_bluesky(image_path, bagdhara):
    """Post the image to Bluesky with rich text facets"""
    # Get credentials
    handle = os.getenv('BLUESKY_HANDLE', os.getenv('BSKY_USERNAME'))
    password = os.getenv('BLUESKY_PASSWORD', os.getenv('BSKY_APP_PASSWORD'))
    
    if not handle or not password:
        print("⚠️  Bluesky credentials not found")
        return False
    
    try:
        # Login
        print("🔐 Logging into Bluesky...")
        client = Client()
        client.login(handle, password)
        print(f"✅ Logged in as @{handle}")
        
        # Read image
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # Upload image
        print("📤 Uploading image...")
        upload = client.upload_blob(image_data)
        print("✅ Image uploaded")
        
        # Create post text
        post_text = f"আজকের বাগধারা: {bagdhara['phrase']}\n\nঅর্থ: {bagdhara['meaning']}\n\n#বাংলা #বাগধারা #BanglaBagdhara #BanglaIdiom #বাংলাভাষা #Bengali"
        
        # Create facets for hashtags
        facets = []
        hashtags = ['#বাংলা', '#বাগধারা', '#BanglaBagdhara', '#BanglaIdiom', '#বাংলাভাষা', '#Bengali']
        
        # Find hashtag section
        hashtag_section = post_text.split('\n\n')[-1]
        hashtag_start_pos = post_text.rfind(hashtag_section)
        
        current_pos = hashtag_start_pos
        for tag in hashtags:
            tag_pos = post_text.find(tag, current_pos)
            if tag_pos != -1:
                byte_start = len(post_text[:tag_pos].encode('utf-8'))
                byte_end = len(post_text[:tag_pos + len(tag)].encode('utf-8'))
                
                facets.append({
                    'index': {
                        'byteStart': byte_start,
                        'byteEnd': byte_end
                    },
                    'features': [{
                        '$type': 'app.bsky.richtext.facet#tag',
                        'tag': tag[1:]  # Remove #
                    }]
                })
                
                current_pos = tag_pos + len(tag)
        
        # Post to Bluesky
        print("📝 Posting to Bluesky...")
        post = client.send_post(
            text=post_text,
            facets=facets if facets else None,
            embed={
                '$type': 'app.bsky.embed.images',
                'images': [{
                    'alt': f'বাংলা বাগধারা: {bagdhara["phrase"]} - {bagdhara["meaning"]}',
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
    """Main function"""
    print("\n🎯 Bangla Bagdhara Image Generator & Bluesky Poster")
    print("="*60)
    
    # Fetch data
    data = fetch_bagdhara_data()
    
    # Select random bagdhara
    bagdhara = select_random_bagdhara(data)
    
    # Create output directory
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"bagdhara_{timestamp}.png")
    
    # Create image
    print("\n🎨 Creating image...")
    create_bagdhara_image(bagdhara, output_path)
    
    # Post to Bluesky
    if os.getenv('POST_TO_BLUESKY', 'false').lower() == 'true':
        print("\n📤 Posting to Bluesky...")
        post_to_bluesky(output_path, bagdhara)
    else:
        print("\n⚠️  POST_TO_BLUESKY not set to 'true', skipping post")
        print("📝 Set POST_TO_BLUESKY=true in .env to enable posting")
    
    print("\n✨ Done!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
