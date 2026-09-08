from dataclasses import dataclass
from os import environ
from pathlib import Path
from string import Template
from typing import Mapping

from dotenv import dotenv_values


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    discord_token: str
    guild_id: int
    server_name: str
    server_ip: str
    application_category_id: int
    app_log_channel_id: int
    general_channel_id: int
    rules_channel_id: int
    applicant_role_id: int
    member_role_id: int
    application_questions: tuple[str, ...]
    rules_agreement_text: str
    welcome_details: str
    google_service_account_file: str
    google_spreadsheet_name: str
    banned_players_worksheet: str
    payments_worksheet: str
    discipline_worksheet: str
    finances_worksheet: str
    payment_unit: str
    donation_currency: str
    database_path: str
    bot_activity: str
    enable_jishaku: bool

    @property
    def application_prompt(self) -> str:
        questions = "\n".join(
            f"{number}. {question}"
            for number, question in enumerate(self.application_questions, 1)
        )
        return (
            f"Please answer the following questions for {self.server_name}.\n\n"
            f"{questions}\n\n"
            "You may also attach pictures of previous builds or projects.\n\n"
            f"Read the rules in <#{self.rules_channel_id}>, then repeat this sentence "
            f'to confirm your agreement:\n"{self.rules_agreement_text}"'
        )

    def welcome_message(self, mention: str) -> str:
        return (
            f"Welcome to {self.server_name}, {mention}!\n"
            f"The server IP is `{self.server_ip}`\n{self.welcome_details}"
        )

    def acceptance_message(self, moderator: str) -> str:
        return (
            f"Your application to {self.server_name} was accepted by {moderator}! "
            f"The server IP is `{self.server_ip}`."
        )


_TEXT_FIELDS = {
    "DISCORD_TOKEN": "discord_token",
    "SERVER_NAME": "server_name",
    "SERVER_IP": "server_ip",
    "RULES_AGREEMENT_TEXT": "rules_agreement_text",
    "WELCOME_DETAILS": "welcome_details",
    "GOOGLE_SERVICE_ACCOUNT_FILE": "google_service_account_file",
    "GOOGLE_SPREADSHEET_NAME": "google_spreadsheet_name",
    "BANNED_PLAYERS_WORKSHEET": "banned_players_worksheet",
    "PAYMENTS_WORKSHEET": "payments_worksheet",
    "DISCIPLINE_WORKSHEET": "discipline_worksheet",
    "FINANCES_WORKSHEET": "finances_worksheet",
    "PAYMENT_UNIT": "payment_unit",
    "DONATION_CURRENCY": "donation_currency",
    "DATABASE_PATH": "database_path",
    "BOT_ACTIVITY": "bot_activity",
}

_ID_FIELDS = {
    "GUILD_ID": "guild_id",
    "APPLICATION_CATEGORY_ID": "application_category_id",
    "APP_LOG_CHANNEL_ID": "app_log_channel_id",
    "GENERAL_CHANNEL_ID": "general_channel_id",
    "RULES_CHANNEL_ID": "rules_channel_id",
    "APPLICANT_ROLE_ID": "applicant_role_id",
    "MEMBER_ROLE_ID": "member_role_id",
}


def _lines(value: str) -> tuple[str, ...]:
    return tuple(
        line.strip()
        for line in value.replace("\\n", "\n").splitlines()
        if line.strip()
    )


def load_config(
    env: Mapping[str, str] | None = None,
    dotenv_path: str | Path | None = ".env",
) -> Config:
    values = (
        dict(dotenv_values(dotenv_path))
        if dotenv_path and Path(dotenv_path).is_file()
        else {}
    )
    values.update(environ if env is None else env)
    missing = [
        name
        for name in (
            *_TEXT_FIELDS,
            *_ID_FIELDS,
            "APPLICATION_QUESTIONS",
            "ENABLE_JISHAKU",
        )
        if not values.get(name, "").strip()
    ]
    if missing:
        raise ConfigurationError(f"Missing required environment variables: {', '.join(missing)}")

    parsed: dict[str, object] = {
        field: Template(values[name].strip()).safe_substitute(values)
        for name, field in _TEXT_FIELDS.items()
    }
    malformed = []
    for name, field in _ID_FIELDS.items():
        try:
            parsed[field] = int(values[name])
            if parsed[field] <= 0:
                raise ValueError
        except (TypeError, ValueError):
            malformed.append(name)
    if malformed:
        raise ConfigurationError(
            f"Environment variables must be positive integers: {', '.join(malformed)}"
        )

    questions = _lines(values["APPLICATION_QUESTIONS"])
    if not questions:
        raise ConfigurationError(
            "APPLICATION_QUESTIONS must contain at least one non-empty question"
        )
    enabled = values["ENABLE_JISHAKU"].strip().lower()
    if enabled not in {"true", "false"}:
        raise ConfigurationError("ENABLE_JISHAKU must be true or false")

    config = Config(
        **parsed,
        application_questions=questions,
        enable_jishaku=enabled == "true",
    )
    if len(config.application_prompt) > 2_000:
        raise ConfigurationError(
            "APPLICATION_QUESTIONS render an application prompt longer than "
            "Discord's 2,000-character limit"
        )
    return config
