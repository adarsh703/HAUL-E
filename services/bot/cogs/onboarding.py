import discord
from discord import app_commands
from discord.ext import commands

class OnboardingModal(discord.ui.Modal, title="Company Onboarding"):
    company_name = discord.ui.TextInput(label="Company Name")
    mc_number = discord.ui.TextInput(label="MC Number")
    eld_provider = discord.ui.TextInput(label="ELD Provider", required=False)
    accounting = discord.ui.TextInput(label="Accounting Software", required=False)

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        data = {
            "company_name": self.company_name.value,
            "mc_number": self.mc_number.value,
            "eld_provider": self.eld_provider.value,
            "accounting_software": self.accounting.value,
            "discord_user_id": str(interaction.user.id)
        }
        await self.bot.api.submit_onboarding(data)
        await interaction.response.send_message("Company profile created!", ephemeral=True)

class Onboarding(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="onboard", description="Create a company profile")
    async def onboard(self, interaction: discord.Interaction):
        await interaction.response.send_modal(OnboardingModal(self.bot))

async def setup(bot):
    await bot.add_cog(Onboarding(bot))
