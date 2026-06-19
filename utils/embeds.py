import discord

COLOUR_BRAND   = 0x5865F2   # Discord blurple (in-progress)
COLOUR_SUCCESS = 0x57F287   # Green
COLOUR_WARNING = 0xFEE75C   # Yellow
COLOUR_ERROR   = 0xED4245   # Red

def progress_embed(
    broker_name: str,
    broker_email: str,
    lane: str,
    date: str,
    status_text: str,
    color: int = COLOUR_BRAND,
) -> discord.Embed:
    """Builds the standard pipeline progress embed."""
    embed = discord.Embed(
        title="📬  Broker Outreach Pipeline",
        color=color,
    )
    embed.add_field(
        name="👤 Broker",
        value=f"**{broker_name}**\n`{broker_email}`",
        inline=True,
    )
    embed.add_field(name="🛣️ Lane", value=lane, inline=True)
    embed.add_field(name="📅 Date", value=date, inline=True)
    embed.add_field(name="⚙️ Pipeline Status", value=status_text, inline=False)
    return embed

def error_embed(title: str, detail: str) -> discord.Embed:
    """Builds a compact error embed."""
    embed = discord.Embed(title=f"❌  {title}", color=COLOUR_ERROR)
    embed.description = f"```{str(detail)[:1000]}```"
    embed.set_footer(text="Check bot-errors.log for the full stack trace.")
    return embed
