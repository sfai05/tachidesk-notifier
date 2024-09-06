# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.5.1

# Copy only requirements to cache them in docker layer
COPY pyproject.toml poetry.lock* /app/

# Configure poetry and install project dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copy the rest of the application's code
COPY . /app

# Create directories for JSON data, thumbnails, and logs
RUN mkdir -p /app/data /app/thumbnails /app/logs

# Set the APP_DIR environment variable
ENV APP_DIR=/app

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# Create a script to setup and run cron with the SCHEDULE environment variable
RUN echo '#!/bin/sh\n\
printenv > /etc/environment\n\
PYTHON_PATH=$(which python)\n\
echo "Running initial check..."\n\
$PYTHON_PATH /app/tachidesk_notifier/tachidesk_notifier.py >> /var/log/cron.log 2>&1\n\
echo "$SCHEDULE $PYTHON_PATH /app/tachidesk_notifier/tachidesk_notifier.py >> /var/log/cron.log 2>&1" > /etc/cron.d/tachidesk-notifier-cron\n\
chmod 0644 /etc/cron.d/tachidesk-notifier-cron\n\
crontab /etc/cron.d/tachidesk-notifier-cron\n\
echo "Starting cron..."\n\
cron && tail -f /var/log/cron.log' > /app/start.sh && chmod +x /app/start.sh

# Run the command on container startup
CMD ["/app/start.sh"]