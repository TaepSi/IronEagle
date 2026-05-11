import discord
from discord.ext import commands
import datetime
import os
import asyncpg
from flask import Flask
from threading import Thread
from collections import defaultdict
import time
from profanity_check import predict

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
MUTE_LOGS_ID = 1503446367979311125
WARN_LOGS_ID = 1503446730757374122
BAN_LOGS_ID = 1503446786826702921

CONFESSION_ROLES = {
    "Протестант": 1503440143942549725,
    "Католик": 1503440470259269713,
    "Православный": 1503440582259773620,
    "Ориентальный православный": 1503440656822177968
}

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- АНТИСПАМ ---
user_messages = defaultdict(list)
SPAM_LIMIT = 5
SPAM_TIME = 4
SPAM_TIMEOUT = 10

# --- АНТИ МАСС УПОМИНАНИЯ ---
MAX_MENTIONS = 5
MENTION_TIMEOUT = 30

# --- КНОПКА ВЕРИФИКАЦИИ ---
class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🦅 Стать гражданином DLHSEC", style=discord.ButtonStyle.green, custom_id="verify_btn")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(CITIZEN_ROLE_ID)
        if role is None:
            return await interaction.response.send_message("❌ Роль не найдена.", ephemeral=True)
        member = interaction.user
        if role in member.roles:
            await interaction.response.send_message("ℹ️ Ты уже гражданин Империи.", ephemeral=True)
        else:
            await member.add_roles(role)
            await interaction.response.send_message("✅ Добро пожаловать в DLHSEC, гражданин!", ephemeral=True)
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(title="🦅 НОВЫЙ ГРАЖДАНИН", description=f"{member.mention} прошёл верификацию.", color=discord.Color.green(), timestamp=datetime.datetime.now(datetime.timezone.utc))
                embed.set_thumbnail(url=member.display_avatar.url)
                await log_channel.send(embed=embed)

# --- ВЫПАДАЮЩЕЕ МЕНЮ КОНФЕССИЙ ---
class ConfessionSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Протестант", emoji="📖"),
            discord.SelectOption(label="Католик", emoji="✝️"),
            discord.SelectOption(label="Православный", emoji="☦️"),
            discord.SelectOption(label="Ориентальный православный", emoji="🕊")
        ]
        super().__init__(placeholder="Выбери свою конфессию...", min_values=1, max_values=1, options=options, custom_id="confession_select")

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        role_id = CONFESSION_ROLES.get(chosen)
        if role_id is None:
            return await interaction.response.send_message("❌ Роль не найдена.", ephemeral=True)
        role = interaction.guild.get_role(role_id)
        if role is None:
            return await interaction.response.send_message("❌ Роль не найдена на сервере.", ephemeral=True)
        member = interaction.user
        for other_name, other_id in CONFESSION_ROLES.items():
            if other_name != chosen:
                other_role = interaction.guild.get_role(other_id)
                if other_role and other_role in member.roles:
                    await member.remove_roles(other_role)
        if role in member.roles:
            await interaction.response.send_message(f"ℹ️ У тебя уже есть роль **{chosen}**.", ephemeral=True)
        else:
            await member.add_roles(role)
            await interaction.response.send_message(f"✅ Ты выбрал: **{chosen}**.", ephemeral=True)
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(title="✝️ ВЫБОР КОНФЕССИИ", description=f"{member.mention} выбрал: **{chosen}**.", color=discord.Color.purple(), timestamp=datetime.datetime.now(datetime.timezone.utc))
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
    print(f"🦅 {bot.user} взлетел! Iron Eagle в небе DLHSEC.")

@bot.event
async def on_member_join(member):
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(title="📥 ВХОД В ИМПЕРИЮ", description=f"{member.mention} пересёк границу DLHSEC.", color=discord.Color.blue(), timestamp=datetime.datetime.now(datetime.timezone.utc))
        embed.add_field(name="Аккаунт создан", value=member.created_at.strftime("%d.%m.%Y"), inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        await log_channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(title="📤 ВЫХОД ИЗ ИМПЕРИИ", description=f"{member.mention} покинул DLHSEC.", color=discord.Color.red(), timestamp=datetime.datetime.now(datetime.timezone.utc))
        embed.set_thumbnail(url=member.display_avatar.url)
        await log_channel.send(embed=embed)

@bot.event
async def on_message_delete(message):
    if message.author.bot: return
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(title="🗑 УДАЛЕНО", color=discord.Color.red(), timestamp=datetime.datetime.now(datetime.timezone.utc))
        embed.add_field(name="Автор", value=message.author.mention, inline=True)
        embed.add_field(name="Канал", value=message.channel.mention, inline=True)
        embed.add_field(name="Текст", value=message.content or "Файл", inline=False)
        await log_channel.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content: return
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(title="📝 ИЗМЕНЕНО", color=discord.Color.orange(), timestamp=datetime.datetime.now(datetime.timezone.utc))
        embed.add_field(name="Автор", value=before.author.mention, inline=True)
        embed.add_field(name="Канал", value=before.channel.mention, inline=True)
        embed.add_field(name="Было", value=before.content, inline=False)
        embed.add_field(name="Стало", value=after.content, inline=False)
        await log_channel.send(embed=embed)

# --- ОСНОВНОЙ ЦИКЛ МОДЕРАЦИИ ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    is_admin = message.author.guild_permissions.administrator
    content = message.content.lower()
    now = time.time()

    # Антиспам
    user_messages[message.author.id].append(now)
    user_messages[message.author.id] = [t for t in user_messages[message.author.id] if now - t <= SPAM_TIME]
    if len(user_messages[message.author.id]) >= SPAM_LIMIT and not is_admin:
        try:
            await message.author.timeout(datetime.timedelta(minutes=SPAM_TIMEOUT), reason="Антиспам")
            await message.channel.send(f"🚫 {message.author.mention} получил мут за спам.", delete_after=5)
            mute_channel = bot.get_channel(MUTE_LOGS_ID)
            if mute_channel:
                embed = discord.Embed(title="🚫 АНТИСПАМ", color=discord.Color.orange(), timestamp=datetime.datetime.now(datetime.timezone.utc))
                embed.add_field(name="Пользователь", value=f"{message.author.mention}", inline=False)
                embed.add_field(name="Наказание", value=f"{SPAM_TIMEOUT} минут тайм-аут", inline=False)
                await mute_channel.send(embed=embed)
            user_messages[message.author.id].clear()
            return
        except: pass

    # Анти масс-упоминания
    if len(message.mentions) >= MAX_MENTIONS and not is_admin:
        try:
            await message.delete()
            await message.author.timeout(datetime.timedelta(minutes=MENTION_TIMEOUT), reason="Массовые упоминания")
            await message.channel.send(f"🚫 {message.author.mention} получил мут за массовые упоминания.", delete_after=5)
            mute_channel = bot.get_channel(MUTE_LOGS_ID)
            if mute_channel:
                embed = discord.Embed(title="🚫 МАСС УПОМИНАНИЯ", color=discord.Color.red(), timestamp=datetime.datetime.now(datetime.timezone.utc))
                embed.add_field(name="Пользователь", value=f"{message.author.mention}", inline=False)
                embed.add_field(name="Наказание", value=f"{MENTION_TIMEOUT} минут тайм-аут", inline=False)
                await mute_channel.send(embed=embed)
            return
        except: pass

    # Умная модерация мата + варны
    if not is_admin and predict([message.content])[0] == 1:
        try: await message.delete()
        except: pass

        async with bot.db_pool.acquire() as conn:
            await conn.execute("INSERT INTO warns (user_id, moderator_id, reason) VALUES ($1, $2, $3)", message.author.id, bot.user.id, f"Мат: {message.content[:50]}")
            count = await conn.fetchval("SELECT COUNT(*) FROM warns WHERE user_id = $1", message.author.id)

        action_text = ""
        if count == 1: action_text = "получил 1-й варн."
        elif count == 2:
            await message.author.timeout(datetime.timedelta(hours=1), reason="2-й мат")
            action_text = "получил мут на 1 час."
        elif count == 3: action_text = "получил 2-й варн."
        elif count == 4:
            await message.author.timeout(datetime.timedelta(hours=12), reason="4-й мат")
            action_text = "получил мут на 12 часов."
        elif count == 5: action_text = "получил 3-й варн (ПОСЛЕДНЕЕ ПРЕДУПРЕЖДЕНИЕ)."
        else:
            try:
                await message.author.ban(reason="Систематический мат")
                action_text = "ЗАБАНЕН за рецидив."
            except: action_text = "должен быть забанен."

        public_chat = bot.get_channel(VERIFY_CHANNEL_ID)
        if public_chat: await public_chat.send(f"⚠️ {message.author.mention}, ты {action_text}")

        if count >= 6:
            ban_log = bot.get_channel(BAN_LOGS_ID)
            if ban_log:
                emb = discord.Embed(title="🔨 БАН", color=discord.Color.dark_red(), timestamp=datetime.datetime.now(datetime.timezone.utc))
                emb.add_field(name="Нарушитель", value=message.author.mention)
                await ban_log.send(embed=emb)
        elif count in [1, 3, 5]:
            warn_log = bot.get_channel(WARN_LOGS_ID)
            if warn_log:
                emb = discord.Embed(title="⚠️ ВАРН", color=discord.Color.orange(), timestamp=datetime.datetime.now(datetime.timezone.utc))
                emb.add_field(name="Юзер", value=message.author.mention)
                emb.add_field(name="Счетчик", value=f"{count}/6")
                await warn_log.send(embed=emb)
        else:
            mute_log = bot.get_channel(MUTE_LOGS_ID)
            if mute_log:
                emb = discord.Embed(title="🔇 МУТ", color=discord.Color.yellow(), timestamp=datetime.datetime.now(datetime.timezone.utc))
                emb.add_field(name="Юзер", value=message.author.mention)
                emb.add_field(name="Счетчик", value=f"{count}/6")
                await mute_log.send(embed=emb)
        return

    await bot.process_commands(message)

# --- КОМАНДЫ ---
@bot.command()
@commands.has_permissions(administrator=True)
async def setup_verify(ctx):
    await ctx.send(embed=discord.Embed(title="🦅 Врата DLHSEC", description="Нажми кнопку, чтобы стать гражданином.", color=discord.Color.gold()), view=VerifyView())

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_confession(ctx):
    await ctx.send(embed=discord.Embed(title="✝️ Выбор конфессии", description="Выбери свою ветвь христианства.", color=discord.Color.purple()), view=ConfessionView())

@bot.command()
async def ping(ctx):
    await ctx.send("🦅 КЛИК КЛИК БУМ!")

# --- ЗАПУСК ---
if __name__ == "__main__":
    bot.db_pool = None
    async def init_db():
        DATABASE_URL = os.getenv("DATABASE_URL")
        bot.db_pool = await asyncpg.create_pool(DATABASE_URL)
        print("💎 Supabase подключен!")
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())
    bot.run(TOKEN)
