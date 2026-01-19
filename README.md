# Chronix

Chronix is a high-performance, multi-purpose Discord bot built with `discord.py` and PostgreSQL.

## Features

- **Economy (Global):** Deep economy system with banking, transfers, daily rewards, and global leaderboards.
- **Moderation:** Advanced warning system with logging, and standard moderation tools (kick, ban, timeout).
- **Music:** High-quality music playback from YouTube using `yt-dlp` (supports queuing, skipping, etc.).

## Prerequisites

- Python 3.9+
- PostgreSQL Database
- FFmpeg (for music)

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd chronix
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r chronix/requirements.txt
    ```

3.  **Database Configuration:**
    - Ensure PostgreSQL is running.
    - Create a database (e.g., `chronix`).
    - The bot automatically initializes the schema (`chronix/data/schema.sql`) on the first run.

4.  **Environment Variables:**
    - Copy `.env.example` to `.env`:
        ```bash
        cp chronix/.env.example chronix/.env
        ```
    - Edit `chronix/.env` and fill in your details:
        ```env
        DISCORD_TOKEN=your_discord_bot_token
        POSTGRES_USER=postgres
        POSTGRES_PASSWORD=your_password
        POSTGRES_DB=chronix
        POSTGRES_HOST=localhost
        POSTGRES_PORT=5432
        ```

## Running the Bot

```bash
python3 chronix/main.py
```
