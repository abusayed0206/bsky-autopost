#!/usr/bin/env python3
"""
Fetch NASA APOD (Astronomy Picture of the Day) and post it to Bluesky
"""
import os
import sys
import requests
import warnings
from io import BytesIO

# Suppress atproto library warnings
warnings.filterwarnings('ignore', category=UserWarning, module='pydantic')

from atproto import Client

# Load environment variables from .env file (for local development)
try:
    from dotenv import load_dotenv
    from pathlib import Path
    root_dir = Path(__file__).parent.parent
    env_path = root_dir / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

# Try to import PIL for image compression
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Bluesky image size limit in bytes (976.56KB)
MAX_IMAGE_SIZE = 976 * 1024

def compress_image(image_data, max_size=MAX_IMAGE_SIZE):
    """Reduce image quality to fit within Bluesky's size limit"""
    if not HAS_PIL:
        return image_data
    
    if len(image_data) <= max_size:
        return image_data
    
    try:
        img = Image.open(BytesIO(image_data))
        
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        
        for quality_level in range(100, 19, -5):
            output = BytesIO()
            img.save(output, format='JPEG', quality=quality_level, optimize=True)
            compressed_data = output.getvalue()
            
            if len(compressed_data) <= max_size:
                print(f"✅ Reduced quality to {quality_level}%: {len(image_data)} → {len(compressed_data)} bytes")
                return compressed_data
        
        # If still too large, downscale the resolution
        print(f"⚠️  Image still {len(compressed_data)} bytes at 20% quality, starting resize...")
        scale = 0.9
        while len(compressed_data) > max_size and scale > 0.1:
            new_size = (int(img.width * scale), int(img.height * scale))
            resized_img = img.resize(new_size, getattr(Image, 'Resampling', Image).LANCZOS if hasattr(getattr(Image, 'Resampling', Image), 'LANCZOS') else Image.ANTIALIAS)
            
            output = BytesIO()
            resized_img.save(output, format='JPEG', quality=40, optimize=True)
            compressed_data = output.getvalue()
            
            print(f"   Resized to {new_size[0]}x{new_size[1]}: {len(compressed_data)} bytes")
            scale -= 0.1
            
        print(f"✅ Final compressed size: {len(compressed_data)} bytes")
        return compressed_data
    except Exception as e:
        print(f"⚠️ Error compressing image: {e}")
        return image_data

def fetch_apod_data():
    """Fetch APOD image info from NASA API"""
    api_key = os.environ.get('NASA_API_KEY', 'DEMO_KEY')
    api_url = f"https://api.nasa.gov/planetary/apod?api_key={api_key}&thumbs=true"
    
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        return {
            'title': data.get('title', 'Unknown Title'),
            'explanation': data.get('explanation', ''),
            'url': data.get('hdurl') or data.get('url'),
            'thumbnail_url': data.get('thumbnail_url'),
            'media_type': data.get('media_type', 'image'),
            'copyright': data.get('copyright'),
            'date': data.get('date')
        }
    except Exception as e:
        print(f"Error fetching NASA API: {e}")
        sys.exit(1)

def download_image(url):
    """Download the image from URL"""
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        image_data = response.content
        
        if len(image_data) > MAX_IMAGE_SIZE:
            image_data = compress_image(image_data)
        
        return image_data
    except Exception as e:
        print(f"Error downloading image: {e}")
        sys.exit(1)

def create_caption(data):
    """Create formatted caption data for Bluesky post with 300 char limit"""
    header = f"🌠 Space Image of the Day: {data['title']}\n\n"
    
    copyright_line = f"📷 {data['copyright']}\n" if data['copyright'] else ""
    date_line = f"🗓️ {data['date']}\n\n" if data['date'] else "\n"
    
    hashtags = ['#NASA', '#APOD', '#Space', '#Astronomy', '#Science']
    hashtag_text = ' '.join(hashtags)
    
    # Calculate available space for explanation
    available_space = 300 - len(header) - len(copyright_line) - len(date_line) - len(hashtag_text) - 5
    
    explanation_text = ""
    if available_space > 20: 
        if len(data['explanation']) > available_space:
            explanation_text = f"{data['explanation'][:available_space - 3]}...\n\n"
        else:
            explanation_text = f"{data['explanation']}\n\n"

    return {
        'header': header,
        'copyright': copyright_line,
        'date': date_line,
        'explanation': explanation_text,
        'hashtags': hashtags
    }

def post_to_bluesky(client, image_data, caption_data):
    """Post image to Bluesky using the atproto SDK"""
    try:
        full_text = (
            caption_data['header'] + 
            caption_data['copyright'] + 
            caption_data['date'] + 
            caption_data['explanation']
        )
        
        # Add hashtags and create facets manually
        facets = []
        if caption_data.get('hashtags'):
            hashtag_start = len(full_text)
            hashtag_text = ' '.join(caption_data['hashtags'])
            full_text += hashtag_text
            
            current_pos = hashtag_start
            for tag in caption_data['hashtags']:
                tag_pos = full_text.find(tag, current_pos)
                if tag_pos != -1:
                    byte_start = len(full_text[:tag_pos].encode('utf-8'))
                    byte_end = len(full_text[:tag_pos + len(tag)].encode('utf-8'))
                    
                    facets.append({
                        'index': {
                            'byteStart': byte_start,
                            'byteEnd': byte_end
                        },
                        'features': [{
                            '$type': 'app.bsky.richtext.facet#tag',
                            'tag': tag[1:]  # Remove '#'
                        }]
                    })
                    current_pos = tag_pos + len(tag)
        
        alt_text = f"NASA APOD: {caption_data['header'].replace('🌠 Space Image of the Day: ', '').strip()}"
        
        response = client.send_image(
            text=full_text,
            image=image_data,
            image_alt=alt_text,
            facets=facets if facets else None
        )
        print("✅ Posted to Bluesky successfully!")
        return True
    except Exception as e:
        print(f"❌ Error posting to Bluesky: {e}")
        sys.exit(1)

def main():
    username = os.environ.get('BSKY_USERNAME')
    app_password = os.environ.get('BSKY_APP_PASSWORD')
    
    if not username or not app_password:
        print("❌ Error: BSKY_USERNAME and BSKY_APP_PASSWORD must be set in .env")
        sys.exit(1)
        
    try:
        client = Client()
        client.login(username, app_password)
    except Exception as e:
        print(f"❌ Login error: {e}")
        sys.exit(1)
        
    apod_data = fetch_apod_data()
    
    img_url = apod_data['url'] if apod_data['media_type'] == 'image' else apod_data['thumbnail_url']
    if not img_url:
        print("❌ No valid image or thumbnail found.")
        sys.exit(1)
        
    image_data = download_image(img_url)
    caption_data = create_caption(apod_data)
    
    post_to_bluesky(client, image_data, caption_data)

if __name__ == "__main__":
    main()
