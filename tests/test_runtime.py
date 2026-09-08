import unittest

import aiosqlite

from main import EXTENSIONS, GameServerBot
from tests.common import config
from utils import migrate_tickets


class RuntimeTests(unittest.TestCase):
    def test_uses_only_required_intents_and_configured_activity(self):
        bot = GameServerBot(config(BOT_ACTIVITY="Watching applications"))

        self.assertTrue(bot.intents.guilds)
        self.assertTrue(bot.intents.members)
        self.assertTrue(bot.intents.guild_messages)
        self.assertTrue(bot.intents.message_content)
        self.assertFalse(bot.intents.dm_messages)
        self.assertFalse(bot.intents.guild_reactions)
        self.assertFalse(bot.intents.presences)
        self.assertEqual(bot.activity.name, "Watching applications")
        self.assertEqual(bot.command_prefix, "-")


class CommandRegistrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_commands_are_hybrid_and_view_is_persistent(self):
        bot = GameServerBot(config())
        bot.db = await aiosqlite.connect(":memory:")
        await migrate_tickets(bot.db)
        try:
            for extension in EXTENSIONS:
                await bot.load_extension(f"cogs.{extension}")

            commands = {
                "accept",
                "ban",
                "banlist",
                "deny",
                "discipline",
                "donation",
                "dumpdb",
                "leave",
                "listguilds",
                "payment",
                "setup-applications",
                "setup-member-permissions",
            }
            self.assertEqual(
                {command.name for command in bot.commands} - {"help"}, commands
            )
            self.assertEqual(
                {command.name for command in bot.tree.get_commands()}, commands
            )
            self.assertEqual(len(bot.persistent_views), 1)
        finally:
            await bot.db.close()


if __name__ == "__main__":
    unittest.main()
