# Memory Book Bot

Telegram bot for creating personal memory books from your daily messages, voice notes, and photos.

## Project Structure

```
memory-book-bot/
├── bot/                    # Bot logic and handlers
│   ├── __init__.py
│   ├── main.py            # Entry point
│   ├── handlers/          # Message handlers
│   │   ├── __init__.py
│   │   ├── text.py
│   │   ├── voice.py
│   │   └── photo.py
│   ├── services/          # Business logic
│   │   ├── __init__.py
│   │   ├── transcription.py
│   │   └── book_generator.py
│   └── keyboards/         # Inline keyboards
│       └── __init__.py
├── db/                     # Database models and connection
│   ├── __init__.py
│   ├── database.py
│   └── models.py
├── migrations/             # Alembic migrations
├── templates/              # Jinja2 templates for PDF
│   └── book.html
├── static/                 # Static files
│   ├── css/
│   │   └── book.css
│   └── fonts/
├── tests/                  # Unit tests
├── logs/                   # Log files
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## Features

- 📝 Text messages with hashtag support
- 🎤 Voice message transcription via Whisper.cpp
- 📷 Photo storage and inclusion in books
- 📚 PDF book generation with beautiful design
- 🏷️ Tag-based organization
- 📅 Chapter organization by weeks/months

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Telegram Bot Token (from @BotFather)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd memory-book-bot
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Edit `.env` and add your Telegram bot token:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
DATABASE_URL=postgresql://user:password@db:5432/memory_book
REDIS_URL=redis://redis:6379/0
```

4. Start the services:
```bash
docker-compose up --build
```

### Usage

1. Start a chat with your bot on Telegram
2. Use `/start` to begin
3. Send text messages, voice notes, or photos
4. Use `#tags` to organize your memories
5. Generate your book with `/book`

### Commands

- `/start` - Start the bot
- `/help` - Show help information
- `/add` - Add a memory manually
- `/list` - List your memories
- `/book` - Generate PDF book

## Development

### Running tests

```bash
docker-compose exec bot pytest tests/
```

### Database migrations

```bash
docker-compose exec bot alembic upgrade head
```

## Deployment on Render

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set environment variables
4. Deploy!

## Tech Stack

- **Backend**: Python 3.11+
- **Bot Framework**: aiogram 3.x
- **Database**: PostgreSQL
- **Cache**: Redis
- **PDF Generation**: WeasyPrint
- **Transcription**: Whisper.cpp
- **Templates**: Jinja2

## License

MIT