import discord
from discord import app_commands
from discord.ext import commands

class Dispatch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="auto_dispatch", description="Auto dispatch loads")
    async def auto_dispatch(self, interaction: discord.Interaction):
        await interaction.response.defer()
        res = await self.bot.api.auto_dispatch()
        assignments = res.get("assignments", [])
        if not assignments:
            await interaction.followup.send("No loads to dispatch.")
        else:
            await interaction.followup.send(f"Dispatched {len(assignments)} loads.")

async def setup(bot):
    await bot.add_cog(Dispatch(bot))
