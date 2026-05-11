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
CONFESSION_CHANNEL_ID = 1503439326909038853

# Конфессии
CONFESSION_ROLES = {
    "Протестант": 1503440143942549725,
    "Католик": 1503440470259269713,
    "Православный": 1503440582259773620,
    "Ориентальный православный": 1503440656822177968
}

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

            # Лог
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

# --- ВЫПАДАЮЩЕЕ МЕНЮ ДЛЯ КОНФЕССИЙ ---
class ConfessionSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Протестант", description="Лютеранство, баптизм, АСД, пятидесятничество и др.", emoji="📖"),
            discord.SelectOption(label="Католик", description="Римско-католическая и восточные католические церкви", emoji="✝️"),
            discord.SelectOption(label="Православный", description="РПЦ, греческая, сербская, грузинская и др.", emoji="☦️"),
            discord.SelectOption(label="Ориентальный православный", description="ААЦ, коптская, сирийская, эфиопская и др.", emoji="🕊")
        ]
        super().__init__(placeholder="Выбери свою конфессию...", min_values=1, max_values=1, options=options, custom_id="confession_select")

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        role_id = CONFESSION_ROLES.get(chosen)
        if role_id is None:
            return await interaction.response.send_message("❌ Ошибка: роль не найдена.", ephemeral=True)

        role = interaction.guild.get_role(role_id)
        if role is None:
            return await interaction.response.send_message("❌ Роль не найдена на сервере.", ephemeral=True)

        member = interaction.user

        # Убираем другие конфессии
        for other_name, other_id in CONFESSION_ROLES.items():
            if other_name != chosen:
                other_role = interaction.guild.get_role(other_id)
                if other_role and other_role in member.roles:
                    await member.remove_roles(other_role)

        if role in member.roles:
            await interaction.response.send_message(f"ℹ️ У тебя уже есть роль **{chosen}**.", ephemeral=True)
        else:
            await member.add_roles(role)
            await interaction.response.send_message(f"✅ Ты выбрал конфессию: **{chosen}**. Добро пожаловать в свою ветвь!", ephemeral=True)

            # Лог
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(
                    title="✝️ ВЫБОР КОНФЕССИИ",
                    description=f"{member.mention} выбрал: **{chosen}**.",
                    color=discord.Color.purple(),
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                await log_channel.send(embed=embed)

class ConfessionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ConfessionSelect())

# --- СОБЫТИЯ ---
@bot.event
async def on_ready():
    bot.add_view(VerifyView())
    bot.add_view(ConfessionView())
    print(f"🦅 {bot.user} взлетел! Iron Eagle патрулирует DLHSEC.")

@bot.event
async def on_member_join(member):
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
        description="Нажми кнопку ниже, чтобы получить роль Гражданина и присоединиться к Империи.",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed, view=VerifyView())

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_confession(ctx):
    embed = discord.Embed(
        title="✝️ Выбор конфессии",
        description="Выбери свою ветвь христианства из выпадающего меню ниже. Это поможет нам лучше понимать друг друга.",
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed, view=ConfessionView())

@bot.command()
async def ping(ctx):
    await ctx.send("🦅 КЛИК КЛИК БУМ!")

# --- ЗАПУСК ---
if __name__ == "__main__":
    bot.run(TOKEN)
