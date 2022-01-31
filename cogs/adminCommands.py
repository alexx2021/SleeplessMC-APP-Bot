import discord
from discord.ext import commands
from discord.ext.commands.core import has_permissions
import io

from utils import get_or_fetch_member

APP_LOG_CHANNEL = 741054231821418581
GENERAL_CHAT = 919789640175718460
RULES_CHANNEL = 919741501733478421



class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @has_permissions(administrator=True)
    @commands.command()
    async def accept(self, ctx):

        try:
            row = await self.bot.db.execute_fetchall('SELECT * FROM tickets WHERE channel_id = ?',(ctx.channel.id,))
            if row:
                messages = await ctx.channel.history(limit=200).flatten()

                buffer = io.BytesIO()
                theContent = ''
                for message in messages:
                    theContent += f'{message.author} ({message.author.id}): {message.content}\n'
                buffer = io.BytesIO(theContent.encode("utf8"))
                
                e = discord.Embed(color=discord.Color.green(), title=f'{ctx.channel.name} Accepted')
                e.timestamp = discord.utils.utcnow()
                
                file = discord.File(fp=buffer, filename=f"{message.channel.id}.txt")

                user_id = int(row[0][0])
                member = await get_or_fetch_member(self, ctx.guild, user_id)

                applog = self.bot.get_channel(APP_LOG_CHANNEL) 
                await applog.send(file=file, embed = e)
                if member is not None:
                    await applog.send(f"Info to allow apps to be searchable on discord\nTag: {member}\nID: {member.id}")
                buffer.close()

                if member is not None:
                    await member.remove_roles(discord.utils.get(ctx.guild.roles, name="Applicant"))
                    await member.add_roles(discord.utils.get(ctx.guild.roles, name="Member"))
                await ctx.channel.delete()

                generalchat = self.bot.get_channel(GENERAL_CHAT)
                if member is not None:
                    await generalchat.send(f"Welcome to the server {member.mention}!")
                    await generalchat.send("The server IP is `play.sleepless.community`\nTo link your minecraft account to your discord account, follow the instructions given upon joining.",delete_after=300)

                try:
                    if member is not None:
                        await member.send(f"Your application has been accepted by {ctx.author}! The server IP is `play.sleepless.community`.")
                except Exception as e:
                    pass

            else:
                await ctx.send("This isn't an application channel")
        finally:
            await self.bot.db.execute('DELETE FROM tickets WHERE channel_id = ?',(ctx.channel.id,))
            await self.bot.db.commit()

    @has_permissions(administrator=True)
    @commands.command(aliases=['reject'])
    async def deny(self, ctx, *, reason: str = None):
        try:
            row = await self.bot.db.execute_fetchall('SELECT * FROM tickets WHERE channel_id = ?',(ctx.channel.id,))
            if row:
                messages = await ctx.channel.history(limit=200).flatten()

                buffer = io.BytesIO()
                theContent = ''
                for message in messages:
                    theContent += f'{message.author} ({message.author.id}): {message.content}\n'
                buffer = io.BytesIO(theContent.encode("utf8"))
                
                e = discord.Embed(color=discord.Color.red(), title=f'{ctx.channel.name} Denied')
                e.timestamp = discord.utils.utcnow()
                
                file = discord.File(fp=buffer, filename=f"{message.guild.id}-{message.channel.id}.txt")

                user_id = int(row[0][0])
                member = await get_or_fetch_member(self, ctx.guild, user_id)

                applog = self.bot.get_channel(APP_LOG_CHANNEL) 
                await applog.send(file=file, embed = e)
                if member is not None:
                    await applog.send(f"Info to allow apps to be searchable on discord\nTag: {member}\nID: {member.id}")
                buffer.close()

                await ctx.channel.delete()


                try:
                    if member is not None:
                        await member.send(f"Your application has been denied by {ctx.author}. Reason: `{reason}`")
                        await ctx.guild.kick(member, reason="Application denied")
                except Exception as e:
                    pass

            else:
                await ctx.send("This isn't an application channel")
        finally:
            await self.bot.db.execute('DELETE FROM tickets WHERE channel_id = ?',(ctx.channel.id,))
            await self.bot.db.commit()





def setup(bot):
    bot.add_cog(Admin(bot))