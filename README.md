# Game-server application bot

A single-guild Discord API v10 bot for private applications, staff decisions, and Google Sheets records. Commands work as both slash commands and with the `-` prefix.

## Setup

1. Install Python 3.12–3.14 and run `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env`, fill every blank, and edit all example values for the community.
3. Place the Google service-account file at `GOOGLE_SERVICE_ACCOUNT_FILE` and share `GOOGLE_SPREADSHEET_NAME` with that account.
4. Run `python main.py`, then use `/setup-applications` once in the desired channel.

In the Discord Developer Portal, enable the privileged **Server Members Intent** and **Message Content Intent**. The bot needs View Channels, Send Messages, Manage Channels, Manage Roles, Read Message History, Attach Files, Embed Links, and Use Application Commands. Its role must be above the configured applicant and member roles.

`APPLICATION_QUESTIONS` accepts real newlines in a double-quoted dotenv value or literal `\n` sequences from a hosting dashboard. Questions are trimmed, blank lines are removed, and numbering is automatic.

## Commands

- Staff administrators: `setup-applications`, `accept`, `deny`, `banlist`, `ban`, `discipline`, `payment`, and `donation`.
- Bot owner: `leave`, `listguilds`, and `dumpdb`.

Google calls run off the Discord event loop. Jishaku loads only when `ENABLE_JISHAKU=true`.

## Deployment checklist

- Back up the old SQLite database.
- Use a new `DATABASE_PATH` when retargeting the bot to another community.
- Verify all configured channel and role IDs in a test guild.
- Start the bot and confirm slash-command sync.
- Post the application panel, restart the bot, and test its button again.
- Confirm ticket privacy, applicant/member role changes, acceptance, denial, transcripts, and member-departure cleanup.
- Run each Google command and confirm it updates the configured worksheet.
- Retire the old reaction panel after the button workflow passes.

Run local checks with:

```console
python -m compileall -q .
python -m unittest discover -v
```
