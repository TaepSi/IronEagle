import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# --- БЛОК ОЖИВЛЯЛКИ ---
app = Flask('')

@app.route('/')
def home():
    return "Iron Eagle is online!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

keep_alive()

# --- НАСТРОЙКИ ---
TOKEN = os.getenv("DISCORD_TOKEN")
VERIFY_CHANNEL_ID = 1503430453342765127
CITIZEN_ROLE_ID = 1503383182467272714

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- КНОПКА ВЕРИФИКАЦИИ ---
class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🦅 Стать гражданином DLHSEC", style=discord.ButtonStyle.green, custom_id="verify_btn")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(CITIZEN_ROLE_ID)
        if role is None:
            return await interaction.response.send_message("❌ Роль не найдена. Сообщи Императору.", ephemeral=True)
        
        member = interaction.user
        if role in member.roles:
            await interaction.response.send_message("ℹ️ Ты уже гражданин Империи.", ephemeral=True)
        else:
            await member.add_roles(role)
            await interaction.response.send_message("✅ Добро пожаловать в DLHSEC, гражданин!", ephemeral=True)

# --- СОБЫТИЯ ---
@bot.event
async def on_ready():
    bot.add_view(VerifyView())
    print(f"🦅 {bot.user} взлетел! Iron Eagle патрулирует DLHSEC.")

# --- КОМАНДЫ ---
@bot.command()
@commands.has_permissions(administrator=True)
async def setup_verify(ctx):
    embed = discord.Embed(
        title="🦅 Врата DLHSEC",
        description="Добро пожаловать в Демократическую Либеральную Священную Социальную Империю Христиан.\n\nНажми кнопку ниже, чтобы получить роль Гражданина и присоединиться к Империи.",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed, view=VerifyView())

@bot.command()
async def ping(ctx):
    await ctx.send("🦅 КЛИК КЛИК БУМ!")

# --- ЗАПУСК ---
if __name__ == "__main__":
    bot.run(TOKEN)
