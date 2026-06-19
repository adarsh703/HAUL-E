from discord.ext import commands

class DocumentOCR(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.attachments:
            return
            
        attachment = message.attachments[0]
        if attachment.content_type and ('image' in attachment.content_type or 'pdf' in attachment.content_type):
            await message.add_reaction("📄")
            res = await self.bot.api.submit_document(attachment.url, attachment.filename, str(message.author.id), message.content)
            if res.get("status") == "ok":
                import discord
                embed = discord.Embed(title="✅ Load Auto-Created via OCR", color=0x10B981)
                embed.add_field(name="Load ID", value=res.get("load_id", "Unknown"), inline=True)
                embed.add_field(name="Route", value=f"{res.get('origin', 'N/A')} ➔ {res.get('destination', 'N/A')}", inline=False)
                embed.add_field(name="Rate", value=f"${res.get('rate', 0):,.2f}", inline=True)
                embed.set_footer(text="HAUL-E System • The load is now available on the Web Dashboard")
                await message.channel.send(embed=embed)
            else:
                await message.channel.send(f"❌ Failed to parse document: {res.get('message', 'Unknown Error')}")

async def setup(bot):
    await bot.add_cog(DocumentOCR(bot))
