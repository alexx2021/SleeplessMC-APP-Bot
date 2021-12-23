import discord

async def setup(bot):
    await bot.db.execute("CREATE TABLE IF NOT EXISTS tickets(user_id INTERGER, channel_id INTERGER)")
    pass

async def delete_global_commands(bot):
# Delete all global commands
    await bot.http.bulk_upsert_global_commands(bot.application_id, [])

async def delete_local_commands(bot, GUILD_ID):
# Delete from guilds
    await bot.http.bulk_upsert_guild_commands(bot.application_id, GUILD_ID, [])

async def get_or_fetch_member(self, guild, member_id): #from r danny :)
    """Only queries API if the member is not in cache."""
    member = guild.get_member(int(member_id))
    if member is not None:
        return member

    try:
        member = await guild.fetch_member(int(member_id))
    except discord.HTTPException:
        return None
    else:
        return member