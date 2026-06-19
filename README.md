# Mor Logistics Operations Assistant (Discord Bot)

A highly capable, autonomous Operations Assistant Discord Bot for Mor Logistics. This bot upgrades the initial email outreach functionality to include document OCR, conversational LLM data extraction, and a scalable, modular cog architecture backed by a SQLite database.

## Features

1. **Email Outreach Pipeline (`/sendmail`)**
   - Autonomously drafts and sends professional broker outreach emails using Google Gemini.
   - Logs sent emails automatically into Google Sheets.
2. **Document OCR Pipeline (`/parsefile` & Auto-listener)**
   - Upload DAT load board screenshots or PDF rate confirmations directly in Discord.
   - The bot extracts data automatically using Tesseract OCR and summarizes it via LLM.
3. **Conversational LLM Tasks**
   - Just mention the bot in a thread or channel. It uses Gemini to parse natural language instructions.
   - Extracts structured data (dates, locations, load assignments) and logs actionable tasks into a local database.
4. **Modular Architecture & Database**
   - Uses `discord.ext.commands.Cog` to separate features (`email_outreach`, `document_ocr`, `conversational_llm`).
   - SQLite with SQLAlchemy ORM (and `aiosqlite`) maintains a robust local database for tasks and logs.
5. **Advanced Logging & Error Handling**
   - Graceful global error handling so the bot never crashes.
   - Saves standard logs to `broker_bot.log` and exclusively logs errors to `bot-errors.log`.

## Setup & Installation

### 1. System Requirements

The OCR component requires system-level dependencies.
If you're on Debian/Ubuntu, install them via:
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils
```
On macOS:
```bash
brew install tesseract poppler
```

### 2. Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Variables

1. Copy `.env.example` to `.env`.
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and fill in your tokens.
   - Get a Discord Bot Token from the [Discord Developer Portal](https://discord.com/developers/applications).
   - Get a Google Workspace App Password.
   - Save your Google Cloud Service Account JSON as `google_credentials.json` in the root folder.

### 4. Discord Privileged Gateway Intents

**Important:** For the bot to read messages and perform OCR/Conversational actions, you must enable the "Message Content Intent" in the Discord Developer Portal:
1. Go to your Application -> **Bot** tab.
2. Scroll down to **Privileged Gateway Intents**.
3. Toggle **Message Content Intent** to ON.
4. Save changes.

### 5. Running the Bot

Run the bot directly via:
```bash
python main.py
```
The bot will automatically:
1. Initialize the `bot_database.db` SQLite database.
2. Sync the slash commands to your Discord server.
3. Show as "online" and "watching /sendmail".

Enjoy your new autonomous Operations Assistant!
