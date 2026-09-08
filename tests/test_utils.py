from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock

import discord

from utils import get_or_fetch_channel, get_or_fetch_role


class LookupTests(IsolatedAsyncioTestCase):
    async def test_cached_channel_does_not_fetch(self):
        guild = MagicMock(spec=discord.Guild)
        channel = MagicMock(spec=discord.TextChannel)
        guild.get_channel.return_value = channel

        self.assertIs(await get_or_fetch_channel(guild, 1), channel)
        guild.fetch_channel.assert_not_awaited()

    async def test_missing_channel_returns_none(self):
        guild = MagicMock(spec=discord.Guild)
        guild.get_channel.return_value = None
        guild.fetch_channel = AsyncMock(
            side_effect=discord.NotFound(MagicMock(status=404), "missing")
        )

        self.assertIsNone(await get_or_fetch_channel(guild, 1))
        guild.fetch_channel.assert_awaited_once_with(1)

    async def test_uncached_channel_fetches_once(self):
        guild = MagicMock(spec=discord.Guild)
        guild.get_channel.return_value = None
        channel = MagicMock(spec=discord.TextChannel)
        guild.fetch_channel = AsyncMock(return_value=channel)

        self.assertIs(await get_or_fetch_channel(guild, 1), channel)
        guild.fetch_channel.assert_awaited_once_with(1)

    async def test_uncached_role_fetches_once_and_finds_role(self):
        guild = MagicMock(spec=discord.Guild)
        guild.get_role.return_value = None
        role = MagicMock(spec=discord.Role)
        role.id = 7
        guild.fetch_roles = AsyncMock(return_value=[role])

        self.assertIs(await get_or_fetch_role(guild, 7), role)
        guild.fetch_roles.assert_awaited_once_with()

    async def test_cached_role_does_not_fetch(self):
        guild = MagicMock(spec=discord.Guild)
        role = MagicMock(spec=discord.Role)
        guild.get_role.return_value = role

        self.assertIs(await get_or_fetch_role(guild, 7), role)
        guild.fetch_roles.assert_not_awaited()

    async def test_missing_role_returns_none(self):
        guild = MagicMock(spec=discord.Guild)
        guild.get_role.return_value = None
        guild.fetch_roles = AsyncMock(return_value=[])

        self.assertIsNone(await get_or_fetch_role(guild, 7))
