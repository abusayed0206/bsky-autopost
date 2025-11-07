#!/usr/bin/env python3
"""
Fetch Bing wallpaper and post it to Bluesky
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

# Available regions for Bing wallpaper
REGIONS = [
    'en-US', 'ja-JP', 'en-AU', 'en-GB', 'de-DE', 
    'en-NZ', 'en-CA', 'en-IN', 'fr-FR', 'fr-CA', 
    'it-IT', 'es-ES', 'pt-BR', 'en-ROW'
]

# Bluesky image size limit in bytes (976.56KB)
MAX_IMAGE_SIZE = 976 * 1024  # 976KB in bytes

def compress_image(image_data, max_size=MAX_IMAGE_SIZE, quality=100):
    """Reduce image quality by 5% decrements to fit within Bluesky's size limit - NO RESIZING"""
    if not HAS_PIL:
        return image_data
    
    # If already under size limit, return as-is
    if len(image_data) <= max_size:
        print(f"✅ Image size {len(image_data)} bytes is within limit, no compression needed")
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
        print(f"⚠️  Image size {len(image_data)} bytes exceeds limit, reducing quality...")
        for quality_level in range(100, 19, -5):  # 100, 95, 90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40, 35, 30, 25, 20
            output = BytesIO()
            img.save(output, format='JPEG', quality=quality_level, optimize=True)
            compressed_data = output.getvalue()
            
            print(f"   Testing quality {quality_level}%: {len(compressed_data)} bytes")
            
            if len(compressed_data) <= max_size:
                print(f"✅ Reduced quality to {quality_level}%: {len(image_data)} → {len(compressed_data)} bytes")
                return compressed_data
        
        # If still too large at 20% quality, return best effort and warn
        print(f"❌ Warning: Image still {len(compressed_data)} bytes at 20% quality (limit: {max_size} bytes)")
        print(f"   This image is too large even at minimum quality. Upload may fail.")
        return compressed_data
        
    except Exception as e:
        print(f"⚠️  Error compressing image: {e}")
        return image_data

def fetch_bing_image():
    """Fetch image info from Bing API with random region and 1080p quality"""
    # Select random region
    region = random.choice(REGIONS)
    print(f"🌍 Using region: {region}")
    
    # Use official Bing API with 1080p quality (will compress later if needed)
    api_url = f"https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt={region}&uhd=1&uhdwidth=1920&uhdheight=1080"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Parse the response
        if 'images' in data and len(data['images']) > 0:
            image_data = data['images'][0]
            
            # Construct full URL
            base_url = "https://www.bing.com"
            image_url = image_data['url']
            
            # Remove any existing parameters after & to get clean URL
            if '&' in image_url:
                image_url = image_url.split('&')[0]
            
            full_url = f"{base_url}{image_url}"
            
            return {
                'url': full_url,
                'copyright': image_data.get('copyright', 'N/A'),
                'copyright_link': image_data.get('copyrightlink', ''),
                'start_date': image_data.get('startdate', ''),
                'end_date': image_data.get('enddate', ''),
                'region': region
            }
        else:
            print("❌ Error: No images found in API response")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error fetching Bing API: {e}")
        sys.exit(1)

def download_image(image_url):
    """Download the image from URL"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(image_url, headers=headers, timeout=60)
        response.raise_for_status()
        image_data = response.content
        
        print(f"✅ Downloaded image: {len(image_data)} bytes")
        
        # Compress image if it's too large (only quality reduction, no resize)
        if len(image_data) > MAX_IMAGE_SIZE:
            image_data = compress_image(image_data)
        
        return image_data
    except Exception as e:
        print(f"Error downloading image: {e}")
        sys.exit(1)

def create_caption(data):
    """Create formatted caption data for Bluesky post with smart 300 char limit"""
    copyright_text = data.get('copyright', 'N/A')
    region = data.get('region', 'N/A')
    
    # Build caption components
    header = "🖼️ Bing Wallpaper of the Day\n\n"
    copyright_line = f"📷 {copyright_text}\n\n"
    region_line = f"🌍 Region: {region}\n"
    hashtags = ['#BingWallpaper', '#DailyWallpaper', '#Photography', '#NaturePhotography', '#Wallpaper']
    
    # Calculate lengths (hashtags with # and spaces: #tag )
    hashtag_text_len = sum(len(tag) + 2 for tag in hashtags)  # +2 for # and space
    
    # Try full caption first
    full_length = len(header) + len(copyright_line) + len(region_line) + hashtag_text_len
    
    if full_length <= 300:
        return {
            'header': header,
            'copyright': copyright_line,
            'region': region_line,
            'hashtags': hashtags
        }
    
    # If too long, drop region
    without_region_length = len(header) + len(copyright_line) + hashtag_text_len
    
    if without_region_length <= 300:
        print(f"ℹ️  Caption too long, dropped region (was {full_length}, now {without_region_length} chars)")
        return {
            'header': header,
            'copyright': copyright_line,
            'hashtags': hashtags
        }
    
    # If still too long, drop hashtags
    minimal_length = len(header) + len(copyright_line.rstrip('\n\n'))
    
    if minimal_length <= 300:
        print(f"ℹ️  Caption too long, dropped region and hashtags (was {full_length}, now {minimal_length} chars)")
        return {
            'header': header,
            'copyright': copyright_line.rstrip('\n\n'),
        }
    
    # If STILL too long, truncate copyright
    max_copyright_len = 300 - len(header) - 5  # 5 for "📷 " and some buffer
    truncated_copyright = copyright_text[:max_copyright_len] + "..."
    
    print(f"ℹ️  Caption too long, truncated copyright (was {full_length} chars)")
    return {
        'header': header,
        'copyright': f"📷 {truncated_copyright}",
    }

def post_to_bluesky(client, image_data, caption_data):
    """Post image to Bluesky using the atproto SDK with rich text facets"""
    try:
        # Use TextBuilder to properly format the caption with hashtags
        text_builder = client_utils.TextBuilder()
        
        # Add the main text
        text_builder.text(caption_data['header'])
        text_builder.text(caption_data['copyright'])
        
        # Add region if present
        if caption_data.get('region'):
            text_builder.text(caption_data['region'])
        
        # Add hashtags with proper facets if present
        if caption_data.get('hashtags'):
            hashtags = caption_data['hashtags']
            for tag in hashtags:
                text_builder.tag(tag, tag)
                text_builder.text(' ')
        
        # Get the final text and facets
        final_text = text_builder.build_text()
        facets = text_builder.build_facets()
        
        print(f"📝 Caption: {final_text}")
        print(f"📝 Caption length: {len(final_text)} characters")
        
        # Prepare alt text (copyright text)
        alt_text = caption_data['copyright'].replace('📷 ', '').strip()
        if len(alt_text) > 100:
            alt_text = alt_text[:97] + "..."
        
        # Post to Bluesky with rich text
        print("📤 Posting to Bluesky...")
        response = client.send_image(
            text=final_text,
            image=image_data,
            image_alt=alt_text,
            facets=facets
        )
        
        print("✅ Image successfully posted to Bluesky!")
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
    
    print("🔍 Fetching Bing wallpaper info...")
    bing_data = fetch_bing_image()
    
    print(f"📥 Found image: {bing_data.get('url')}")
    print(f"📅 Date: {bing_data.get('start_date')} - {bing_data.get('end_date')}")
    
    print("⬇️ Downloading image...")
    image_data = download_image(bing_data['url'])
    
    print("📝 Creating caption...")
    caption_data = create_caption(bing_data)
    
    # Post to Bluesky
    post_to_bluesky(client, image_data, caption_data)
    
    print("🎉 Done!")

if __name__ == "__main__":
    main()
