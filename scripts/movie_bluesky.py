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


def select_random_movie(movies):
    """Select a random movie from the list (with backdrop)"""
    # Filter movies with backdrops and with a non-empty tagline (user requested)
    movies_filtered = [m for m in movies
                       if m.get('backdrop_path') and m['backdrop_path'].strip()
                       and m.get('tagline') and m['tagline'].strip()]

    if not movies_filtered:
        print("❌ No movies with both backdrop and tagline found")
        sys.exit(1)

    movie = random.choice(movies_filtered)
    title = movie.get('title', 'Unknown')
    year = ''
    # Try to extract year from release_date if present
    rd = movie.get('release_date') or movie.get('release_date_local') or ''
    if rd:
        try:
            year = rd.split('-')[0]
        except:
            year = ''

    if year:
        print(f"🎲 Selected: {title} ({year}) (from {len(movies_filtered)} candidates)")
    else:
        print(f"🎲 Selected: {title} (from {len(movies_filtered)} candidates)")

    return movie


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


def download_backdrop(backdrop_path, output_path="movie_backdrop.jpg"):
    """Download backdrop image from TMDB"""
    if not backdrop_path or backdrop_path.strip() == '':
        print("⚠️  No backdrop path available")
        return None
    
    # TMDB image base URL (original size)
    base_url = "https://image.tmdb.org/t/p/original"
    image_url = base_url + backdrop_path
    
    try:
        print(f"⬇️  Downloading backdrop from: {image_url}")
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ Backdrop downloaded: {output_path} ({len(response.content)} bytes)")
        
        # Compress if needed
        compressed_path = compress_image_to_limit(output_path, max_size_kb=976)
        
        return compressed_path
        
    except Exception as e:
        print(f"❌ Error downloading backdrop: {e}")
        return None


def create_post_text(movie, max_length=300):
    """Create post text with movie details"""
    title = movie.get('title', 'Unknown')
    tagline = movie.get('tagline', '').strip()
    genres = movie.get('genres', '').strip()
    countries = movie.get('production_countries', '').strip()
    languages = movie.get('spoken_languages', '').strip()
    movie_id = movie.get('id', '').strip()

    # Title with year if available
    year = ''
    rd = movie.get('release_date', '').strip()
    if rd:
        try:
            year = rd.split('-')[0]
        except:
            year = ''

    title_line = f"🎬 Movie of the Day: {title}"
    if year:
        title_line = f"{title_line}({year})"

    # Country and language names (take first entries)
    country_list = [c.strip() for c in countries.split(',')] if countries else []
    language_list = [l.strip() for l in languages.split(',')] if languages else []

    country_display = country_list[0] if country_list else ''
    language_display = language_list[0] if language_list else ''

    # Get flags for inline display
    country_flag = country_to_flag(country_display) if country_display else ''
    language_flag = language_to_flag(language_display) if language_display else ''

    # Build lines per requested style
    lines = [title_line]
    lines.append(f"Tagline: {tagline}")
    
    # Country and Language with inline flags
    country_text = f"{country_display}{country_flag}" if country_display else 'N/A'
    language_text = f"{language_display}{language_flag}" if language_display else 'N/A'
    lines.append(f"Country: {country_text}, Language: {language_text}")

    # Attribution line with TMDB URL
    if movie_id:
        lines.append(f'\n© TMDB(https://www.themoviedb.org/movie/{movie_id})')
    else:
        lines.append('\n© TMDB')

    base_text = '\n'.join(lines)

    # Build hashtags: genres (max 2), country, language, #onthisday and some extras
    hashtag_parts = []
    if genres:
        genre_list = [g.strip() for g in genres.split(',') if g.strip()]
        for g in genre_list[:2]:
            tag = '#' + g.replace(' ', '').replace('-', '')
            hashtag_parts.append(tag)

    if country_display:
        hashtag_parts.append('#' + country_display.replace(' ', '').replace('-', ''))

    if language_display:
        hashtag_parts.append('#' + language_display.replace(' ', '').replace('-', ''))

    # Add required and helpful tags
    hashtag_parts.extend(['#OnThisDay', '#MovieOfTheDay', '#TMDB'])

    # Ensure unique and reasonable order
    seen = set()
    hashtags_ordered = []
    for h in hashtag_parts:
        if h.lower() not in seen:
            hashtags_ordered.append(h)
            seen.add(h.lower())

    hashtag_line = ' '.join(hashtags_ordered)

    full_text = base_text + '\n\n' + hashtag_line

    # Ensure byte length <= max_length (default 300). Trim hashtags then tagline if needed.
    def byte_len(s):
        return len(s.encode('utf-8'))

    if byte_len(full_text) > max_length:
        # First trim hashtags progressively
        for keep in range(len(hashtags_ordered), 0, -1):
            trial = base_text + '\n\n' + ' '.join(hashtags_ordered[:keep])
            if byte_len(trial) <= max_length:
                full_text = trial
                hashtags_ordered = hashtags_ordered[:keep]
                break

    if byte_len(full_text) > max_length:
        # Remove tagline line (user ok with that fallback previously)
        country_text = f"{country_display}{country_flag}" if country_display else 'N/A'
        language_text = f"{language_display}{language_flag}" if language_display else 'N/A'
        lines_no_tag = [title_line, f"Country: {country_text}, Language: {language_text}"]
        if movie_id:
            lines_no_tag.append(f'\n© TMDB(https://www.themoviedb.org/movie/{movie_id})')
        else:
            lines_no_tag.append('\n© TMDB')
        base_no_tag = '\n'.join(lines_no_tag)
        for keep in range(len(hashtags_ordered), 0, -1):
            trial = base_no_tag + '\n\n' + ' '.join(hashtags_ordered[:keep])
            if byte_len(trial) <= max_length:
                full_text = trial
                hashtags_ordered = hashtags_ordered[:keep]
                break

    # Final fallback: truncate hashtags string to fit (rare)
    if byte_len(full_text) > max_length:
        allowed = max_length - byte_len(base_text) - 2
        if allowed > 0:
            truncated = (' '.join(hashtags_ordered)).encode('utf-8')[:allowed].decode('utf-8', errors='ignore')
            full_text = base_text + '\n\n' + truncated
        else:
            full_text = base_text[:max_length]

    return full_text, hashtags_ordered


def post_to_bluesky(image_path, movie):
    """Post the movie backdrop to Bluesky with rich text facets"""
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
        print("📤 Uploading backdrop...")
        upload = client.upload_blob(image_data)
        print("✅ Backdrop uploaded")
        
        # Create post text
        post_text, hashtag_list = create_post_text(movie)
        
        print("\n" + "="*60)
        print("📝 POST PREVIEW:")
        print("="*60)
        print(post_text)
        print("="*60)
        print(f"Character count: {len(post_text.encode('utf-8'))} bytes\n")
        
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
        
        # Post to Bluesky
        print("📝 Posting to Bluesky...")
        alt_text = f"Movie backdrop for {movie['title']}"
        if movie.get('tagline'):
            alt_text += f" - {movie['tagline']}"
        
        post = client.send_post(
            text=post_text,
            facets=facets if facets else None,
            embed={
                '$type': 'app.bsky.embed.images',
                'images': [{
                    'alt': alt_text[:1000],  # Alt text limit
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
    print("\n🎬 Movie of the Day - Bluesky Poster")
    print("="*60)
    
    # Download and extract dataset
    dataset_dir = download_and_extract_dataset()
    
    # Get today's movies
    movies = get_todays_movies(dataset_dir)
    
    # Select random movie
    movie = select_random_movie(movies)
    
    # Create output directory
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"movie_{timestamp}.jpg")
    
    # Download backdrop
    print("\n🖼️  Downloading backdrop...")
    backdrop_path = download_backdrop(movie['backdrop_path'], output_path)
    
    if not backdrop_path:
        print("❌ Could not download backdrop, exiting")
        sys.exit(1)
    
    # Post to Bluesky
    if os.getenv('POST_TO_BLUESKY', 'false').lower() == 'true':
        print("\n📤 Posting to Bluesky...")
        post_to_bluesky(backdrop_path, movie)
    else:
        print("\n⚠️  POST_TO_BLUESKY not set to 'true', skipping post")
        print("📝 Set POST_TO_BLUESKY=true in .env to enable posting")
        # Still show preview
        post_text, _ = create_post_text(movie)
        print("\n" + "="*60)
        print("📝 POST PREVIEW:")
        print("="*60)
        print(post_text)
        print("="*60)
        print(f"Character count: {len(post_text.encode('utf-8'))} bytes\n")
    
    print("\n✨ Done!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
