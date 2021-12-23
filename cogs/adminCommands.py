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
            
            file = discord.File(fp=buffer, filename=f"{message.guild.id}-{message.channel.id}.txt")

            applog = self.bot.get_channel(APP_LOG_CHANNEL) 
            await applog.send(file=file, embed = e)
            buffer.close()


            user_id = int(row[0][0])
            member = await get_or_fetch_member(self, ctx.guild, user_id)
            await member.remove_roles(discord.utils.get(ctx.guild.roles, name="Applicant"))
            await member.add_roles(discord.utils.get(ctx.guild.roles, name="Member"))
            await ctx.channel.delete()

            try:
                await member.send(f"Your application has been accepted by {ctx.author}! The server IP is `play.sleepless.community`.")
            except Exception as e:
                pass

            generalchat = self.bot.get_channel(GENERAL_CHAT)
            await generalchat.send(f"Welcome {member.mention}! Make sure to read <#{RULES_CHANNEL}>.")
            await self.bot.db.execute('DELETE FROM tickets WHERE channel_id = ?',(ctx.channel.id,))
            await self.bot.db.commit()
        else:
            await ctx.send("This isn't an application channel")

    @has_permissions(administrator=True)
    @commands.command()
    async def deny(self, ctx, *, reason: str = None):
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

            applog = self.bot.get_channel(APP_LOG_CHANNEL) 
            await applog.send(file=file, embed = e)
            buffer.close()

            await ctx.channel.delete()

            user_id = int(row[0][0])
            member = await get_or_fetch_member(self, ctx.guild, user_id)


            try:
                await member.send(f"Your application has been denied by {ctx.author}. Reason: `{reason}`")
            except Exception as e:
                pass

            await self.bot.db.execute('DELETE FROM tickets WHERE channel_id = ?',(ctx.channel.id,))
            await self.bot.db.commit()

        else:
            await ctx.send("This isn't an application channel")





def setup(bot):
    bot.add_cog(Admin(bot)) 