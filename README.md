# Tachidesk Notifier

Tachidesk Notifier is a Python-based application that integrates with Tachidesk to send Telegram notifications for new manga chapters. It uses a GraphQL API to fetch manga data, stores information locally, and sends notifications with thumbnails. This entire project was conceptualized and created with the assistance of Claude, an AI language model.

## Features

- Fetches manga data from Tachidesk using GraphQL
- Sends Telegram notifications for new unread chapters
- Includes manga thumbnails in notifications
- Caches thumbnails locally to reduce bandwidth usage
- Prevents notification spam for older chapters on first run
- Runs on a customizable schedule using cron (when deployed with Docker)

## Prerequisites

- Python 3.9 or higher
- Docker (for containerized deployment)
- A Tachidesk instance
- A Telegram Bot Token and Chat ID

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/tachidesk-notifier.git
   cd tachidesk-notifier
   ```

2. Copy the `.env.sample` file to `.env` and fill in your details:
   ```
   cp .env.sample .env
   ```

3. Edit the `.env` file with your specific configuration:
   ```
   TACHIDESK_BASE_URL=http://your-tachidesk-base-url:4567
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   TELEGRAM_CHAT_ID=your_telegram_chat_id
   JSON_FILE_PATH=/app/data/manga_data.json
   THUMBNAIL_DIR=/app/thumbnails
   SCHEDULE="0 * * * *"
   ```

## Usage

### Running Locally

1. Install the required dependencies:
   ```
   pip install poetry
   poetry install
   ```

2. Run the script:
   ```
   poetry run python tachidesk_notifier.py
   ```

### Running with Docker

1. Build the Docker image:
   ```
   docker build -t tachidesk-notifier .
   ```

2. Run the Docker container:
   ```
   docker run -d --name tachidesk-notifier \
     --env-file .env \
     tachidesk-notifier
   ```
   or
    ```
   docker run -d --name tachidesk-notifier \
     -e TACHIDESK_BASE_URL=http://your-tachidesk-base-url:4567 \
     -e TELEGRAM_BOT_TOKEN=your_telegram_bot_token \
     -e TELEGRAM_CHAT_ID=your_telegram_chat_id \
     -e JSON_FILE_PATH=/app/data/manga_data.json \
     -e THUMBNAIL_DIR=/app/thumbnails \
     -e SCHEDULE="0 * * * *" \
     -v $(pwd)/data:/app/data \
     -v $(pwd)/thumbnails:/app/thumbnails \
     tachidesk-notifier
   ```
## Running Tests

To run the tests for this project:

1. Ensure you have the development dependencies installed:
   ```
   poetry install
   ```

2. Run the tests using pytest:
   ```
   poetry run pytest
   ```

This will run all the tests in the `tests/` directory and provide a summary of the results.

## Configuration

- `TACHIDESK_BASE_URL`: The base URL of your Tachidesk instance
- `TELEGRAM_BOT_TOKEN`: Your Telegram Bot Token
- `TELEGRAM_CHAT_ID`: Your Telegram Chat ID
- `JSON_FILE_PATH`: Path to store the manga data JSON file
- `THUMBNAIL_DIR`: Directory to store downloaded thumbnails
- `SCHEDULE`: Cron schedule for running the script (e.g., "0 * * * *" for every hour)

## How It Works

1. The script fetches manga data from Tachidesk using the GraphQL API.
2. It compares the fetched data with locally stored data to identify new chapters.
3. For new or updated manga:
   - If it's a new manga, it only sends a notification if the chapter is less than 24 hours old.
   - For existing manga with new chapters, it always sends a notification.
4. Thumbnails are downloaded and cached locally.
5. Notifications are sent via Telegram, including the manga thumbnail and chapter information.

## Notification Behavior

- First Run: To prevent notification spam, only chapters uploaded within the last 24 hours will trigger notifications for newly added manga.
- Subsequent Runs: All new chapters for tracked manga will trigger notifications, regardless of upload date.

## Development

To contribute to this project:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Acknowledgements

- [Tachidesk](https://github.com/Suwayomi/Tachidesk-Server) for the manga server
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) for Telegram integration
- [Poetry](https://python-poetry.org/) for dependency management