import asyncio
from datetime import datetime
import logging

import discord
from discord.ext import commands
import gspread


log = logging.getLogger(__name__)


def ban_pages(rows: list[list[str]], page_size: int = 20) -> list[list[tuple[str, str]]]:
    entries = [
        (row[1][:256], row[2][:1024])
        for row in rows
        if len(row) >= 3 and row[1].strip()
    ]
    return [entries[index : index + page_size] for index in range(0, len(entries), page_size)] or [[]]


class SheetCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.worksheets = None

    def _open_worksheets(self):
        config = self.bot.config
        spreadsheet = gspread.service_account(
            filename=config.google_service_account_file
        ).open(config.google_spreadsheet_name)
        return {
            "bans": spreadsheet.worksheet(config.banned_players_worksheet),
            "payments": spreadsheet.worksheet(config.payments_worksheet),
            "discipline": spreadsheet.worksheet(config.discipline_worksheet),
            "finances": spreadsheet.worksheet(config.finances_worksheet),
        }

    async def _sheets(self, ctx: commands.Context):
        try:
            if self.worksheets is None:
                self.worksheets = await asyncio.to_thread(self._open_worksheets)
            return self.worksheets
        except Exception:
            log.exception("Could not open configured spreadsheet")
            await ctx.send("Google Sheets is unavailable. Check the bot logs.", ephemeral=True)
            return None

    @commands.hybrid_command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def banlist(self, ctx: commands.Context) -> None:
        """Show the configured ban list."""
        sheets = await self._sheets(ctx)
        if sheets is None:
            return
        try:
            rows = await asyncio.to_thread(sheets["bans"].get_all_values)
        except Exception:
            log.exception("Could not read ban list")
            await ctx.send("Could not read the ban list. Check the bot logs.", ephemeral=True)
            return
        pages = ban_pages(rows)
        for page_number, entries in enumerate(pages, 1):
            embed = discord.Embed(
                title=f"{self.bot.config.server_name} Banned Players",
                color=0x83E2E6,
            )
            if len(pages) > 1:
                embed.set_footer(text=f"Page {page_number} of {len(pages)}")
            if entries:
                for username, reason in entries:
                    embed.add_field(name=username, value=reason or "No reason provided", inline=False)
            else:
                embed.description = "No banned players."
            await ctx.send(embed=embed)

    @commands.hybrid_command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def ban(self, ctx: commands.Context, username: str, *, reason: str) -> None:
        """Add a player to the configured ban worksheet."""
        sheets = await self._sheets(ctx)
        if sheets is None:
            return
        try:
            await asyncio.to_thread(
                sheets["bans"].insert_row,
                [datetime.now().astimezone().isoformat(timespec="seconds"), username, reason],
                2,
            )
        except Exception:
            log.exception("Could not add ban")
            await ctx.send("Could not update the ban list. Check the bot logs.", ephemeral=True)
            return
        await ctx.send(f"{username} was added to the ban list.")

    @commands.hybrid_command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def discipline(self, ctx: commands.Context, username: str, amount: int) -> None:
        """Add discipline points for a player."""
        sheets = await self._sheets(ctx)
        if sheets is None:
            return
        try:
            await asyncio.to_thread(
                sheets["discipline"].insert_row,
                [datetime.now().astimezone().isoformat(timespec="seconds"), username, amount],
                2,
            )
        except Exception:
            log.exception("Could not add discipline points")
            await ctx.send("Could not update discipline. Check the bot logs.", ephemeral=True)
            return
        await ctx.send(f"Added {amount} discipline point(s) for {username}.")

    @commands.hybrid_command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def payment(self, ctx: commands.Context, username: str, amount: int) -> None:
        """Record an in-game payment."""
        sheets = await self._sheets(ctx)
        if sheets is None:
            return
        try:
            await asyncio.to_thread(
                sheets["payments"].insert_row, [username, amount], 2
            )
        except Exception:
            log.exception("Could not add payment")
            await ctx.send("Could not record the payment. Check the bot logs.", ephemeral=True)
            return
        await ctx.send(
            f"Recorded {username}'s payment of {amount} {self.bot.config.payment_unit}(s)."
        )

    @commands.hybrid_command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def donation(
        self, ctx: commands.Context, donor: str, amount: float, fee: float
    ) -> None:
        """Record a donation and its fee."""
        sheets = await self._sheets(ctx)
        if sheets is None:
            return

        def update() -> None:
            worksheet = sheets["finances"]
            row = len([value for value in worksheet.col_values(1) if value]) + 2
            worksheet.update(
                [[
                    datetime.now().astimezone().isoformat(timespec="seconds"),
                    f"Donation ({donor})",
                    amount,
                    fee,
                ]],
                f"A{row}:D{row}",
                value_input_option="USER_ENTERED",
            )

        try:
            await asyncio.to_thread(update)
        except Exception:
            log.exception("Could not add donation")
            await ctx.send("Could not record the donation. Check the bot logs.", ephemeral=True)
            return
        currency = self.bot.config.donation_currency
        await ctx.send(
            f"Recorded {donor}'s {currency}{amount:g} donation with a {currency}{fee:g} fee."
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SheetCommands(bot))
