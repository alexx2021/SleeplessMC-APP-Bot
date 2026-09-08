import io
import logging

import discord
from discord.ext import commands

from utils import get_or_fetch_member


log = logging.getLogger(__name__)


async def transcript(channel: discord.TextChannel) -> bytes:
    lines = []
    async for message in channel.history(limit=None, oldest_first=True):
        timestamp = message.created_at.isoformat()
        lines.append(
            f"[{timestamp}] {message.author} ({message.author.id}): {message.content}"
        )
        lines.extend(
            f"  [attachment] {attachment.url}" for attachment in message.attachments
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None and ctx.guild.id == self.bot.config.guild_id

    async def _ticket(self, ctx: commands.Context) -> int | None:
        if ctx.guild is None:
            return None
        row = await self.bot.db.execute_fetchall(
            "SELECT user_id FROM tickets WHERE channel_id = ?", (ctx.channel.id,)
        )
        if not row:
            await ctx.send("This is not an application channel.", ephemeral=True)
            return None
        return row[0][0]

    async def _log(
        self,
        ctx: commands.Context,
        user_id: int,
        outcome: str,
        color: discord.Color,
    ) -> discord.Member | None:
        config = self.bot.config
        log_channel = ctx.guild.get_channel(config.app_log_channel_id)
        if log_channel is None:
            await ctx.send(
                "The configured application log channel is missing.", ephemeral=True
            )
            raise commands.CommandError("Missing application log channel")

        member = await get_or_fetch_member(ctx.guild, user_id)
        data = await transcript(ctx.channel)
        embed = discord.Embed(
            color=color,
            title=f"{ctx.channel.name} {outcome}",
            timestamp=discord.utils.utcnow(),
        )
        if member is not None:
            embed.description = f"Applicant: {member} (`{member.id}`)"
        await log_channel.send(
            embed=embed,
            file=discord.File(io.BytesIO(data), filename=f"{ctx.channel.id}.txt"),
        )
        return member

    @commands.hybrid_command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def accept(self, ctx: commands.Context) -> None:
        """Accept the application in the current channel."""
        user_id = await self._ticket(ctx)
        if user_id is None:
            return
        config = self.bot.config
        general = ctx.guild.get_channel(config.general_channel_id)
        applicant = ctx.guild.get_role(config.applicant_role_id)
        member_role = ctx.guild.get_role(config.member_role_id)
        missing = [
            name
            for name, resource in (
                ("general channel", general),
                ("applicant role", applicant),
                ("member role", member_role),
            )
            if resource is None
        ]
        if missing:
            await ctx.send(
                f"Cannot accept: missing {', '.join(missing)}.", ephemeral=True
            )
            return

        member = await self._log(ctx, user_id, "Accepted", discord.Color.green())
        if member is not None:
            await member.remove_roles(applicant, reason=f"Accepted by {ctx.author}")
            await member.add_roles(member_role, reason=f"Accepted by {ctx.author}")
            await general.send(config.welcome_message(member.mention))
            try:
                await member.send(config.acceptance_message(str(ctx.author)))
            except discord.HTTPException:
                log.info("Could not DM accepted applicant %s", member.id)
        await ctx.channel.delete(reason=f"Application accepted by {ctx.author}")
        await self.bot.db.execute(
            "DELETE FROM tickets WHERE channel_id = ?", (ctx.channel.id,)
        )
        await self.bot.db.commit()

    @commands.hybrid_command(aliases=["reject"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def deny(self, ctx: commands.Context, *, reason: str | None = None) -> None:
        """Deny the application in the current channel."""
        user_id = await self._ticket(ctx)
        if user_id is None:
            return
        member = await self._log(ctx, user_id, "Denied", discord.Color.red())
        if member is not None:
            try:
                await member.send(
                    f"Your application to {self.bot.config.server_name} was denied by "
                    f"{ctx.author}. Reason: {reason or 'No reason provided.'}"
                )
            except discord.HTTPException:
                log.info("Could not DM denied applicant %s", member.id)
        await ctx.channel.delete(reason=f"Application denied by {ctx.author}")
        await self.bot.db.execute(
            "DELETE FROM tickets WHERE channel_id = ?", (ctx.channel.id,)
        )
        await self.bot.db.commit()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Tickets(bot))
