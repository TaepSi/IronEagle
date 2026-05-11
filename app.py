import discord
from discord.ext import commands
import os

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🦅 {bot.user} взлетел! Iron Eagle в небе.")

@bot.command()
async def ping(ctx):
    await ctx.send("🦅 Клёкот!")

if __name__ == "__main__":
    bot.run(TOKEN)