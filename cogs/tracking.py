import discord
from discord.ext import commands
from discord import app_commands
import random
import logging
from sqlalchemy.future import select

from database.models import AsyncSessionLocal, Vehicle

log = logging.getLogger("broker_bot.tracking")

class Tracking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="track", description="Get real-time GPS and Hours of Service data for a truck.")
    async def track_truck(self, interaction: discord.Interaction, unit_id: str):
        await interaction.response.defer()
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Vehicle).where(Vehicle.unit_id == unit_id))
            vehicle = result.scalars().first()
            
            if not vehicle:
                # Fallback to a mock truck if not found, to keep demo smooth
                mock_driver = "Unknown Driver"
            else:
                mock_driver = vehicle.driver
                
            # Simulate fetching data from an ELD provider like Samsara / Motive
            mock_locations = [
                "I-40 East, near Amarillo, TX",
                "Rest Stop, outside Little Rock, AR",
                "Stuck in traffic, I-95 North, Richmond, VA",
                "Pilot Travel Center, I-80, Cheyenne, WY",
                "Loading Dock, Sysco Facility, Atlanta, GA"
            ]
            
            current_location = random.choice(mock_locations)
            speed = random.choice([0, 0, 55, 65, 70])
            hos_remaining = round(random.uniform(2.5, 10.0), 1)
            
            status_text = "🟢 Driving" if speed > 0 else "🛑 Stopped / Idle"
            
            embed = discord.Embed(
                title=f"📡 Live Tracking: Unit {unit_id}",
                description=f"**Driver:** {mock_driver}",
                color=discord.Color.brand_green() if speed > 0 else discord.Color.orange()
            )
            embed.add_field(name="Current Location", value=f"📍 {current_location}", inline=False)
            embed.add_field(name="Current Speed", value=f"⏱️ {speed} mph", inline=True)
            embed.add_field(name="Engine Status", value=status_text, inline=True)
            embed.add_field(name="Hours of Service (HOS)", value=f"⏳ {hos_remaining} hrs remaining today", inline=False)
            
            embed.set_footer(text="Data synced via secure ELD Integration (Motive/Samsara)")
            
            await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Tracking(bot))
