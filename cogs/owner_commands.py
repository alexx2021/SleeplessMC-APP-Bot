from discord.ext import commands


class OwnerCommands(commands.Cog, command_attrs={"hidden": True}):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command()
    @commands.is_owner()
    async def leave(self, ctx: commands.Context, guild_id: int) -> None:
        """Make the bot leave a guild."""
        await ctx.defer(ephemeral=True)
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            await ctx.send("That guild is not available.", ephemeral=True)
            return
        await guild.leave()
        await ctx.send(f"Left {guild} (`{guild.id}`).", ephemeral=True)

    @commands.hybrid_command()
    @commands.is_owner()
    async def listguilds(self, ctx: commands.Context) -> None:
        """List guilds visible to the bot."""
        await ctx.send(
            "\n".join(f"{guild} - {guild.id}" for guild in self.bot.guilds)
            or "No guilds.",
            ephemeral=True,
        )

    @commands.hybrid_command()
    @commands.is_owner()
    async def dumpdb(self, ctx: commands.Context) -> None:
        """Show current ticket mappings."""
        rows = await self.bot.db.execute_fetchall(
            "SELECT user_id, channel_id FROM tickets ORDER BY user_id"
        )
        await ctx.send(str(rows), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OwnerCommands(bot))
