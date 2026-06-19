import discord
from discord.ext import commands
from api_client import APIClient
import os
from dotenv import load_dotenv

load_dotenv()

class BrokerBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.api = APIClient()

    async def setup_hook(self):
        cogs = ['cogs.document_ocr', 'cogs.driver_portal', 'cogs.onboarding', 'cogs.dispatch', 'cogs.tracking']
        for cog in cogs:
            await self.load_extension(cog)
        await self.tree.sync()

    async def close(self):
        await self.api.close()
        await super().close()

bot = BrokerBot()

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
