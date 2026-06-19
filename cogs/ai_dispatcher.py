import discord
from discord.ext import commands
from discord import app_commands
import logging
from sqlalchemy.future import select

from database.models import AsyncSessionLocal, Load, Vehicle

log = logging.getLogger("broker_bot.ai_dispatcher")

class AIDispatcher(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="auto_dispatch", description="Automatically match pending loads to available trucks based on profitability.")
    async def auto_dispatch(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        async with AsyncSessionLocal() as session:
            # Get pending loads
            result = await session.execute(select(Load).where(Load.status == 'Pending'))
            pending_loads = result.scalars().all()
            
            # Get active vehicles
            v_result = await session.execute(select(Vehicle).where(Vehicle.status == 'Active'))
            active_vehicles = v_result.scalars().all()
            
            if not pending_loads:
                await interaction.followup.send("No pending loads to dispatch.")
                return
            if not active_vehicles:
                await interaction.followup.send("No active trucks available for dispatch.")
                return

            dispatched_count = 0
            messages = []
            
            for load in pending_loads:
                # Basic mock profit logic
                rate_num = float(load.rate.replace(',', '').replace('$', '')) if load.rate else 0
                # A simple rule: if rate > 3000, consider it highly profitable
                if rate_num > 3000:
                    # Pick an available truck (just picking the first one for this demo)
                    truck = active_vehicles[dispatched_count % len(active_vehicles)]
                    
                    # Dispatch
                    load.driver = truck.driver
                    load.status = 'Dispatched'
                    dispatched_count += 1
                    
                    messages.append(f"✅ **{load.load_id}** ({load.origin_dest}) - ${rate_num} assigned to **{truck.driver}** (Truck {truck.unit_id})")

            if dispatched_count > 0:
                await session.commit()
                response_text = f"🚀 **AI Dispatch Complete!** Successfully dispatched {dispatched_count} loads:\n\n" + "\n".join(messages)
            else:
                response_text = "🤖 **AI Dispatch Complete!** Evaluated loads but none met the high-profit threshold (> $3000) for auto-dispatch. Consider negotiating better rates."

            await interaction.followup.send(response_text)

async def setup(bot: commands.Bot):
    await bot.add_cog(AIDispatcher(bot))
