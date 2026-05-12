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
import asyncio

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
PUBLIC_LOG_ID = 1503433900536369323
GENERAL_CHAT_ID = 1503432785363206155
TICKET_CATEGORY_ID = 1503677546900754553
TICKET_CHANNEL_ID = 1503678206572625920

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
async def on_member_join(member):
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(title="📥 ВХОД В ИМПЕРИЮ", description=f"{member.mention} пересёк границу DLHSEC.", color=discord.Color.blue(), timestamp=datetime.datetime.now(datetime.timezone.utc))
        embed.add_field(name="Аккаунт создан", value=member.created_at.strftime("%d.%m.%Y"), inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        await log_channel.send(embed=embed)

    general_chat = bot.get_channel(GENERAL_CHAT_ID)
    if general_chat:
        await general_chat.send(
            f"🦅 **Приветствуем нового гражданина, {member.mention}!**\n\n"
            f"Добро пожаловать в **DLHSEC** — Демократическую Либеральную Священную Социальную Империю Христиан.\n\n"
            f"📜 Ознакомься с правилами в <#1503433303047340172>\n"
            f"✝️ Выбери свою конфессию в <#1503439326909038853>\n\n"
            f"Да хранит тебя Господь! Да хранит Господь твоих сограждан! Да хранит Господь империю!"
        )

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

    # АВТОРЕГИСТРАЦИЯ И СЧЁТЧИК СООБЩЕНИЙ ЗА ДЕНЬ
    if bot.db_pool:
        async with bot.db_pool.acquire() as conn:
            await conn.execute('INSERT INTO users (user_id) VALUES ($1) ON CONFLICT DO NOTHING', message.author.id)
            await conn.execute('''
                INSERT INTO daily_message_counts (user_id, message_date, msg_count)
                VALUES ($1, CURRENT_DATE, 1)
                ON CONFLICT (user_id, message_date)
                DO UPDATE SET msg_count = daily_message_counts.msg_count + 1
            ''', message.author.id)

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
        except Exception as e: print(f"Ошибка антиспама: {e}")

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
        except Exception as e: print(f"Ошибка анти-масс-пинга: {e}")

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

        public_chat = bot.get_channel(GENERAL_CHAT_ID)
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

# --- SLASH-КОМАНДЫ ---
@bot.tree.command(name="ban", description="Забанить пользователя")
@commands.has_permissions(administrator=True)
async def slash_ban(interaction: discord.Interaction, member: discord.Member, reason: str = "Нарушение правил"):
    try:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"✅ {member.mention} забанен. Причина: {reason}", ephemeral=True)
        ban_log = bot.get_channel(BAN_LOGS_ID)
        if ban_log:
            embed = discord.Embed(title="🔨 БАН", description=f"{member.mention} забанен.", color=discord.Color.dark_red(), timestamp=datetime.datetime.now(datetime.timezone.utc))
            embed.add_field(name="Модератор", value=interaction.user.mention)
            embed.add_field(name="Причина", value=reason)
            await ban_log.send(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="kick", description="Выгнать пользователя")
@commands.has_permissions(administrator=True)
async def slash_kick(interaction: discord.Interaction, member: discord.Member, reason: str = "Нарушение правил"):
    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"✅ {member.mention} выгнан. Причина: {reason}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="ping", description="Проверить связь с орлом")
async def slash_ping(interaction: discord.Interaction):
    await interaction.response.send_message("🦅 КЛИК КЛИК БУМ!", ephemeral=True)

@bot.tree.command(name="warn", description="Выдать варн пользователю")
@commands.has_permissions(administrator=True)
async def slash_warn(interaction: discord.Interaction, member: discord.Member, reason: str = "Нарушение правил"):
    async with bot.db_pool.acquire() as conn:
        await conn.execute("INSERT INTO warns (user_id, moderator_id, reason) VALUES ($1, $2, $3)", member.id, interaction.user.id, reason)
        count = await conn.fetchval("SELECT COUNT(*) FROM warns WHERE user_id = $1", member.id)

    warn_log = bot.get_channel(WARN_LOGS_ID)
    if warn_log:
        embed = discord.Embed(title="⚠️ ВАРН", color=discord.Color.orange(), timestamp=datetime.datetime.now(datetime.timezone.utc))
        embed.add_field(name="Нарушитель", value=member.mention, inline=True)
        embed.add_field(name="Модератор", value=interaction.user.mention, inline=True)
        embed.add_field(name="Причина", value=reason, inline=False)
        embed.add_field(name="Счетчик", value=f"{count}/6", inline=False)
        await warn_log.send(embed=embed)

    public_chat = bot.get_channel(GENERAL_CHAT_ID)
    if public_chat:
        await public_chat.send(f"⚠️ {member.mention} получил варн. Причина: {reason}. Всего: {count}/6")

    await interaction.response.send_message(f"✅ Варн выдан {member.mention}. Всего: {count}/6", ephemeral=True)

@bot.tree.command(name="unwarn", description="Снять последний варн с пользователя")
@commands.has_permissions(administrator=True)
async def slash_unwarn(interaction: discord.Interaction, member: discord.Member):
    async with bot.db_pool.acquire() as conn:
        last_warn_id = await conn.fetchval("SELECT warn_id FROM warns WHERE user_id = $1 ORDER BY timestamp DESC LIMIT 1", member.id)
        if last_warn_id is None:
            return await interaction.response.send_message(f"❌ У {member.mention} нет варнов.", ephemeral=True)
        await conn.execute("DELETE FROM warns WHERE warn_id = $1", last_warn_id)
        remaining = await conn.fetchval("SELECT COUNT(*) FROM warns WHERE user_id = $1", member.id)

    warn_log = bot.get_channel(WARN_LOGS_ID)
    if warn_log:
        embed = discord.Embed(title="➖ ВАРН СНЯТ", color=discord.Color.blue(), timestamp=datetime.datetime.now(datetime.timezone.utc))
        embed.add_field(name="С кого", value=member.mention, inline=True)
        embed.add_field(name="Модератор", value=interaction.user.mention, inline=True)
        embed.add_field(name="Осталось варнов", value=str(remaining), inline=False)
        await warn_log.send(embed=embed)

    public_chat = bot.get_channel(GENERAL_CHAT_ID)
    if public_chat:
        await public_chat.send(f"😇 С {member.mention} снят варн. Осталось: {remaining}/6")

    await interaction.response.send_message(f"✅ Последний варн снят с {member.mention}. Осталось: {remaining}/6", ephemeral=True)

@bot.tree.command(name="clearwarns", description="Полностью очистить историю варнов пользователя")
@commands.has_permissions(administrator=True)
async def slash_clearwarns(interaction: discord.Interaction, member: discord.Member):
    async with bot.db_pool.acquire() as conn:
        await conn.execute("DELETE FROM warns WHERE user_id = $1", member.id)

    warn_log = bot.get_channel(WARN_LOGS_ID)
    if warn_log:
        embed = discord.Embed(title="♻️ ИСТОРИЯ ОЧИЩЕНА", color=discord.Color.green(), timestamp=datetime.datetime.now(datetime.timezone.utc))
        embed.add_field(name="Пользователь", value=member.mention, inline=True)
        embed.add_field(name="Модератор", value=interaction.user.mention, inline=True)
        await warn_log.send(embed=embed)

    public_chat = bot.get_channel(GENERAL_CHAT_ID)
    if public_chat:
        await public_chat.send(f"✨ Все варны {member.mention} аннулированы. Чистый лист! Благодари Бога за снисхождение императора.")

    await interaction.response.send_message(f"✅ Все варны {member.mention} удалены.", ephemeral=True)

# --- ТИКЕТЫ ---
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Закрыть тикет", style=discord.ButtonStyle.red, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Только администратор может закрыть тикет.", ephemeral=True)
        async with bot.db_pool.acquire() as conn:
            await conn.execute("DELETE FROM tickets WHERE channel_id = $1", interaction.channel_id)
        await interaction.followup.send("✅ Тикет закрыт. Канал будет удалён через 5 секунд.")
        await asyncio.sleep(5)
        await interaction.channel.delete()

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Создать тикет", style=discord.ButtonStyle.blurple, custom_id="create_ticket_btn")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        user = interaction.user
        async with bot.db_pool.acquire() as conn:
            existing = await conn.fetchrow("SELECT channel_id FROM tickets WHERE user_id = $1 AND status = 'open'", user.id)
        if existing:
            old_channel = guild.get_channel(existing['channel_id'])
            if old_channel:
                return await interaction.response.send_message(f"❌ У тебя уже есть открытый тикет: {old_channel.mention}", ephemeral=True)
            else:
                async with bot.db_pool.acquire() as conn:
                    await conn.execute("DELETE FROM tickets WHERE channel_id = $1", existing['channel_id'])
        category = guild.get_channel(TICKET_CATEGORY_ID)
        if category is None:
            return await interaction.response.send_message("❌ Категория тикетов не найдена.", ephemeral=True)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(name=f"тикет-{user.name}", category=category, overwrites=overwrites)
        async with bot.db_pool.acquire() as conn:
            await conn.execute("INSERT INTO tickets (channel_id, user_id, status) VALUES ($1, $2, 'open')", channel.id, user.id)
        await interaction.followup.send(f"✅ Тикет создан: {channel.mention}", ephemeral=True)
        view = CloseTicketView()
        await channel.send(f"📩 {user.mention}, добро пожаловать в твой тикет!\nОпиши свою проблему или вопрос.\nАдминистратор ответит тебе здесь.\n\nКогда вопрос будет решён, администратор нажмёт кнопку ниже для закрытия тикета.", view=view)

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_tickets(ctx):
    embed = discord.Embed(title="📩 Поддержка DLHSEC", description="Нажми кнопку ниже, чтобы создать приватный тикет. Администрация ответит тебе лично.", color=discord.Color.blurple())
    await ctx.send(embed=embed, view=TicketView())

# =========================================
# КОМАНДА !ктоя (своя стата или чья-то)
# =========================================
@bot.command(name="ктоя")
async def who_am_i(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    user = member
    async with bot.db_pool.acquire() as conn:
        user_data = await conn.fetchrow('SELECT status, registered_at FROM users WHERE user_id = $1', user.id)
        if not user_data:
            await conn.execute('INSERT INTO users (user_id) VALUES ($1) ON CONFLICT DO NOTHING', user.id)
            user_data = await conn.fetchrow('SELECT status, registered_at FROM users WHERE user_id = $1', user.id)
        desc_data = await conn.fetchrow('SELECT description FROM user_descriptions WHERE user_id = $1', user.id)
        awards = await conn.fetch('SELECT award_name FROM user_awards WHERE user_id = $1', user.id)
        total_msgs = await conn.fetchval('SELECT msg_count FROM stats WHERE user_id = $1', user.id)
        total_msgs = total_msgs or 0
        today_msgs = await conn.fetchval('SELECT msg_count FROM daily_message_counts WHERE user_id = $1 AND message_date = CURRENT_DATE', user.id)
        today_msgs = today_msgs or 0
        warn_count = await conn.fetchval('SELECT COUNT(*) FROM warns WHERE user_id = $1', user.id)
        warn_count = warn_count or 0

    days_on_server = (datetime.datetime.now(datetime.timezone.utc) - user.joined_at).days if user.joined_at else "?"
    roles = ", ".join([role.mention for role in user.roles if role.name != "@everyone"]) or "Нет ролей"
    embed = discord.Embed(title=f"📋 Профиль: {user.display_name}", color=discord.Color.blue(), timestamp=datetime.datetime.now(datetime.timezone.utc))
    embed.set_thumbnail(url=user.display_avatar.url if user.display_avatar else user.default_avatar.url)
    embed.add_field(name="🏷 Ник", value=user.name, inline=True)
    embed.add_field(name="📅 На сервере", value=f"{days_on_server} дн.", inline=True)
    embed.add_field(name="🛡 Роли", value=roles, inline=False)
    status_text = user_data['status'] or "Не установлен"
    embed.add_field(name="📝 Статус", value=status_text, inline=False)
    desc_text = desc_data['description'] if desc_data and desc_data['description'] else "Описание отсутствует"
    embed.add_field(name="📖 Описание", value=desc_text, inline=False)
    awards_text = ", ".join([a['award_name'] for a in awards]) if awards else "Нет наград"
    embed.add_field(name="🏆 Награды", value=awards_text, inline=False)
    embed.add_field(name="💬 Сообщений всего", value=str(total_msgs), inline=True)
    embed.add_field(name="📆 Сообщений сегодня", value=str(today_msgs), inline=True)
    embed.add_field(name="⚠️ Варнов", value=str(warn_count), inline=True)
    await ctx.send(embed=embed)

# =========================================
# КОМАНДА !статус
# =========================================
@bot.command(name="статус")
async def set_status(ctx, *, text=None):
    if text is None:
        await ctx.send("❌ Используй: `!статус твой текст`")
        return
    async with bot.db_pool.acquire() as conn:
        await conn.execute('INSERT INTO users (user_id, status) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET status = $2, last_updated = NOW()', ctx.author.id, text)
    await ctx.send(f"✅ Статус обновлён!")

# =========================================
# КОМАНДА !описание
# =========================================
@bot.command(name="описание")
async def set_description(ctx, *, text=None):
    if text is None:
        await ctx.send("❌ Используй: `!описание твой текст` (или `!описание стереть`)")
        return
    user_id = ctx.author.id
    if text.strip().lower() in ["стереть", "удалить", "очистить"]:
        async with bot.db_pool.acquire() as conn:
            await conn.execute('DELETE FROM user_descriptions WHERE user_id = $1', user_id)
        await ctx.send("🗑 Описание удалено.")
        return
    async with bot.db_pool.acquire() as conn:
        await conn.execute('INSERT INTO user_descriptions (user_id, description) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET description = $2, updated_at = NOW()', user_id, text)
    await ctx.send("✅ Описание сохранено!")

# =========================================
# КОМАНДА !награда (только для админов)
# =========================================
@bot.command(name="награда")
@commands.has_permissions(administrator=True)
async def give_award(ctx, member: discord.Member, *, award_name: str):
    async with bot.db_pool.acquire() as conn:
        await conn.execute('INSERT INTO user_awards (user_id, award_name, awarded_by) VALUES ($1, $2, $3)', member.id, award_name, ctx.author.id)
    await ctx.send(f"🏆 Награда **{award_name}** выдана пользователю {member.mention}!")

# =========================================
# КОМАНДА !top
# =========================================
@bot.command(name="top")
async def top(ctx):
    async with bot.db_pool.acquire() as conn:
        rows = await conn.fetch('SELECT user_id, msg_count FROM stats ORDER BY msg_count DESC LIMIT 10')
    if not rows:
        return await ctx.send("Статистика пока пуста. Будь первым!")
    embed = discord.Embed(title="🏆 Топ активных граждан DLHSEC", color=discord.Color.gold(), timestamp=datetime.datetime.now(datetime.timezone.utc))
    description = ""
    for i, row in enumerate(rows, 1):
        member = ctx.guild.get_member(row['user_id'])
        name = member.display_name if member else f"Юзер {row['user_id']}"
        description += f"**{i}.** {name} — `{row['msg_count']}` сообщ.\n"
    embed.description = description
    await ctx.send(embed=embed)

# =========================================
# КОМАНДА !обнулить (админ)
# =========================================
@bot.command(name="обнулить")
@commands.has_permissions(administrator=True)
async def reset_stats(ctx):
    async with bot.db_pool.acquire() as conn:
        await conn.execute('DELETE FROM daily_message_counts')
        await conn.execute('DELETE FROM stats')
    await ctx.send("✅ Статистика полностью обнулена.")

# --- ЗАПУСК ---
bot.db_pool = None

async def init_db():
    DATABASE_URL = os.getenv("DATABASE_URL")
    bot.db_pool = await asyncpg.create_pool(DATABASE_URL, statement_cache_size=0)
    print("💎 Supabase подключен!")

@bot.event
async def on_ready():
    await init_db()
    bot.add_view(VerifyView())
    bot.add_view(ConfessionView())
    bot.add_view(TicketView())
    bot.add_view(CloseTicketView())
    await bot.tree.sync()
    print(f"🦅 {bot.user} взлетел! Iron Eagle в небе DLHSEC.")

if __name__ == "__main__":
    bot.run(TOKEN)
