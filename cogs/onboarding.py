import discord
from discord.ext import commands
from discord import app_commands
import logging
from sqlalchemy.future import select

from database.models import AsyncSessionLocal, CompanyProfile

log = logging.getLogger("broker_bot.onboarding")

class OnboardingModal(discord.ui.Modal, title='Company Onboarding'):
    company_name = discord.ui.TextInput(
        label='Company Name',
        placeholder='e.g., Fast Freight Logistics',
        required=True
    )
    mc_number = discord.ui.TextInput(
        label='MC / DOT Number',
        placeholder='e.g., MC-123456',
        required=True
    )
    eld_provider = discord.ui.TextInput(
        label='ELD Provider',
        placeholder='e.g., Motive, Samsara, KeepTruckin',
        required=True
    )
    accounting_software = discord.ui.TextInput(
        label='Accounting Software',
        placeholder='e.g., QuickBooks Online, Xero',
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            async with AsyncSessionLocal() as session:
                # Check if user already has a profile
                result = await session.execute(
                    select(CompanyProfile).where(CompanyProfile.user_id == str(interaction.user.id))
                )
                profile = result.scalars().first()

                if profile:
                    # Update existing profile
                    profile.company_name = self.company_name.value
                    profile.mc_number = self.mc_number.value
                    profile.eld_provider = self.eld_provider.value
                    profile.accounting_software = self.accounting_software.value
                    msg = "✅ Your company profile has been updated in HAUL-E!"
                else:
                    # Create new profile
                    new_profile = CompanyProfile(
                        company_name=self.company_name.value,
                        mc_number=self.mc_number.value,
                        eld_provider=self.eld_provider.value,
                        accounting_software=self.accounting_software.value,
                        user_id=str(interaction.user.id)
                    )
                    session.add(new_profile)
                    msg = f"🎉 Welcome aboard, **{self.company_name.value}**! Your account is fully set up in HAUL-E."
                
                await session.commit()
            
            await interaction.response.send_message(msg, ephemeral=True)
            log.info(f"User {interaction.user.id} completed onboarding for {self.company_name.value}")
        
        except Exception as e:
            log.error(f"Error during onboarding: {e}", exc_info=True)
            await interaction.response.send_message("❌ An error occurred while saving your profile. Please try again later.", ephemeral=True)


class Onboarding(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="onboard", description="Set up your company profile and integrate your data systems.")
    async def onboard(self, interaction: discord.Interaction):
        """Pops up a modal for users to enter their company info."""
        await interaction.response.send_modal(OnboardingModal())

async def setup(bot: commands.Bot):
    await bot.add_cog(Onboarding(bot))
