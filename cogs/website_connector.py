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
                select(OperationalTask).where(
                    OperationalTask.status == 'PENDING',
                    OperationalTask.task_type.in_(['NEW_LOAD', 'INVOICE_APPROVAL'])
                )
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
                        if t.task_type == 'NEW_LOAD':
                            embed = discord.Embed(
                                title="🚀 Website Connector",
                                description=t.description,
                                color=discord.Color.brand_green()
                            )
                            await channel.send(embed=embed)
                        
                        elif t.task_type == 'INVOICE_APPROVAL':
                            from database.models import Load
                            result_load = await session.execute(select(Load).where(Load.load_id == t.reference_id))
                            load = result_load.scalars().first()
                            if load and load.bol_path and load.pod_path:
                                from utils.invoice_generator import generate_invoice
                                from cogs.driver_portal import InvoiceApprovalView
                                import os
                                
                                pdf_path = generate_invoice(
                                    load_id=load.load_id,
                                    broker_name=load.broker_email or "Broker",
                                    origin_dest=load.origin_dest,
                                    rate=load.rate,
                                    date=load.pickup_date
                                )
                                
                                notify_email = os.getenv('GMAIL_USER', 'cavemann177@gmail.com')
                                final_bol = load.bol_path if load.bol_path else load.pod_path
                                view = InvoiceApprovalView(load.load_id, pdf_path, final_bol, notify_email)
                                
                                await channel.send(
                                    f"💸 **Invoice generated for Load #{load.load_id}!**\n"
                                    f"Should I email this invoice to `{notify_email}`?",
                                    file=discord.File(pdf_path),
                                    view=view
                                )
                                
                        t.status = 'COMPLETED'
                        
                    await session.commit()

async def setup(bot: commands.Bot):
    await bot.add_cog(WebsiteConnector(bot))
