import discord
from discord.ext import commands
import os
import datetime
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
LOG_CHANNEL_ID = 1503433900536369323

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

            # Лог верификации
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(
                    title="🦅 НОВЫЙ ГРАЖДАНИН",
                    description=f"{member.mention} прошёл верификацию и стал гражданином DLHSEC.",
                    color=discord.Color.green(),
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                await log_channel.send(embed=embed)

# --- СОБЫТИЯ ---
@bot.event
async def on_ready():
    bot.add_view(VerifyView())
    print(f"🦅 {bot.user} взлетел! Iron Eagle патрулирует DLHSEC.")

@bot.event
async def on_member_join(member):
    # Лог входа
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="📥 ВХОД В ИМПЕРИЮ",
            description=f"{member.mention} пересёк границу DLHSEC.",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="Аккаунт создан", value=member.created_at.strftime("%d.%m.%Y"), inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        await log_channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    # Лог выхода
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="📤 ВЫХОД ИЗ ИМПЕРИИ",
            description=f"{member.mention} покинул DLHSEC.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await log_channel.send(embed=embed)

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
