import asyncio
from discord.ext import commands




class Alexx(commands.Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot):
        self.bot = bot

    @commands.is_owner()
    @commands.command(hidden=False, help="only alex can use this")
    async def leave(self, ctx, GUILD_ID: int):
        guild = self.bot.get_guild(GUILD_ID)

        if (guild.id != 812951618945286185) and (guild is not None):
            await guild.leave()
            await ctx.send(f"ok - left {guild} - {guild.id}")

    @commands.is_owner()
    @commands.command(hidden=False, help="only alex can use this")
    async def listguilds(self, ctx):
        for guild in self.bot.guilds:
                await asyncio.sleep(1)
                await ctx.send(f"{guild} - {guild.id}")
        await ctx.send("Finished loop.")

    @commands.is_owner()
    @commands.command(hidden=False, help="only alex can use this")
    async def dumpdb(self, ctx):
        row = await self.bot.db.execute_fetchall('SELECT * FROM tickets')
        await ctx.send(row)





def setup(bot):
    bot.add_cog(Alexx(bot)) 