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
        for role_id, role in self.roles.items():
            role.id = role_id
        self.guild = MagicMock(spec=discord.Guild)
        self.guild.id = 1
        self.guild.default_role = MagicMock(spec=discord.Role)
        self.guild.get_channel.side_effect = self.resources.get
        self.guild.get_role.side_effect = self.roles.get
        self.guild.fetch_channel.return_value = None
        self.guild.fetch_roles.return_value = []
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

    async def test_uncached_resources_are_fetched(self):
        self.guild.get_channel.side_effect = lambda _: None
        self.guild.fetch_channel.side_effect = self.resources.get
        self.guild.get_role.side_effect = lambda _: None
        self.guild.fetch_roles.return_value = list(self.roles.values())

        await self.click(self.interaction())

        self.guild.fetch_channel.assert_any_await(2)
        self.guild.fetch_channel.assert_any_await(3)
        self.guild.fetch_channel.assert_any_await(4)
        self.guild.fetch_channel.assert_any_await(5)
        self.assertEqual(self.guild.fetch_roles.await_count, 2)
        self.guild.create_text_channel.assert_awaited_once()

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

    async def test_member_permissions_setup_reports_results_and_preserves_overwrites(self):
        default_role = self.guild.default_role
        default_role.id = 1
        member_role = self.roles[7]
        member_role.id = 7
        applicant = MagicMock(spec=discord.Member)
        applicant.id = 42

        def channel(name, channel_id, visible=True, overwrites=None):
            result = MagicMock(spec=discord.TextChannel)
            result.name = name
            result.id = channel_id
            result.permissions_for.return_value = SimpleNamespace(view_channel=visible)
            result.overwrites = overwrites or {}
            result.overwrites_for.side_effect = lambda target: result.overwrites.get(
                target, discord.PermissionOverwrite()
            )
            result.set_permissions = AsyncMock()
            return result

        panel = channel("applications", 10)
        open_channel = channel(
            "open",
            11,
            overwrites={
                default_role: discord.PermissionOverwrite(send_messages=False),
                member_role: discord.PermissionOverwrite(send_messages=False),
                applicant: discord.PermissionOverwrite(view_channel=True),
            },
        )
        denied = channel("private", 12, visible=False)
        failed = channel("broken", 13)
        failed.set_permissions.side_effect = RuntimeError("Discord failed")
        self.guild.fetch_channels.return_value = [panel, open_channel, denied, failed]
        ctx = SimpleNamespace(
            guild=self.guild, channel=panel, author="moderator", send=AsyncMock()
        )

        with self.assertLogs("cogs.applications", level="ERROR"):
            await Applications.setup_member_permissions.callback(
                Applications(self.bot), ctx
            )

        self.guild.fetch_channels.assert_awaited_once_with()
        self.assertEqual(open_channel.set_permissions.await_count, 2)
        targets = [call.args[0] for call in open_channel.set_permissions.await_args_list]
        self.assertEqual(targets, [default_role, member_role])
        self.assertFalse(
            open_channel.set_permissions.await_args_list[0].kwargs["overwrite"].view_channel
        )
        self.assertFalse(
            open_channel.set_permissions.await_args_list[0].kwargs["overwrite"].send_messages
        )
        self.assertTrue(open_channel.overwrites[applicant].view_channel)
        self.assertTrue(
            open_channel.set_permissions.await_args_list[1].kwargs["overwrite"].view_channel
        )
        self.assertEqual(denied.set_permissions.await_count, 0)
        self.assertEqual(panel.set_permissions.await_count, 0)
        self.assertEqual(failed.set_permissions.await_count, 1)
        response = "\n".join(call.args[0] for call in ctx.send.await_args_list)
        self.assertIn("open (11)", response)
        self.assertIn("applications (10)", response)
        self.assertIn("private (12)", response)
        self.assertIn("broken (13)", response)
        self.assertIn("Failures (1)", response)
        self.assertIn("Possible exceptions", response)


if __name__ == "__main__":
    unittest.main()
