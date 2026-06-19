import discord
from discord import app_commands
from discord.ext import commands
import logging
from google import genai
from google.genai import types
import json
import os
import random
from database.models import AsyncSessionLocal, OperationalTask, Load

from google.oauth2 import service_account

log = logging.getLogger("broker_bot.conversational_llm")

_VERTEX_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

class ConversationalLLM(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        creds_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "google_credentials.json")
        creds = service_account.Credentials.from_service_account_file(
            creds_file, scopes=_VERTEX_SCOPES
        )
        self.gemini_client = genai.Client(
            vertexai=True,
            project=os.getenv("GOOGLE_PROJECT_ID"),
            location=os.getenv("GOOGLE_LOCATION"),
            credentials=creds,
        )
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    @app_commands.command(name="loads", description="Fetches all active loads from the database")
    async def fetch_loads(self, interaction: discord.Interaction):
        await interaction.response.defer()
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            result = await session.execute(select(Load))
            all_loads = result.scalars().all()
            
            if not all_loads:
                await interaction.followup.send("📭 No active loads found in the database.")
                return
            
            embed = discord.Embed(title="🚛 Active Loads", color=discord.Color.blurple())
            for load in all_loads:
                embed.add_field(
                    name=f"{load.load_id} - {load.status}",
                    value=f"**Route:** {load.origin_dest}\n**Date:** {load.pickup_date}\n**Rate:** {load.rate}\n**Driver:** {load.driver}",
                    inline=False
                )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="create_load", description="Create a new load via natural language instructions")
    @app_commands.describe(instruction="E.g., 'New load from Austin to Miami picking up tomorrow for $4000'")
    async def create_load_command(self, interaction: discord.Interaction, instruction: str):
        await interaction.response.defer()
        prompt = f"""You are an autonomous Operations Assistant for a logistics company.
Read the user's message and extract structured data to create a shipment.
Return a JSON object with the following structure:
{{
    "extracted_data": {{
        "origin": "string (city/state) or Unknown",
        "destination": "string (city/state) or Unknown",
        "pickup_date": "string or Unknown",
        "rate": "string (just the number/amount) or 0",
        "driver": "string or Unassigned"
    }}
}}

User Message: {instruction}
"""
        try:
            response = await self.gemini_client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            data = json.loads(response.text)
            extracted = data.get("extracted_data", {})
            
            load_id = f"#L-{random.randint(1000, 9999)}"
            origin_dest = f"{extracted.get('origin', 'Unknown')} → {extracted.get('destination', 'Unknown')}"
            
            # Save load to database
            async with AsyncSessionLocal() as session:
                new_load = Load(
                    load_id=load_id,
                    origin_dest=origin_dest,
                    pickup_date=extracted.get('pickup_date', 'Unknown'),
                    driver=extracted.get('driver', 'Unassigned'),
                    rate=str(extracted.get('rate', '0')),
                    status='Pending'
                )
                session.add(new_load)
                
                new_task = OperationalTask(
                    task_type="NEW_LOAD_AI",
                    description=f"AI parsed load from /create_load: {load_id} ({origin_dest})"
                )
                session.add(new_task)
                await session.commit()
            
            embed = discord.Embed(title="✅ New Load Created", description="Successfully parsed and added the load to the TMS.", color=discord.Color.green())
            embed.add_field(name="Load ID", value=load_id, inline=True)
            embed.add_field(name="Route", value=origin_dest, inline=True)
            embed.add_field(name="Date", value=extracted.get('pickup_date', 'Unknown'), inline=True)
            embed.add_field(name="Rate", value=f"${extracted.get('rate', '0')}", inline=True)
            embed.set_footer(text="The website has been automatically updated.")
            
            await interaction.followup.send(embed=embed)
        except Exception as e:
            log.error(f"Error processing natural language for slash command: {e}", exc_info=True)
            await interaction.followup.send("Sorry, I encountered an error trying to process that load creation.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Check if the bot was mentioned
        if self.bot.user in message.mentions:
            # Show typing indicator
            async with message.channel.typing():
                # Fetch all loads from DB to provide context to the LLM
                context_str = "Current TMS Database Context:\n"
                try:
                    async with AsyncSessionLocal() as session:
                        from sqlalchemy import select
                        result = await session.execute(select(Load))
                        all_loads = result.scalars().all()
                        
                        if all_loads:
                            for load in all_loads:
                                context_str += f"Load {load.load_id}: Route={load.origin_dest}, Date={load.pickup_date}, Status={load.status}, Driver={load.driver}, Rate={load.rate}\n"
                        else:
                            context_str += "No active loads in the database right now.\n"
                except Exception as e:
                    log.error(f"Error fetching loads for context: {e}")
                    context_str += "Error connecting to database.\n"
                
                # Remove the bot mention from the user's message
                clean_content = message.clean_content.replace(f"@{self.bot.user.display_name}", "").strip()
                
                prompt = f"""You are HAUL-E, an intelligent, helpful, and highly capable personal assistant for Mor Logistics dispatchers and brokers.
You have direct access to the TMS database. Answer the user's question clearly, concisely, and professionally.
Here is the current state of the database:
{context_str}

User Question: {clean_content}
"""
                try:
                    response = await self.gemini_client.aio.models.generate_content(
                        model=self.model,
                        contents=prompt
                    )
                    await message.reply(response.text)
                except Exception as e:
                    log.error(f"Error generating LLM reply: {e}", exc_info=True)
                    await message.reply("Sorry, I'm having trouble thinking right now.")

async def setup(bot: commands.Bot):
    await bot.add_cog(ConversationalLLM(bot))
