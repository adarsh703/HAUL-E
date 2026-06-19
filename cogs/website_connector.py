import discord
from discord.ext import commands, tasks
import logging
from sqlalchemy.future import select
from database.models import AsyncSessionLocal, OperationalTask

log = logging.getLogger("broker_bot.website_connector")

class WebsiteConnector(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.poll_website_tasks.start()

    def cog_unload(self):
        self.poll_website_tasks.cancel()

    @tasks.loop(seconds=5)
    async def poll_website_tasks(self):
        await self.bot.wait_until_ready()
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(OperationalTask).where(OperationalTask.status == 'PENDING', OperationalTask.task_type == 'NEW_LOAD')
            )
            tasks_list = result.scalars().all()
            
            if tasks_list:
                # Find a text channel
                channel = None
                for guild in self.bot.guilds:
                    for c in guild.text_channels:
                        if c.permissions_for(guild.me).send_messages:
                            channel = c
                            break
                    if channel:
                        break
                
                if channel:
                    for t in tasks_list:
                        embed = discord.Embed(
                            title="🚀 Website Connector",
                            description=t.description,
                            color=discord.Color.brand_green()
                        )
                        await channel.send(embed=embed)
                        t.status = 'COMPLETED'
                        
                    await session.commit()

async def setup(bot: commands.Bot):
    await bot.add_cog(WebsiteConnector(bot))
