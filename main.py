import asyncio
import logging

import aiosqlite
import discord
from discord.ext import commands

from config import Config, ConfigurationError, load_config
from utils import migrate_tickets


EXTENSIONS = ("applications", "tickets", "sheet_commands", "owner_commands", "errors")


class GameServerBot(commands.Bot):
    def __init__(self, config: Config):
        intents = discord.Intents.none()
        intents.guilds = True
        intents.members = True
        intents.guild_messages = True
        intents.message_content = True
        super().__init__(
            command_prefix="-",
            case_insensitive=True,
            intents=intents,
            allowed_mentions=discord.AllowedMentions(
                roles=True, users=True, everyone=False
            ),
            activity=discord.Game(name=config.bot_activity),
        )
        self.config = config
        self.db: aiosqlite.Connection | None = None
        self.application_lock = asyncio.Lock()

    async def setup_hook(self) -> None:
        self.db = await aiosqlite.connect(self.config.database_path)
        await migrate_tickets(self.db)
        for extension in EXTENSIONS:
            await self.load_extension(f"cogs.{extension}")
        if self.config.enable_jishaku:
            await self.load_extension("jishaku")

        guild = discord.Object(id=self.config.guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def close(self) -> None:
        if self.db is not None:
            await self.db.close()
        await super().close()

    async def on_ready(self) -> None:
        logging.getLogger(__name__).info(
            "Logged in as %s (%s) in %d guild(s)",
            self.user,
            self.user.id,
            len(self.guilds),
        )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
    )
    try:
        config = load_config()
    except ConfigurationError as error:
        raise SystemExit(f"Configuration error: {error}") from error
    GameServerBot(config).run(config.discord_token, log_handler=None)


if __name__ == "__main__":
    main()
