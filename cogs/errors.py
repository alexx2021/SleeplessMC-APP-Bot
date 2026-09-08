import logging

from discord.ext import commands


log = logging.getLogger(__name__)


class Errors(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        error = getattr(error, "original", error)
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"Missing required arguments. Usage: `{ctx.command} {ctx.command.signature}`"
            )
            return
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Administrator permission is required.", ephemeral=True)
            return
        if isinstance(error, commands.NotOwner):
            return
        if isinstance(error, commands.CheckFailure):
            await ctx.send("This command is not available here.", ephemeral=True)
            return
        if isinstance(error, (commands.BadArgument, commands.UserInputError)):
            await ctx.send(f"Invalid command arguments: {error}", ephemeral=True)
            return
        log.error("Command %s failed", ctx.command, exc_info=error)
        await ctx.send("The command failed. Check the bot logs.", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Errors(bot))
