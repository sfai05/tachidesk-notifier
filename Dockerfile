# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install cron and Poetry
RUN apt-get update && apt-get install -y cron && \
    pip install poetry

# Copy the project files into the container
COPY pyproject.toml poetry.lock* /app/

# Install dependencies
RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi

# Copy the entire project into the container
COPY . /app

# Create directories for JSON data and thumbnails
RUN mkdir -p /app/data /app/thumbnails

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# Create a script to setup and run cron with the SCHEDULE environment variable
RUN echo '#!/bin/sh\n\
echo "Running initial check..."\n\
python /app/tachidesk_notifier/tachidesk_notifier.py >> /var/log/cron.log 2>&1\n\
echo "$SCHEDULE python /app/tachidesk_notifier/tachidesk_notifier.py >> /var/log/cron.log 2>&1" > /etc/cron.d/tachidesk-notifier-cron\n\
chmod 0644 /etc/cron.d/tachidesk-notifier-cron\n\
crontab /etc/cron.d/tachidesk-notifier-cron\n\
echo "Starting cron..."\n\
cron && tail -f /var/log/cron.log' > /app/start.sh && chmod +x /app/start.sh

# Run the command on container startup
CMD ["/app/start.sh"]