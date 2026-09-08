from datetime import UTC, datetime
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock

import aiosqlite
import discord

from cogs.tickets import Tickets, transcript
from tests.common import config
from utils import migrate_tickets


class TicketTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = await aiosqlite.connect(":memory:")
        await migrate_tickets(self.db)
        await self.db.execute("INSERT INTO tickets VALUES (42, 99)")
        await self.db.commit()
        self.config = config()
        self.bot = SimpleNamespace(config=self.config, db=self.db)
        self.cog = Tickets(self.bot)
        self.cog._log = AsyncMock(return_value=None)

        self.channel = SimpleNamespace(id=99, delete=AsyncMock())
        self.general = SimpleNamespace(send=AsyncMock())
        self.applicant = object()
        self.member_role = object()
        self.guild = SimpleNamespace(
            get_channel=lambda channel_id: self.general if channel_id == 4 else None,
            get_role=lambda role_id: {6: self.applicant, 7: self.member_role}.get(role_id),
        )
        self.ctx = SimpleNamespace(
            guild=self.guild,
            channel=self.channel,
            author="moderator",
            defer=AsyncMock(),
            send=AsyncMock(),
        )

    async def asyncTearDown(self):
        await self.db.close()

    async def test_accept_deletes_mapping_only_after_required_operations(self):
        self.channel.delete.side_effect = RuntimeError("Discord failed")

        with self.assertRaisesRegex(RuntimeError, "Discord failed"):
            await Tickets.accept.callback(self.cog, self.ctx)

        self.ctx.defer.assert_awaited_once_with(ephemeral=True)
        self.assertEqual(
            await self.db.execute_fetchall("SELECT user_id, channel_id FROM tickets"),
            [(42, 99)],
        )

    async def test_accept_fetches_uncached_resources(self):
        self.guild.get_channel = lambda _: None
        self.guild.get_role = lambda _: None
        self.guild.fetch_channel = AsyncMock(return_value=self.general)
        self.guild.fetch_roles = AsyncMock(
            side_effect=[
                [SimpleNamespace(id=6)],
                [SimpleNamespace(id=7)],
            ]
        )

        await Tickets.accept.callback(self.cog, self.ctx)

        self.guild.fetch_channel.assert_awaited_once_with(4)
        self.assertEqual(self.guild.fetch_roles.await_count, 2)

    async def test_deny_deletes_mapping_after_success(self):
        await Tickets.deny.callback(self.cog, self.ctx, reason="Incomplete")
        self.assertEqual(
            await self.db.execute_fetchall("SELECT user_id, channel_id FROM tickets"), []
        )

    async def test_deny_keeps_mapping_when_logging_fails(self):
        self.cog._log.side_effect = RuntimeError("log failed")
        with self.assertRaisesRegex(RuntimeError, "log failed"):
            await Tickets.deny.callback(self.cog, self.ctx)
        self.assertEqual(
            await self.db.execute_fetchall("SELECT user_id, channel_id FROM tickets"),
            [(42, 99)],
        )

    async def test_transcript_is_chronological_with_timestamps_and_attachments(self):
        author = MagicMock()
        author.__str__.return_value = "Player"
        author.id = 42
        messages = [
            SimpleNamespace(
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                author=author,
                content="First",
                attachments=[],
            ),
            SimpleNamespace(
                created_at=datetime(2026, 1, 2, tzinfo=UTC),
                author=author,
                content="Second",
                attachments=[SimpleNamespace(url="https://cdn.example/file.png")],
            ),
        ]

        async def history(**kwargs):
            self.assertEqual(kwargs, {"limit": None, "oldest_first": True})
            for message in messages:
                yield message

        data = (await transcript(SimpleNamespace(history=history))).decode()
        self.assertLess(data.index("First"), data.index("Second"))
        self.assertIn("2026-01-01T00:00:00+00:00", data)
        self.assertIn("https://cdn.example/file.png", data)


if __name__ == "__main__":
    unittest.main()
