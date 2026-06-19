import discord
from discord import app_commands
from discord.ext import commands

class Tracking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="track", description="Track a vehicle by unit ID")
    @app_commands.describe(unit_id="The unit ID to track")
    async def track(self, interaction: discord.Interaction, unit_id: str):
        await interaction.response.defer()
        try:
            res = await self.bot.api.track_vehicle(unit_id)
            embed = discord.Embed(title=f"Tracking {unit_id}", color=discord.Color.green() if res.get('status') == 'Driving' else discord.Color.orange())
            embed.add_field(name="Driver", value=res.get("driver"), inline=True)
            embed.add_field(name="Location", value=res.get("location"), inline=True)
            embed.add_field(name="Speed", value=f"{res.get('speed')} mph", inline=True)
            embed.add_field(name="Status", value=res.get("status"), inline=True)
            embed.add_field(name="HOS Remaining", value=f"{res.get('hos_remaining')} hrs", inline=True)
            await interaction.followup.send(embed=embed)
        except Exception:
            await interaction.followup.send(f"Could not track unit {unit_id}.")

async def setup(bot):
    await bot.add_cog(Tracking(bot))
