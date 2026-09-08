import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock

import aiosqlite
import discord

from cogs.applications import ApplicationView, Applications
from tests.common import config
from utils import migrate_tickets


class ApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.config = config()
        self.db = await aiosqlite.connect(":memory:")
        await migrate_tickets(self.db)
        self.bot = SimpleNamespace(
            config=self.config, db=self.db, application_lock=asyncio.Lock()
        )

        self.member = MagicMock(spec=discord.Member)
        self.member.id = 42
        self.member.name = "player"
        self.member.mention = "<@42>"
        self.member.add_roles = AsyncMock()
        self.member.remove_roles = AsyncMock()

        self.created = MagicMock(spec=discord.TextChannel)
        self.created.id = 99
        self.created.mention = "<#99>"
        self.created.send = AsyncMock()
        self.created.delete = AsyncMock()

        self.resources = {
            2: MagicMock(spec=discord.CategoryChannel),
            3: MagicMock(spec=discord.TextChannel),
            4: MagicMock(spec=discord.TextChannel),
            5: MagicMock(spec=discord.TextChannel),
            99: self.created,
        }
        self.roles = {6: MagicMock(spec=discord.Role), 7: MagicMock(spec=discord.Role)}
        self.guild = MagicMock(spec=discord.Guild)
        self.guild.id = 1
        self.guild.default_role = MagicMock(spec=discord.Role)
        self.guild.get_channel.side_effect = self.resources.get
        self.guild.get_role.side_effect = self.roles.get
        self.guild.create_text_channel = AsyncMock(return_value=self.created)

    async def asyncTearDown(self):
        await self.db.close()

    def interaction(self):
        interaction = MagicMock(spec=discord.Interaction)
        interaction.guild = self.guild
        interaction.user = self.member
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()
        return interaction

    async def click(self, interaction):
        view = ApplicationView(self.bot)
        await view.children[0].callback(interaction)

    async def test_concurrent_duplicate_clicks_create_one_ticket(self):
        first, second = self.interaction(), self.interaction()
        await asyncio.gather(self.click(first), self.click(second))

        self.assertEqual(self.guild.create_text_channel.await_count, 1)
        self.assertEqual(
            await self.db.execute_fetchall("SELECT user_id, channel_id FROM tickets"),
            [(42, 99)],
        )
        replies = " ".join(
            call.args[0]
            for interaction in (first, second)
            for call in interaction.followup.send.await_args_list
        )
        self.assertIn("ready", replies)
        self.assertIn("already", replies)

    async def test_stale_mapping_is_replaced(self):
        await self.db.execute("INSERT INTO tickets VALUES (42, 98)")
        await self.db.commit()

        await self.click(self.interaction())

        self.assertEqual(
            await self.db.execute_fetchall("SELECT user_id, channel_id FROM tickets"),
            [(42, 99)],
        )

    async def test_missing_resource_stops_before_channel_creation(self):
        del self.resources[2]
        interaction = self.interaction()

        await self.click(interaction)

        self.guild.create_text_channel.assert_not_awaited()
        self.assertIn("missing or invalid", interaction.followup.send.await_args.args[0])

    async def test_failed_setup_removes_created_channel_role_and_mapping(self):
        self.created.send.side_effect = [None, RuntimeError("send failed")]

        with self.assertLogs("cogs.applications", level="ERROR"):
            await self.click(self.interaction())

        self.member.remove_roles.assert_awaited_once()
        self.created.delete.assert_awaited_once()
        self.assertEqual(
            await self.db.execute_fetchall("SELECT user_id, channel_id FROM tickets"), []
        )

    async def test_panel_uses_configured_server_name(self):
        ctx = SimpleNamespace(send=AsyncMock())
        cog = Applications(self.bot)

        await Applications.setup_applications.callback(cog, ctx)

        self.assertEqual(
            ctx.send.await_args.kwargs["embed"].title, "Example Server Applications"
        )


if __name__ == "__main__":
    unittest.main()
