from discord.ext import commands

class DriverPortal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.attachments or not message.content.strip():
            return
            
        # Hardcoding dummy load_id for demo purposes
        load_id = "UNKNOWN"
        res = await self.bot.api.update_load_status(load_id, message.content, str(message.author.id))
        if res.get("status") == "ok":
            await message.add_reaction("✅")

async def setup(bot):
    await bot.add_cog(DriverPortal(bot))
