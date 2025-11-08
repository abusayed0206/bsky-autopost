#!/usr/bin/env python3
"""
Movie of the Day Image Downloader and Bluesky Poster
Downloads dataset from Kaggle, selects random movie for today, and posts to Bluesky
"""

import os
import sys
import random
import requests
import zipfile
import csv
from datetime import datetime
from atproto import Client
import pycountry
import subprocess
import tempfile
from requests.auth import HTTPBasicAuth
from PIL import Image

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


def country_to_flag(country_name):
    """Convert country name to flag emoji"""
    if not country_name or country_name.strip() == '':
        return ''
    
    try:
        country = pycountry.countries.search_fuzzy(country_name)[0]
        code = country.alpha_2.upper()
        # Regional indicator symbols: 🇦 = U+1F1E6, offset by 127397 from 'A'
        flag = chr(127397 + ord(code[0])) + chr(127397 + ord(code[1]))
        return flag
    except:
        return ''


def language_to_flag(language_name):
    """Convert language name to flag emoji (using primary country)"""
    if not language_name or language_name.strip() == '':
        return ''
    
    # Manual mapping for common languages to their representative flags
    language_map = {
        'English': '🇬🇧',
        'Spanish': '🇪🇸',
        'French': '🇫🇷',
        'German': '🇩🇪',
        'Italian': '🇮🇹',
        'Portuguese': '🇵🇹',
        'Russian': '🇷🇺',
        'Japanese': '🇯🇵',
        'Korean': '🇰🇷',
        'Chinese': '🇨🇳',
        'Mandarin': '🇨🇳',
        'Arabic': '🇸🇦',
        'Hindi': '🇮🇳',
        'Bengali': '🇧🇩',
        'Urdu': '🇵🇰',
        'Turkish': '🇹🇷',
        'Dutch': '🇳🇱',
        'Swedish': '🇸🇪',
        'Norwegian': '🇳🇴',
        'Danish': '🇩🇰',
        'Finnish': '🇫🇮',
        'Polish': '🇵🇱',
        'Czech': '🇨🇿',
        'Greek': '🇬🇷',
        'Hebrew': '🇮🇱',
        'Thai': '🇹🇭',
        'Vietnamese': '🇻🇳',
        'Indonesian': '🇮🇩',
        'Malay': '🇲🇾',
        'Tamil': '🇮🇳',
        'Telugu': '🇮🇳',
        'Marathi': '🇮🇳',
        'Haitian; Haitian Creole': '🇭🇹',
        'Xhosa': '🇿🇦',
    }
    
    # Try exact match first
    if language_name in language_map:
        return language_map[language_name]
    
    # Try fuzzy match
    for lang, flag in language_map.items():
        if lang.lower() in language_name.lower() or language_name.lower() in lang.lower():
            return flag
    
    return ''


def download_and_extract_dataset():
    """Download and extract the Kaggle dataset"""
    dataset_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "dataset_movies"
    )
    
    # If dataset already exists, use it
    if os.path.exists(dataset_dir) and os.path.isdir(dataset_dir):
        # Check if it has month folders
        months = ['january', 'february', 'march', 'april', 'may', 'june',
                  'july', 'august', 'september', 'october', 'november', 'december']
        if any(os.path.exists(os.path.join(dataset_dir, month)) for month in months):
            print(f"✅ Dataset already exists at {dataset_dir}")
            return dataset_dir
    
    # Download dataset
    print("⬇️  Downloading movie dataset from Kaggle...")
    kaggle_dataset = "abusayed0206/movie-of-the-day"

    kaggle_username = os.getenv('KAGGLE_USERNAME') or os.getenv('KAGGLE_USER') or None
    kaggle_key = os.getenv('KAGGLE_KEY') or os.getenv('KAGGLE_API_KEY') or None

    # Helper to run kaggle CLI
    def try_kaggle_cli():
        try:
            # Ensure target dir exists
            os.makedirs(dataset_dir, exist_ok=True)
            cmd = ["kaggle", "datasets", "download", "-d", kaggle_dataset, "-p", dataset_dir, "--unzip"]
            print(f"🔁 Running: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
            return True
        except Exception as e:
            print(f"⚠️  kaggle CLI failed: {e}")
            return False

    # If username/key present, write a temporary kaggle.json to allow kaggle CLI to run
    kaggle_json_path = None
    wrote_kaggle_json = False
    try:
        if kaggle_username and kaggle_key:
            home = os.path.expanduser('~')
            kaggle_dir = os.path.join(home, '.kaggle')
            os.makedirs(kaggle_dir, exist_ok=True)
            kaggle_json_path = os.path.join(kaggle_dir, 'kaggle.json')
            # Only write if it doesn't exist to avoid overwriting user file
            if not os.path.exists(kaggle_json_path):
                with open(kaggle_json_path, 'w', encoding='utf-8') as kf:
                    import json
                    json.dump({'username': kaggle_username, 'key': kaggle_key}, kf)
                try:
                    os.chmod(kaggle_json_path, 0o600)
                except Exception:
                    pass
                wrote_kaggle_json = True

        # Try kaggle CLI first
        if try_kaggle_cli():
            print(f"✅ Dataset downloaded/extracted to: {dataset_dir} (via kaggle CLI)")
            return dataset_dir

        # If CLI not available or failed, try authenticated requests (when creds available)
        if kaggle_username and kaggle_key:
            print("🔐 Trying authenticated HTTP download from Kaggle API...")
            dataset_url = f"https://www.kaggle.com/api/v1/datasets/download/{kaggle_dataset}"
            try:
                response = requests.get(dataset_url, auth=HTTPBasicAuth(kaggle_username, kaggle_key), timeout=60)
                response.raise_for_status()

                zip_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset_movies.zip")
                with open(zip_path, 'wb') as f:
                    f.write(response.content)

                print(f"✅ Downloaded dataset: {len(response.content)} bytes")
                print("📦 Extracting dataset...")
                os.makedirs(dataset_dir, exist_ok=True)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(dataset_dir)
                os.remove(zip_path)
                print(f"✅ Dataset extracted to: {dataset_dir}")
                return dataset_dir
            except Exception as e:
                print(f"⚠️  Authenticated HTTP download failed: {e}")

        # Last resort: unauthenticated HTTP GET (may return HTML or fail)
        print("🔁 Falling back to unauthenticated HTTP download (may fail for private datasets)")
        dataset_url = f"https://www.kaggle.com/api/v1/datasets/download/{kaggle_dataset}"
        try:
            response = requests.get(dataset_url, timeout=60)
            response.raise_for_status()
            zip_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset_movies.zip")
            with open(zip_path, 'wb') as f:
                f.write(response.content)

            print(f"✅ Downloaded dataset: {len(response.content)} bytes")
            print("📦 Extracting dataset...")
            os.makedirs(dataset_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(dataset_dir)
            os.remove(zip_path)
            print(f"✅ Dataset extracted to: {dataset_dir}")
            return dataset_dir
        except Exception as e:
            print(f"❌ Error downloading/extracting dataset: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    finally:
        # Clean up temporary kaggle.json if we wrote it
        try:
            if wrote_kaggle_json and kaggle_json_path and os.path.exists(kaggle_json_path):
                os.remove(kaggle_json_path)
        except Exception:
            pass
    
    try:
        response = requests.get(dataset_url, timeout=60)
        response.raise_for_status()
        
        # Save zip file
        zip_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "dataset_movies.zip"
        )
        
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ Downloaded dataset: {len(response.content)} bytes")
        
        # Extract zip file
        print("📦 Extracting dataset...")
        os.makedirs(dataset_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(dataset_dir)
        
        print(f"✅ Dataset extracted to: {dataset_dir}")
        
        # Clean up zip file
        os.remove(zip_path)
        
        return dataset_dir
        
    except Exception as e:
        print(f"❌ Error downloading/extracting dataset: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def get_todays_movies(dataset_dir):
    """Get list of movies for today's date"""
    now = datetime.now()
    month_name = now.strftime("%B").lower()  # e.g., "november"
    day_num = now.strftime("%d")  # e.g., "09"
    
    csv_path = os.path.join(dataset_dir, month_name, f"{day_num}.csv")
    
    if not os.path.exists(csv_path):
        print(f"❌ CSV file not found: {csv_path}")
        sys.exit(1)
    
    print(f"📂 Reading movies from: {csv_path}")
    
    movies = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            movies.append(row)
    
    print(f"✅ Found {len(movies)} movies for {month_name} {day_num}")
    return movies


def select_movies_by_time(movies):
    """Select 4 movies based on time of day (AM/PM) and popularity"""
    # Filter movies with posters AND tagline (user requested)
    movies_filtered = [m for m in movies
                       if m.get('poster_path') and m['poster_path'].strip()
                       and m.get('tagline') and m['tagline'].strip()]

    if not movies_filtered:
        print("❌ No movies with both poster and tagline found")
        sys.exit(1)
    
    print(f"📊 Found {len(movies_filtered)} movies with poster and tagline")

    # Sort by popularity (descending) and take top 8
    try:
        movies_sorted = sorted(movies_filtered, key=lambda m: float(m.get('popularity', 0)), reverse=True)[:8]
    except:
        # Fallback if popularity parsing fails
        movies_sorted = movies_filtered[:8]
    
    print(f"🏆 Selected top 8 movies by popularity")
    
    # Check time of day (AM = 0-11, PM = 12-23)
    current_hour = datetime.now().hour
    is_am = current_hour < 12
    
    # Select movies based on time
    if is_am:
        selected = movies_sorted[0:4]
        time_label = "AM"
    else:
        selected = movies_sorted[4:8]
        time_label = "PM"
    
    print(f"⏰ Current time: {datetime.now().strftime('%I:%M %p')} ({time_label})")
    print(f"🎬 Selected 4 movies for {time_label}:")
    for i, movie in enumerate(selected, 1):
        title = movie.get('title', 'Unknown')
        year = ''
        rd = movie.get('release_date', '').strip()
        if rd:
            try:
                year = rd.split('-')[0]
            except:
                year = ''
        
        if year:
            print(f"   {i}. {title} ({year})")
        else:
            print(f"   {i}. {title}")
    
    return selected


def compress_image_to_limit(image_path, max_size_kb=976):
    """Compress image progressively until it's under the size limit"""
    max_size_bytes = max_size_kb * 1024
    
    # Check current size
    current_size = os.path.getsize(image_path)
    
    if current_size <= max_size_bytes:
        print(f"✅ Image size OK: {current_size / 1024:.2f}KB (limit: {max_size_kb}KB)")
        return image_path
    
    print(f"⚠️  Image too large: {current_size / 1024:.2f}KB (limit: {max_size_kb}KB)")
    print("🔄 Compressing image...")
    
    # Open image
    img = Image.open(image_path)
    
    # Convert RGBA to RGB if needed
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
        img = background
    
    # Try different quality levels (start at 95%, reduce by 5% each time)
    quality = 95
    while quality >= 20:
        # Save with reduced quality
        img.save(image_path, 'JPEG', quality=quality, optimize=True)
        new_size = os.path.getsize(image_path)
        
        print(f"   Quality {quality}%: {new_size / 1024:.2f}KB")
        
        if new_size <= max_size_bytes:
            print(f"✅ Compressed successfully to {new_size / 1024:.2f}KB at {quality}% quality")
            return image_path
        
        quality -= 5
    
    # If still too large, resize the image
    print("⚠️  Still too large after quality reduction, resizing...")
    img = Image.open(image_path)
    
    # Reduce dimensions by 10% each iteration
    scale_factor = 0.9
    while True:
        new_width = int(img.width * scale_factor)
        new_height = int(img.height * scale_factor)
        
        if new_width < 100 or new_height < 100:
            print("❌ Could not compress image enough")
            return None
        
        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        resized.save(image_path, 'JPEG', quality=85, optimize=True)
        new_size = os.path.getsize(image_path)
        
        print(f"   Resized to {new_width}x{new_height}: {new_size / 1024:.2f}KB")
        
        if new_size <= max_size_bytes:
            print(f"✅ Compressed successfully to {new_size / 1024:.2f}KB")
            return image_path


def download_poster(poster_path, output_path="movie_poster.jpg"):
    """Download poster image from TMDB"""
    if not poster_path or poster_path.strip() == '':
        print("⚠️  No poster path available")
        return None
    
    # TMDB image base URL (original size)
    base_url = "https://image.tmdb.org/t/p/original"
    image_url = base_url + poster_path
    
    try:
        print(f"⬇️  Downloading poster from: {image_url}")
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ Poster downloaded: {output_path} ({len(response.content)} bytes)")
        
        # Compress if needed
        compressed_path = compress_image_to_limit(output_path, max_size_kb=976)
        
        return compressed_path
        
    except Exception as e:
        print(f"❌ Error downloading poster: {e}")
        return None


def download_multiple_posters(movies, output_dir):
    """Download and compress posters for multiple movies"""
    poster_paths = []
    
    for i, movie in enumerate(movies, 1):
        title = movie.get('title', 'Unknown').replace('/', '_').replace('\\', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"poster_{i}_{timestamp}_{title[:30]}.jpg")
        
        poster_path = download_poster(movie.get('poster_path'), output_path)
        
        if poster_path:
            poster_paths.append(poster_path)
        else:
            print(f"⚠️  Failed to download poster for {title}")
    
    return poster_paths


def create_post_text(movies, max_length=300):
    """Create post text with multiple movie details"""
    if not movies:
        return "", []
    
    # Build main caption
    lines = ["Movies of the day (4/8)"]
    
    # Add each movie with title and year
    for movie in movies:
        title = movie.get('title', 'Unknown')
        year = ''
        rd = movie.get('release_date', '').strip()
        if rd:
            try:
                year = rd.split('-')[0]
            except:
                year = ''
        
        if year:
            lines.append(f"🎬 {title}({year})")
        else:
            lines.append(f"🎬 {title}")
    
    # Attribution (no URL as requested)
    lines.append("\n© TMDB")
    
    base_text = '\n'.join(lines)
    
    # Build hashtags: movie titles (no spaces) + unique genres + #Movie + generic tags
    hashtag_parts = []
    
    # Add movie title hashtags (remove spaces)
    for movie in movies:
        title = movie.get('title', '').strip()
        if title:
            # Remove spaces, special chars, keep alphanumeric
            tag = '#' + ''.join(c for c in title if c.isalnum())
            hashtag_parts.append(tag)
    
    # Collect unique genres from all 4 movies
    all_genres = set()
    for movie in movies:
        genres = movie.get('genres', '').strip()
        if genres:
            genre_list = [g.strip() for g in genres.split(',') if g.strip()]
            for g in genre_list:
                all_genres.add(g)
    
    # Add genre hashtags
    for genre in sorted(all_genres):
        tag = '#' + genre.replace(' ', '').replace('-', '')
        hashtag_parts.append(tag)
    
    # Add generic tags
    hashtag_parts.extend(['#Movie', '#MovieOfTheDay', '#OnThisDay', '#TMDB'])
    
    # Ensure unique hashtags (case-insensitive)
    seen = set()
    hashtags_ordered = []
    for h in hashtag_parts:
        if h.lower() not in seen:
            hashtags_ordered.append(h)
            seen.add(h.lower())
    
    hashtag_line = ' '.join(hashtags_ordered)
    full_text = base_text + '\n\n' + hashtag_line
    
    # Ensure byte length <= max_length (default 300)
    def byte_len(s):
        return len(s.encode('utf-8'))
    
    if byte_len(full_text) > max_length:
        # Trim hashtags progressively
        for keep in range(len(hashtags_ordered), 0, -1):
            trial = base_text + '\n\n' + ' '.join(hashtags_ordered[:keep])
            if byte_len(trial) <= max_length:
                full_text = trial
                hashtags_ordered = hashtags_ordered[:keep]
                break
    
    # Final fallback: just base text if still too long
    if byte_len(full_text) > max_length:
        full_text = base_text[:max_length]
    
    return full_text, hashtags_ordered


def post_to_bluesky(poster_paths, movies):
    """Post multiple movie posters to Bluesky with rich text facets"""
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
        
        # Upload all images
        print(f"📤 Uploading {len(poster_paths)} posters...")
        images = []
        
        for i, (poster_path, movie) in enumerate(zip(poster_paths, movies), 1):
            # Read image
            with open(poster_path, 'rb') as f:
                image_data = f.read()
            
            # Upload image
            print(f"   Uploading poster {i}/{len(poster_paths)}...")
            upload = client.upload_blob(image_data)
            
            # Create alt text with movie title
            title = movie.get('title', 'Unknown')
            alt_text = f"Movie poster for {title}"
            
            images.append({
                'alt': alt_text[:1000],  # Alt text limit
                'image': upload.blob
            })
        
        print("✅ All posters uploaded")
        
        # Create post text
        post_text, hashtag_list = create_post_text(movies)
        
        print("\n" + "="*60)
        print("📝 POST PREVIEW:")
        print("="*60)
        print(post_text)
        print("="*60)
        print(f"Character count: {len(post_text.encode('utf-8'))} bytes")
        print(f"Images: {len(images)}\n")
        
        # Create facets for hashtags
        facets = []
        
        for tag in hashtag_list:
            tag_pos = post_text.find(tag)
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
        
        # Post to Bluesky with multiple images
        print("📝 Posting to Bluesky...")
        
        post = client.send_post(
            text=post_text,
            facets=facets if facets else None,
            embed={
                '$type': 'app.bsky.embed.images',
                'images': images
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
    print("\n🎬 Movies of the Day - Bluesky Poster")
    print("="*60)
    
    # Download and extract dataset
    dataset_dir = download_and_extract_dataset()
    
    # Get today's movies
    movies = get_todays_movies(dataset_dir)
    
    # Select 4 movies based on time (AM/PM) and popularity
    selected_movies = select_movies_by_time(movies)
    
    if len(selected_movies) < 4:
        print(f"⚠️  Only {len(selected_movies)} movies available, need 4")
        if len(selected_movies) == 0:
            print("❌ No movies to post")
            sys.exit(1)
    
    # Create output directory
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Download all posters
    print(f"\n🖼️  Downloading {len(selected_movies)} posters...")
    poster_paths = download_multiple_posters(selected_movies, output_dir)
    
    if len(poster_paths) == 0:
        print("❌ Could not download any posters, exiting")
        sys.exit(1)
    
    if len(poster_paths) < len(selected_movies):
        print(f"⚠️  Only downloaded {len(poster_paths)}/{len(selected_movies)} posters")
    
    # Adjust selected_movies to match downloaded posters
    selected_movies = selected_movies[:len(poster_paths)]
    
    # Post to Bluesky
    if os.getenv('POST_TO_BLUESKY', 'false').lower() == 'true':
        print("\n📤 Posting to Bluesky...")
        post_to_bluesky(poster_paths, selected_movies)
    else:
        print("\n⚠️  POST_TO_BLUESKY not set to 'true', skipping post")
        print("📝 Set POST_TO_BLUESKY=true in .env to enable posting")
        # Still show preview
        post_text, _ = create_post_text(selected_movies)
        print("\n" + "="*60)
        print("📝 POST PREVIEW:")
        print("="*60)
        print(post_text)
        print("="*60)
        print(f"Character count: {len(post_text.encode('utf-8'))} bytes")
        print(f"Images: {len(poster_paths)}\n")
    
    print("\n✨ Done!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
