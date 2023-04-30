import asyncio
import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
from bot.elevenlabs_utils import set_api_key

load_dotenv()
set_api_key(os.getenv('API_KEY'))

intents = discord.Intents.default()

bot = commands.Bot(command_prefix='?', intents=intents)
discord.utils.setup_logging()


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

    await bot.tree.sync()


async def load_extensions():
    for filename in os.listdir("./bot/cogs"):
        if filename.endswith(".py") and filename != "__init__.py":
            await bot.load_extension(f"bot.cogs.{filename[:-3]}")

# Load cogs


async def main():
    async with bot:
        await load_extensions()
        await bot.start(os.getenv('BOT_TOKEN'))

asyncio.run(main())
