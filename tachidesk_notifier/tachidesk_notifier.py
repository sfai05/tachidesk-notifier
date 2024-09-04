import requests
import json
import os
import sys
from datetime import datetime, timedelta
import telebot
from dotenv import load_dotenv
from urllib.parse import urljoin
import hashlib

# Load environment variables
load_dotenv()

# Check for required environment variables
required_vars = ['TACHIDESK_BASE_URL', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print(f"Error: The following required environment variables are not set: {', '.join(missing_vars)}")
    sys.exit(1)

# Tachidesk base URL and GraphQL endpoint
base_url = os.getenv('TACHIDESK_BASE_URL')
graphql_endpoint = urljoin(base_url, 'api/graphql')

# Telegram Bot Token and Chat ID
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Initialize Telegram bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# JSON file for storing manga data
JSON_FILE = os.getenv('JSON_FILE_PATH', os.path.join(os.getcwd(), 'manga_data.json'))

# Directory for storing thumbnails
THUMBNAIL_DIR = os.getenv('THUMBNAIL_DIR', os.path.join(os.getcwd(), 'thumbnails'))
os.makedirs(THUMBNAIL_DIR, exist_ok=True)

# GraphQL query
query = """
query {
  categories {
    nodes {
      mangas {
        nodes {
          title
          firstUnreadChapter {
            id
            name
            uploadDate
          }
          id
          thumbnailUrl
        }
      }
    }
  }
}
"""

def fetch_manga_data():
    response = requests.post(graphql_endpoint, json={'query': query})
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Query failed with status code: {response.status_code}")

def load_stored_data():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_manga_data(data):
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_thumbnail_path(manga_id, thumbnail_url):
    filename = f"{manga_id}_{hashlib.md5(thumbnail_url.encode()).hexdigest()}.jpg"
    return os.path.join(THUMBNAIL_DIR, filename)

def download_thumbnail(thumbnail_url, manga_id):
    full_thumbnail_url = urljoin(base_url, thumbnail_url)
    local_path = get_thumbnail_path(manga_id, thumbnail_url)
    
    if os.path.exists(local_path):
        print(f"Thumbnail already exists for manga {manga_id}")
        return local_path
    
    try:
        response = requests.get(full_thumbnail_url, timeout=10)
        response.raise_for_status()
        with open(local_path, 'wb') as f:
            f.write(response.content)
        print(f"Successfully downloaded thumbnail for manga {manga_id}")
        return local_path
    except Exception as e:
        print(f"Error downloading thumbnail for manga {manga_id}: {str(e)}")
        return None

def send_telegram_notification(title, chapter_name, upload_date, thumbnail_path):
    message = f"New unread chapter for {title}:\n" \
              f"Chapter: {chapter_name}\n" \
              f"Upload Date: {upload_date}"
    
    try:
        if thumbnail_path and os.path.exists(thumbnail_path):
            with open(thumbnail_path, 'rb') as photo:
                bot.send_photo(TELEGRAM_CHAT_ID, photo, caption=message)
            print(f"Successfully sent notification with thumbnail for {title}")
        else:
            fallback_message = f"{message}\n(Thumbnail couldn't be loaded)"
            bot.send_message(TELEGRAM_CHAT_ID, fallback_message)
            print(f"Sent notification without thumbnail for {title}")
    except Exception as e:
        print(f"Error sending Telegram notification: {str(e)}")
        fallback_message = f"{message}\n(Error sending notification)"
        bot.send_message(TELEGRAM_CHAT_ID, fallback_message)

def process_manga_data(data):
    mangas = data['data']['categories']['nodes'][0]['mangas']['nodes']
    stored_data = load_stored_data()
    updated_data = {}
    current_time = datetime.now()
    
    for manga in mangas:
        manga_id = str(manga['id'])
        title = manga['title']
        thumbnail_url = manga.get('thumbnailUrl', '')
        
        if manga['firstUnreadChapter']:
            chapter = manga['firstUnreadChapter']
            new_chapter_id = str(chapter['id'])
            new_chapter_name = chapter['name']
            new_upload_date = datetime.fromtimestamp(int(chapter['uploadDate']) / 1000)
            
            stored_chapter = stored_data.get(manga_id, {})
            
            if not stored_chapter:
                # New manga entry
                updated_data[manga_id] = {
                    'title': title,
                    'chapter_id': new_chapter_id,
                    'chapter_name': new_chapter_name,
                    'upload_date': new_upload_date.isoformat(),
                    'thumbnail_url': thumbnail_url
                }
                
                # Only send notification if the upload date is within the last day
                if current_time - new_upload_date <= timedelta(days=1):
                    thumbnail_path = download_thumbnail(thumbnail_url, manga_id)
                    send_telegram_notification(title, new_chapter_name, new_upload_date.isoformat(), thumbnail_path)
                    print(f"New manga added and notified: {title}")
                else:
                    print(f"New manga added without notification (older than 1 day): {title}")
            
            elif stored_chapter.get('chapter_id') != new_chapter_id:
                # Existing manga with new chapter
                updated_data[manga_id] = {
                    'title': title,
                    'chapter_id': new_chapter_id,
                    'chapter_name': new_chapter_name,
                    'upload_date': new_upload_date.isoformat(),
                    'thumbnail_url': thumbnail_url
                }
                
                thumbnail_path = download_thumbnail(thumbnail_url, manga_id)
                send_telegram_notification(title, new_chapter_name, new_upload_date.isoformat(), thumbnail_path)
                print(f"Updated: {title}")
                print(f"New Chapter: {new_chapter_name}")
                print(f"Upload Date: {new_upload_date.isoformat()}")
            else:
                updated_data[manga_id] = stored_chapter
                print(f"No new chapter for: {title}")
        else:
            updated_data[manga_id] = stored_data.get(manga_id, {})
            print(f"No unread chapters for: {title}")
    
    save_manga_data(updated_data)

def main():
    try:
        data = fetch_manga_data()
        process_manga_data(data)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()