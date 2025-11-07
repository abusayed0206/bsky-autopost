#!/usr/bin/env python3
"""
Fetch Windows Spotlight images and post them to Bluesky
"""
import os
import sys
import random
import requests
import warnings
from datetime import datetime
from io import BytesIO

# Suppress atproto library warnings
warnings.filterwarnings('ignore', category=UserWarning, module='pydantic')

from atproto import Client, client_utils

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

# Try to import PIL for image compression
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("⚠️  Pillow not installed. Image compression disabled.")
    print("   Install with: pip install Pillow")

# Available locales for Spotlight
LOCALES = [
    ('US', 'en-US'), ('JP', 'en-US'), ('AU', 'en-US'), ('GB', 'en-US'), 
    ('DE', 'en-US'), ('NZ', 'en-US'), ('CA', 'en-US'), ('IN', 'en-US'), 
    ('FR', 'en-US'), ('IT', 'en-US'), ('ES', 'en-US'), ('BR', 'en-US')
]

# Bluesky image size limit in bytes (976.56KB)
MAX_IMAGE_SIZE = 976 * 1024  # 976KB in bytes

def compress_image(image_data, max_size=MAX_IMAGE_SIZE, quality=100):
    """Reduce image quality by 5% decrements to fit within Bluesky's size limit - NO RESIZING"""
    if not HAS_PIL:
        return image_data
    
    # If already under size limit, return as-is
    if len(image_data) <= max_size:
        print(f"   ✅ Image size {len(image_data)} bytes is within limit, no compression needed")
        return image_data
    
    try:
        # Open image
        img = Image.open(BytesIO(image_data))
        
        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        
        # Try reducing quality by 5% decrements: 100→95→90→...→30→25→20
        print(f"   ⚠️  Image size {len(image_data)} bytes exceeds limit, reducing quality...")
        for quality_level in range(100, 19, -5):  # 100, 95, 90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40, 35, 30, 25, 20
            output = BytesIO()
            img.save(output, format='JPEG', quality=quality_level, optimize=True)
            compressed_data = output.getvalue()
            
            if len(compressed_data) <= max_size:
                print(f"   ✅ Reduced quality to {quality_level}%: {len(image_data)} → {len(compressed_data)} bytes")
                return compressed_data
        
        # If still too large at 20% quality, return best effort and warn
        print(f"   ❌ Warning: Image still {len(compressed_data)} bytes at 20% quality (limit: {max_size} bytes)")
        return compressed_data
        
    except Exception as e:
        print(f"   ⚠️  Error compressing image: {e}")
        return image_data

def fetch_spotlight_images():
    """Fetch Spotlight images from Microsoft API (returns up to 4 images)"""
    # Select random locale
    country, locale = random.choice(LOCALES)
    print(f"🌍 Using country: {country}, locale: {locale}")
    
    # Use Windows 11 Spotlight API v4 (supports up to 4K resolution)
    # bcnt=4 to get maximum 4 images
    api_url = f"https://fd.api.iris.microsoft.com/v4/api/selection?placement=88000820&bcnt=4&country={country}&locale={locale}&fmt=json"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        images = []
        
        # Parse the response
        if 'batchrsp' in data and 'items' in data['batchrsp']:
            items = data['batchrsp']['items']
            
            for idx, item in enumerate(items[:4]):  # Maximum 4 images
                if 'item' in item:
                    # The 'item' field contains a JSON string, parse it
                    import json
                    item_json = json.loads(item['item'])
                    
                    if 'ad' in item_json:
                        ad_data = item_json['ad']
                        
                        # Get image URL - use the asset URL directly (already at max quality)
                        image_url = ''
                        if 'landscapeImage' in ad_data and 'asset' in ad_data['landscapeImage']:
                            image_url = ad_data['landscapeImage']['asset']
                        elif 'portraitImage' in ad_data and 'asset' in ad_data['portraitImage']:
                            image_url = ad_data['portraitImage']['asset']
                        
                        if image_url:
                            title = ad_data.get('title', 'N/A')
                            copyright_text = ad_data.get('copyright', 'N/A')
                            
                            images.append({
                                'url': image_url,
                                'title': title,
                                'copyright': copyright_text,
                                'index': idx + 1,
                                'country': country,
                                'locale': locale
                            })
            
            if images:
                print(f"✅ Found {len(images)} Spotlight images")
                return images
            else:
                print("❌ Error: No images found in API response")
                sys.exit(1)
        else:
            print("❌ Error: Invalid API response structure")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error fetching Spotlight API: {e}")
        sys.exit(1)

def download_image(image_url):
    """Download the image from URL with validation"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        'Referer': 'https://www.microsoft.com/'
    }
    
    try:
        response = requests.get(image_url, headers=headers, timeout=60, stream=True)
        response.raise_for_status()
        
        content = response.content
        
        # Check size - images should be at least 50KB
        # Note: Microsoft CDN may return Content-Type: text/plain but actual image data
        if len(content) < 50000:
            print(f"   ⚠️  Warning: Image too small ({len(content)} bytes), likely placeholder")
            return None
        
        # Verify it's actually image data by checking magic bytes
        # JPEG starts with FF D8 FF
        # PNG starts with 89 50 4E 47
        if content[:3] == b'\xff\xd8\xff' or content[:4] == b'\x89PNG':
            print(f"   ✅ Downloaded valid image: {len(content)} bytes")
            
            # Compress image if it's too large
            if len(content) > MAX_IMAGE_SIZE:
                print(f"   ⚠️  Image exceeds Bluesky limit, compressing...")
                content = compress_image(content)
            
            return content
        else:
            print(f"   ⚠️  Warning: Response is not valid image data (first bytes: {content[:10].hex()})")
            return None
        
    except Exception as e:
        print(f"   ❌ Error downloading image: {e}")
        return None

def create_caption(images_data):
    """Create formatted caption data for Bluesky post with Telegram-style format"""
    # Build caption components
    header = "🖼️ Windows Spotlight Images\n\n"
    
    # Add titles
    titles = ""
    for img_data in images_data:
        image_info = img_data['info']
        titles += f"📝 {image_info['title']}\n"
    
    hashtags = ['#WindowsSpotlight, ', '#Spotlight, ', '#Wallpaper, ', '#Microsoft, ', '#Photography, ', '@sayed.page']
    
    # Calculate lengths (hashtags with # and spaces: #tag )
    hashtag_text_len = sum(len(tag) + 2 for tag in hashtags)  # +2 for # and space
    
    # Try full caption first
    full_length = len(header) + len(titles) + 1 + hashtag_text_len  # +1 for newline before hashtags
    
    if full_length <= 300:
        return {
            'header': header,
            'titles': titles,
            'hashtags': hashtags
        }
    
    # If too long, drop hashtags
    minimal_length = len(header) + len(titles)
    
    if minimal_length <= 300:
        print(f"ℹ️  Caption too long, dropped hashtags (was {full_length}, now {minimal_length} chars)")
        return {
            'header': header,
            'titles': titles,
        }
    
    # If STILL too long, truncate titles
    print(f"ℹ️  Caption too long, truncating titles")
    max_titles_len = 300 - len(header) - 3
    truncated_titles = titles[:max_titles_len] + "..."
    
    return {
        'header': header,
        'titles': truncated_titles,
    }


def post_to_bluesky(client, images_data):
    """Post images to Bluesky using the atproto SDK with rich text facets"""
    try:
        # Create caption data
        caption_data = create_caption(images_data)
        
        # Use TextBuilder to properly format the caption with hashtags
        text_builder = client_utils.TextBuilder()
        
        # Add the main text
        text_builder.text(caption_data['header'])
        text_builder.text(caption_data['titles'])
        
        # Add hashtags with proper facets if present
        if caption_data.get('hashtags'):
            text_builder.text('\n')
            hashtags = caption_data['hashtags']
            for tag in hashtags:
                text_builder.tag(tag, tag)
                text_builder.text(' ')
        
        # Get the final text and facets
        final_text = text_builder.build_text()
        facets = text_builder.build_facets()
        
        print(f"📝 Caption length: {len(final_text)} characters")
        
        # Prepare image data and alt texts (with copyright details)
        image_contents = []
        image_alts = []
        
        for img_data in images_data:
            image_contents.append(img_data['content'])
            info = img_data['info']
            # Alt text includes full copyright info for each image
            alt_text = f"{info['title']} - {info['copyright']}"
            # Alt text should be concise (max 1000 chars, but keep it reasonable)
            if len(alt_text) > 200:
                alt_text = alt_text[:197] + "..."
            image_alts.append(alt_text)
        
        # Post to Bluesky with multiple images
        print(f"📤 Posting {len(image_contents)} images to Bluesky...")
        
        if len(image_contents) == 1:
            # Use send_image for single image
            response = client.send_image(
                text=final_text,
                image=image_contents[0],
                image_alt=image_alts[0],
                facets=facets
            )
        else:
            # Use send_images for multiple images (up to 4)
            response = client.send_images(
                text=final_text,
                images=image_contents,
                image_alts=image_alts,
                facets=facets
            )
        
        print(f"✅ Successfully posted to Bluesky!")
        print(f"Post URI: {response.uri}")
        return True
        
    except Exception as e:
        print(f"❌ Error posting to Bluesky: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    """Main function"""
    # Get environment variables
    username = os.environ.get('BSKY_USERNAME')
    app_password = os.environ.get('BSKY_APP_PASSWORD')
    
    if not username or not app_password:
        print("❌ Error: BSKY_USERNAME and BSKY_APP_PASSWORD must be set in .env file")
        sys.exit(1)
    
    # Initialize Bluesky client
    print("🔐 Logging into Bluesky...")
    try:
        client = Client()
        client.login(username, app_password)
        print(f"✅ Logged in as @{username}")
    except Exception as e:
        print(f"❌ Error logging into Bluesky: {e}")
        sys.exit(1)
    
    print("🔍 Fetching Windows Spotlight images...")
    spotlight_images = fetch_spotlight_images()
    
    # Download all images
    images_data = []
    for img_info in spotlight_images:
        print(f"⬇️ Downloading image #{img_info['index']}: {img_info['title'][:50]}...")
        content = download_image(img_info['url'])
        if content:
            print(f"✅ Downloaded {len(content)} bytes")
            images_data.append({
                'content': content,
                'info': img_info
            })
    
    if not images_data:
        print("❌ Error: No images were downloaded successfully")
        sys.exit(1)
    
    # Post to Bluesky
    post_to_bluesky(client, images_data)
    
    print("🎉 Done!")

if __name__ == "__main__":
    main()
