import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import json
import os
import hashlib


# Import the functions you want to test
from tachidesk_notifier.tachidesk_notifier import (
    load_stored_data,
    save_manga_data,
    get_thumbnail_path,
    download_thumbnail,
    send_telegram_notification,
    process_manga_data
)

# Sample test data
sample_manga_data = {
    "data": {
        "categories": {
            "nodes": [
                {
                    "mangas": {
                        "nodes": [
                            {
                                "id": "1",
                                "title": "Test Manga",
                                "firstUnreadChapter": {
                                    "id": "100",
                                    "name": "Chapter 1",
                                    "uploadDate": str(int((datetime.now() - timedelta(hours=1)).timestamp() * 1000))
                                },
                                "thumbnailUrl": "/covers/1.jpg"
                            }
                        ]
                    }
                }
            ]
        }
    }
}

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("TACHIDESK_BASE_URL", "http://localhost:4567")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")
    monkeypatch.setenv("JSON_FILE_PATH", "/tmp/test_manga_data.json")
    monkeypatch.setenv("THUMBNAIL_DIR", "/tmp/test_thumbnails")

@pytest.fixture
def mock_telebot():
    with patch("tachidesk_notifier.tachidesk_notifier.telebot.TeleBot") as mock:
        yield mock

def test_load_stored_data(tmp_path):
    # Create a temporary JSON file
    test_data = {"test": "data"}
    json_file = tmp_path / "test_data.json"
    json_file.write_text(json.dumps(test_data))
    
    # Test loading the data
    with patch("tachidesk_notifier.tachidesk_notifier.JSON_FILE", str(json_file)):
        loaded_data = load_stored_data()
        assert loaded_data == test_data

def test_save_manga_data(tmp_path):
    test_data = {"test": "data"}
    json_file = tmp_path / "test_data.json"
    
    with patch("tachidesk_notifier.tachidesk_notifier.JSON_FILE", str(json_file)):
        save_manga_data(test_data)
        assert json.loads(json_file.read_text()) == test_data

def test_get_thumbnail_path():
    with patch("tachidesk_notifier.tachidesk_notifier.THUMBNAIL_DIR", "/tmp/test_thumbnails"):
        manga_id = "1"
        thumbnail_url = "/covers/1.jpg"
        expected_path = os.path.join("/tmp/test_thumbnails", f"1_{hashlib.md5(thumbnail_url.encode()).hexdigest()}.jpg")
        assert get_thumbnail_path(manga_id, thumbnail_url) == expected_path

@patch("requests.get")
def test_download_thumbnail(mock_get, tmp_path):
    mock_get.return_value.content = b"fake image data"
    manga_id = "1"
    thumbnail_url = "/covers/1.jpg"
    
    with patch("tachidesk_notifier.tachidesk_notifier.THUMBNAIL_DIR", str(tmp_path)):
        path = download_thumbnail(thumbnail_url, manga_id)
        assert os.path.exists(path)
        with open(path, "rb") as f:
            assert f.read() == b"fake image data"

@patch("tachidesk_notifier.tachidesk_notifier.send_telegram_notification")
@patch("tachidesk_notifier.tachidesk_notifier.download_thumbnail")
def test_process_manga_data(mock_download, mock_send, tmp_path):
    mock_download.return_value = "/tmp/test.jpg"
    
    json_file = tmp_path / "test_data.json"
    json_file.write_text("{}")
    
    with patch("tachidesk_notifier.tachidesk_notifier.JSON_FILE", str(json_file)):
        process_manga_data(sample_manga_data)
    
    mock_download.assert_called_once()
    mock_send.assert_called_once()
    
    # Check that the data was saved
    saved_data = json.loads(json_file.read_text())
    assert "1" in saved_data
    assert saved_data["1"]["title"] == "Test Manga"

if __name__ == "__main__":
    pytest.main()