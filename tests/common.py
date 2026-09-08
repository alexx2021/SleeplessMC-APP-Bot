from config import Config, load_config


def environment(**changes: str) -> dict[str, str]:
    values = {
        "DISCORD_TOKEN": "token",
        "GUILD_ID": "1",
        "SERVER_NAME": "Example Server",
        "SERVER_IP": "game.example.test",
        "APPLICATION_CATEGORY_ID": "2",
        "APP_LOG_CHANNEL_ID": "3",
        "GENERAL_CHANNEL_ID": "4",
        "RULES_CHANNEL_ID": "5",
        "APPLICANT_ROLE_ID": "6",
        "MEMBER_ROLE_ID": "7",
        "APPLICATION_QUESTIONS": r"First question?\nSecond question?",
        "RULES_AGREEMENT_TEXT": "I agree.",
        "WELCOME_DETAILS": "Follow the welcome instructions.",
        "GOOGLE_SERVICE_ACCOUNT_FILE": "service-account.json",
        "GOOGLE_SPREADSHEET_NAME": "Community Book",
        "BANNED_PLAYERS_WORKSHEET": "Bans",
        "PAYMENTS_WORKSHEET": "Payments",
        "DISCIPLINE_WORKSHEET": "Discipline",
        "FINANCES_WORKSHEET": "Finances",
        "PAYMENT_UNIT": "token",
        "DONATION_CURRENCY": "€",
        "DATABASE_PATH": ":memory:",
        "BOT_ACTIVITY": "Applications for ${SERVER_NAME}",
        "ENABLE_JISHAKU": "false",
    }
    values.update(changes)
    return values


def config(**changes: str) -> Config:
    return load_config(environment(**changes), None)
