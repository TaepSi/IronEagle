import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# --- БЛОК ОЖИВЛЯЛКИ ---
app = Flask('')
@app.route('/')
def home(): return "Iron Eagle is online!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# --- НАСТРОЙКИ ---
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
    keep_alive()
    bot.run(TOKEN)
