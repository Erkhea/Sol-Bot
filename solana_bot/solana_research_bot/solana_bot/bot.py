import asyncio
import logging
from datetime import datetime, timezone
import discord
from discord import app_commands
from discord.ext import commands, tasks

from .config import DISCORD_TOKEN, SOLANA_RPC_URL, POLL_SECONDS
from .providers import DataProvider
from .analyzer import analyse
from .ai_explainer import explain
from . import storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("solana-research")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
provider = DataProvider(SOLANA_RPC_URL)

def money(value):
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "Unavailable"

async def build_report(address: str):
    pair = await provider.market_data(address)
    mint = None
    try:
        mint = await provider.mint_checks(address)
    except Exception as exc:
        log.warning("Mint checks unavailable for %s: %s", address, exc)
    return analyse(address, pair, mint)

def report_embed(report):
    colour = discord.Colour.green() if report["score"] >= 75 and not report["hard_flags"] else (
        discord.Colour.orange() if report["score"] >= 55 and not report["hard_flags"] else discord.Colour.red()
    )
    embed = discord.Embed(
        title=f'{report["name"]} ({report["symbol"]})',
        description=f'**Assessment:** {report["verdict"]}\n**Heuristic score:** {report["score"]}/100',
        url=report.get("pair_url"),
        colour=colour,
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Price", value=money(report["price_usd"]), inline=True)
    embed.add_field(name="Liquidity", value=money(report["liquidity_usd"]), inline=True)
    embed.add_field(name="24h volume", value=money(report["volume_24h_usd"]), inline=True)
    embed.add_field(name="Market cap / FDV", value=money(report["market_cap_usd"]), inline=True)
    embed.add_field(name="24h change", value=f'{report["price_change_24h_pct"]:+.2f}%', inline=True)
    embed.add_field(name="24h buys / sells", value=f'{report["buys_24h"]} / {report["sells_24h"]}', inline=True)
    if report["hard_flags"]:
        embed.add_field(name="Risk flags", value="\n".join(f"• {x}" for x in report["hard_flags"])[:1024], inline=False)
    if report["reasons"]:
        embed.add_field(name="Findings", value="\n".join(f"• {x}" for x in report["reasons"])[:1024], inline=False)
    embed.set_footer(text="Read-only research • Heuristic, not financial advice • Verify data independently")
    return embed

@bot.event
async def on_ready():
    await bot.tree.sync()
    log.info("Logged in as %s", bot.user)
    if not watch_loop.is_running():
        watch_loop.start()

@bot.tree.command(name="scan", description="Analyse a Solana token mint address (read-only)")
@app_commands.describe(address="Solana token mint address")
async def scan(interaction: discord.Interaction, address: str):
    await interaction.response.defer(thinking=True)
    try:
        report = await build_report(address.strip())
        embed = report_embed(report)
        ai_text = await explain(report)
        if ai_text:
            embed.add_field(name="AI explanation", value=ai_text[:1024], inline=False)
        await interaction.followup.send(embed=embed)
    except Exception as exc:
        await interaction.followup.send(f"Scan failed: {type(exc).__name__}: {exc}")

@bot.tree.command(name="watch", description="Add a token mint to the read-only watchlist")
@app_commands.describe(address="Solana token mint address")
async def watch(interaction: discord.Interaction, address: str):
    try:
        # Validate it before storing.
        await provider.market_data(address.strip())
        storage.add_watch(address.strip(), str(interaction.user.id))
        await interaction.response.send_message("Added to the watchlist. Important changes will be posted here.", ephemeral=True)
    except Exception as exc:
        await interaction.response.send_message(f"Could not add token: {type(exc).__name__}: {exc}", ephemeral=True)

@bot.tree.command(name="unwatch", description="Remove a token from the watchlist")
@app_commands.describe(address="Solana token mint address")
async def unwatch(interaction: discord.Interaction, address: str):
    removed = storage.remove_watch(address.strip())
    await interaction.response.send_message("Removed." if removed else "That address was not on the watchlist.", ephemeral=True)

@bot.tree.command(name="setalertchannel", description="Choose where important watchlist alerts are posted")
@app_commands.describe(channel="A channel where the bot can send alerts")
@app_commands.checks.has_permissions(manage_guild=True)
async def setalertchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    storage.set_alert_channel(interaction.guild_id, channel.id)
    await interaction.response.send_message(f"Important watchlist alerts will be posted in {channel.mention}.", ephemeral=True)

@bot.tree.command(name="watchlist", description="Show currently watched tokens")
async def watchlist(interaction: discord.Interaction):
    rows = storage.list_watched()
    if not rows:
        await interaction.response.send_message("The watchlist is empty. Use /watch with a token mint address.", ephemeral=True)
        return
    lines = [f"`{r[0][:6]}…{r[0][-6:]}` — {r[2] or 'Waiting for first scan'} — score {r[1] if r[1] is not None else 'N/A'}" for r in rows]
    await interaction.response.send_message("\n".join(lines)[:1900], ephemeral=True)

@tasks.loop(seconds=POLL_SECONDS)
async def watch_loop():
    # Important-change alerts are sent to the channel where the bot is used/configured.
    # For this starter, alerts go to the first text channel the bot can send to per guild.
    for address, old_score, old_verdict, old_price, old_liquidity, old_change in storage.get_watched():
        try:
            report = await build_report(address)
            price = float(report["price_usd"] or 0)
            liquidity = float(report["liquidity_usd"] or 0)
            prior_price = float(old_price or 0)
            prior_liq = float(old_liquidity or 0)
            price_move = abs((price / prior_price - 1) * 100) if prior_price else 0
            liq_move = abs((liquidity / prior_liq - 1) * 100) if prior_liq else 0
            verdict_changed = old_verdict is not None and old_verdict != report["verdict"]
            important = verdict_changed or (old_verdict is None and bool(report["hard_flags"])) or price_move >= 15 or liq_move >= 20
            storage.update_watch(address, report["score"], report["verdict"], price, liquidity, report["price_change_24h_pct"])
            if important:
                for guild in bot.guilds:
                    channel_id = storage.get_alert_channel(guild.id)
                    channel = guild.get_channel(int(channel_id)) if channel_id else None
                    if isinstance(channel, discord.TextChannel) and channel.permissions_for(guild.me).send_messages:
                        embed = report_embed(report)
                        embed.title = "WATCH ALERT: " + embed.title
                        await channel.send(embed=embed)
        except Exception as exc:
            log.warning("Watch scan failed for %s: %s", address, exc)

@watch_loop.before_loop
async def before_watch_loop():
    await bot.wait_until_ready()

async def main():
    if not DISCORD_TOKEN:
        raise SystemExit("Missing DISCORD_TOKEN. Copy .env.example to .env and add your bot token.")
    await bot.start(DISCORD_TOKEN)
