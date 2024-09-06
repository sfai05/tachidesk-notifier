import requests
import json
import os
import sys
from datetime import datetime, timedelta
import telebot
from dotenv import load_dotenv
from urllib.parse import urljoin
import hashlib
import logging
import logging.config

# Load environment variables
load_dotenv()
APP_DIR = os.getenv('APP_DIR', os.getcwd())

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(APP_DIR, 'logs/tachidesk_notifier.log'))
    ]
)
logger = logging.getLogger(__name__)

# Check for required environment variables
required_vars = ['TACHIDESK_BASE_URL', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
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
JSON_FILE = os.getenv('JSON_FILE_PATH', os.path.join(APP_DIR, 'data/manga_data.json'))

# Directory for storing thumbnails
THUMBNAIL_DIR = os.getenv('THUMBNAIL_DIR', os.path.join(APP_DIR, 'data/thumbnails'))
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
    logger.info("Fetching manga data from Tachidesk API")
    try:
        response = requests.post(graphql_endpoint, json={'query': query})
        response.raise_for_status()
        logger.info("Successfully fetched manga data")
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch manga data: {str(e)}")
        raise

def load_stored_data():
    logger.info(f"Loading stored data from {JSON_FILE}")
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded data for {len(data)} manga")
        return data
    logger.info("No stored data found")
    return {}

def save_manga_data(data):
    logger.info(f"Saving manga data to {JSON_FILE}")
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved data for {len(data)} manga")

def get_thumbnail_path(manga_id, thumbnail_url):
    filename = f"{manga_id}_{hashlib.md5(thumbnail_url.encode()).hexdigest()}.jpg"
    return os.path.join(THUMBNAIL_DIR, filename)

def download_thumbnail(thumbnail_url, manga_id):
    logger.info(f"Downloading thumbnail for manga {manga_id}")
    full_thumbnail_url = urljoin(base_url, thumbnail_url)
    local_path = get_thumbnail_path(manga_id, thumbnail_url)
    
    if os.path.exists(local_path):
        logger.info(f"Thumbnail already exists for manga {manga_id}")
        return local_path
    
    try:
        response = requests.get(full_thumbnail_url, timeout=10)
        response.raise_for_status()
        with open(local_path, 'wb') as f:
            f.write(response.content)
        logger.info(f"Successfully downloaded thumbnail for manga {manga_id}")
        return local_path
    except Exception as e:
        logger.error(f"Error downloading thumbnail for manga {manga_id}: {str(e)}")
        return None

def send_telegram_notification(title, chapter_name, upload_date, thumbnail_path):
    logger.info(f"Sending Telegram notification for {title}")
    message = f"New unread chapter for {title}:\n" \
              f"Chapter: {chapter_name}\n" \
              f"Upload Date: {upload_date}"
    
    try:
        if thumbnail_path and os.path.exists(thumbnail_path):
            with open(thumbnail_path, 'rb') as photo:
                bot.send_photo(TELEGRAM_CHAT_ID, photo, caption=message)
            logger.info(f"Successfully sent notification with thumbnail for {title}")
        else:
            bot.send_message(TELEGRAM_CHAT_ID, message)
            logger.info(f"Sent notification without thumbnail for {title}")
    except Exception as e:
        logger.error(f"Error sending Telegram notification for {title}: {str(e)}")

def process_manga_data(data):
    logger.info("Processing manga data")
    mangas = data['data']['categories']['nodes'][0]['mangas']['nodes']
    stored_data = load_stored_data()
    updated_data = {}
    current_time = datetime.now()
    
    for manga in mangas:
        manga_id = str(manga['id'])
        title = manga['title']
        thumbnail_url = manga.get('thumbnailUrl', '')
        
        logger.info(f"Processing manga: {title} (ID: {manga_id})")
        
        if manga['firstUnreadChapter']:
            chapter = manga['firstUnreadChapter']
            new_chapter_id = str(chapter['id'])
            new_chapter_name = chapter['name']
            new_upload_date = datetime.fromtimestamp(int(chapter['uploadDate']) / 1000)
            
            stored_chapter = stored_data.get(manga_id, {})
            
            if not stored_chapter:
                logger.info(f"New manga entry: {title}")
                updated_data[manga_id] = {
                    'title': title,
                    'chapter_id': new_chapter_id,
                    'chapter_name': new_chapter_name,
                    'upload_date': new_upload_date.isoformat(),
                    'thumbnail_url': thumbnail_url
                }
                
                if current_time - new_upload_date <= timedelta(hours=48):
                    thumbnail_path = download_thumbnail(thumbnail_url, manga_id)
                    send_telegram_notification(title, new_chapter_name, new_upload_date.isoformat(), thumbnail_path)
                    logger.info(f"New manga added and notified: {title}")
                else:
                    logger.info(f"New manga added without notification (older than 48 hours): {title}")
            
            elif stored_chapter.get('chapter_id') != new_chapter_id:
                logger.info(f"New chapter detected for {title}")
                updated_data[manga_id] = {
                    'title': title,
                    'chapter_id': new_chapter_id,
                    'chapter_name': new_chapter_name,
                    'upload_date': new_upload_date.isoformat(),
                    'thumbnail_url': thumbnail_url
                }
                
                thumbnail_path = download_thumbnail(thumbnail_url, manga_id)
                send_telegram_notification(title, new_chapter_name, new_upload_date.isoformat(), thumbnail_path)
                logger.info(f"Updated: {title}, New Chapter: {new_chapter_name}, Upload Date: {new_upload_date.isoformat()}")
            else:
                updated_data[manga_id] = stored_chapter
                logger.info(f"No new chapter for: {title}")
        else:
            updated_data[manga_id] = stored_data.get(manga_id, {})
            logger.info(f"No unread chapters for: {title}")
    
    save_manga_data(updated_data)
    logger.info("Finished processing manga data")

def main():
    logger.info("Starting Tachidesk Notifier")
    try:
        data = fetch_manga_data()
        process_manga_data(data)
    except Exception as e:
        logger.error(f"An error occurred in the main process: {str(e)}")
    logger.info("Tachidesk Notifier finished")

if __name__ == "__main__":
    main()