from discord.ext import commands
from discord.raw_models import RawReactionActionEvent
import discord
from utils import get_or_fetch_member

REACTION_MESSAGE_ID = 923689289764728862


class Events(commands.Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot):
        self.bot = bot    

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):   
        if payload.message_id == REACTION_MESSAGE_ID:
            row = await self.bot.db.execute_fetchall('SELECT channel_id FROM tickets WHERE user_id = ?',(payload.user_id,))
            if row:
                pass
                #print("User already has a ticket open")
            else:
                guild = self.bot.get_guild(payload.guild_id)
                user = self.bot.get_user(payload.user_id)
                category=discord.utils.get(guild.categories, name="applications")
                overwrites = ""
                member = await get_or_fetch_member(self, guild, payload.user_id)

                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    member: discord.PermissionOverwrite(read_messages=True),
                }

                channel = await guild.create_text_channel(f'app-{user.name}', category=category, overwrites=overwrites)
                await channel.send(f"{member.mention} please answer the following questions in this channel.\n\n1. What is your Minecraft username?\n2. How old are you?\n3. How did you find out about the server (reddit, a friend, a discord server, etc)?\n4. Share a fun fact about yourself.\n5. How often do you play MC and what is your playstyle?\n6. Why would you like to play on our server?\n\nFeel free to attach pictures of previous builds/farms you have made before! We would love to see them! \n\nPlease also repeat this sentence to signify your agreement and understanding of the rules in the <#919741501733478421> channel.\n\"I have read and understood the rules and ignorance is not an excuse for breaking them.\"")
                
                await self.bot.db.execute('INSERT INTO tickets VALUES (?,?)', (payload.user_id, channel.id))
                await self.bot.db.commit()

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        
        if member == self.bot.user:
            return
        row = await self.bot.db.execute_fetchall('SELECT channel_id FROM tickets WHERE user_id = ?',(member.id,))
        if row:
            channel = self.bot.get_channel(int(row[0][0]))
            await self.bot.db.execute('DELETE FROM tickets WHERE channel_id = ?',(channel.id,))
            await self.bot.db.commit()
            await channel.delete()
        else:
            pass






def setup(bot):
    bot.add_cog(Events(bot))