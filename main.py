import discord
from discord.ext import commands
from utils import setup

import logging
from dotenv import load_dotenv
import os
import aiosqlite
import asyncio

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

load_dotenv()

intents = discord.Intents.all()


bot = commands.Bot(
command_prefix="-", 
case_insensitive=True, 
intents=intents, 
allowed_mentions=discord.AllowedMentions(roles=True, users=True, everyone=False), 
activity=discord.Streaming(name=f"-help", url='https://www.twitch.tv/alexxwastakenlol'),
)

loop = asyncio.get_event_loop()
bot.db = loop.run_until_complete(aiosqlite.connect('apps.db'))
loop.create_task(setup(bot))




extensions = (
    "alexxOnly",
    "adminCommands",
    "events",
    "errors",
    "SMC-Master-Sheet.py",
    )

bot.load_extension("jishaku")
count = 0
for ext in extensions:
    bot.load_extension(f"cogs.{ext}")
    print(f'Loaded {ext}')
    count += 1

@bot.event
async def on_ready():
    await bot.wait_until_ready()
    print('--------------------------')
    print(f'Logged in as: {bot.user.name}')
    print(f'With ID: {bot.user.id}')
    print(f'{count} total extensions loaded')
    print(f"Servers - {str(len(bot.guilds))}")
    print('--------------------------')
    print('Bot is ready!')


TOKEN = os.getenv("DISCORD_TOKEN_SMCAPPS")
bot.run(TOKEN)
