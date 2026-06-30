# app.py - ПОЛНАЯ ВЕРСИЯ С ИГРОЙ И РАСШИРЕННЫМИ РОЛЯМИ

import asyncio
from telegram import Update, ChatPermissions, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import sqlite3
from datetime import datetime, timedelta
import logging
import os

# ============================================
# НАСТРОЙКИ
# ============================================
BOT_TOKEN = "8600278635:AAHEaVssEyfEk6vFIVhGXsSqgSkjnZUpFpI"
OWNER_ID = 5454940943
DATABASE = "admin.db"
GAME_URL = "https://depressedlua.github.io/testminiapp/"  # Сюда ссылку на game.html

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# БАЗА ДАННЫХ (с ролями)
# ============================================
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        tg_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        role TEXT DEFAULT 'user',
        is_banned INTEGER DEFAULT 0,
        ban_reason TEXT,
        muted_until TEXT,
        warnings INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        last_active TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        action TEXT,
        target_id INTEGER,
        details TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS groups (
        chat_id INTEGER PRIMARY KEY,
        title TEXT,
        welcome_text TEXT,
        rules_text TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def get_user(tg_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
    result = c.fetchone()
    conn.close()
    return result

def get_user_by_username(username):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    return result

def create_user(tg_id, username, first_name):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (tg_id, username, first_name) VALUES (?, ?, ?)", (tg_id, username, first_name))
    conn.commit()
    conn.close()

def get_user_role(tg_id):
    user = get_user(tg_id)
    return user[3] if user else 'user'

def set_user_role(tg_id, role):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("UPDATE users SET role = ? WHERE tg_id = ?", (role, tg_id))
    conn.commit()
    conn.close()

def ban_user(tg_id, reason):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned = 1, ban_reason = ? WHERE tg_id = ?", (reason, tg_id))
    conn.commit()
    conn.close()

def unban_user(tg_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned = 0, ban_reason = NULL WHERE tg_id = ?", (tg_id,))
    conn.commit()
    conn.close()

def mute_user(tg_id, minutes):
    muted_until = (datetime.now() + timedelta(minutes=minutes)).isoformat()
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("UPDATE users SET muted_until = ? WHERE tg_id = ?", (muted_until, tg_id))
    conn.commit()
    conn.close()

def unmute_user(tg_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("UPDATE users SET muted_until = NULL WHERE tg_id = ?", (tg_id,))
    conn.commit()
    conn.close()

def add_warning(tg_id, reason, admin_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("UPDATE users SET warnings = warnings + 1 WHERE tg_id = ?", (tg_id,))
    c.execute("SELECT warnings FROM users WHERE tg_id = ?", (tg_id,))
    warnings = c.fetchone()[0]
    c.execute("INSERT INTO logs (admin_id, action, target_id, details) VALUES (?, 'warn', ?, ?)", (admin_id, tg_id, reason))
    conn.commit()
    conn.close()
    return warnings

def remove_warning(tg_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("UPDATE users SET warnings = warnings - 1 WHERE tg_id = ? AND warnings > 0", (tg_id,))
    conn.commit()
    conn.close()

# ============================================
# ПРОВЕРКА РОЛЕЙ
# ============================================
ROLE_LEVELS = {
    'user': 0,
    'helper': 1,
    'moder': 2,
    'admin': 3,
    'fd1': 4,
    'fd2': 5,
    'owner': 99
}

def has_role(tg_id, required_role):
    """Проверяет, есть ли у пользователя роль или выше"""
    user_role = get_user_role(tg_id)
    return ROLE_LEVELS.get(user_role, 0) >= ROLE_LEVELS.get(required_role, 0)

def is_admin(tg_id):
    return has_role(tg_id, 'admin')

def is_moder(tg_id):
    return has_role(tg_id, 'moder')

def is_helper(tg_id):
    return has_role(tg_id, 'helper')

def is_fd1(tg_id):
    return has_role(tg_id, 'fd1')

def is_fd2(tg_id):
    return has_role(tg_id, 'fd2')

def is_owner(tg_id):
    return tg_id == OWNER_ID

def log_action(admin_id, action, target_id, details=''):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO logs (admin_id, action, target_id, details) VALUES (?, ?, ?, ?)", (admin_id, action, target_id, details))
    conn.commit()
    conn.close()

def get_recent_logs(limit=10):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM logs ORDER BY created_at DESC LIMIT ?", (limit,))
    result = c.fetchall()
    conn.close()
    return result

def get_total_users():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    result = c.fetchone()[0]
    conn.close()
    return result

def get_banned_count():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")
    result = c.fetchone()[0]
    conn.close()
    return result

def get_role_count(role):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE role = ?", (role,))
    result = c.fetchone()[0]
    conn.close()
    return result

def get_all_groups():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM groups")
    result = c.fetchall()
    conn.close()
    return result

def set_group_welcome(chat_id, text):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO groups (chat_id, welcome_text) VALUES (?, ?)", (chat_id, text))
    conn.commit()
    conn.close()

def get_group_welcome(chat_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT welcome_text FROM groups WHERE chat_id = ?", (chat_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def set_group_rules(chat_id, text):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO groups (chat_id, rules_text) VALUES (?, ?)", (chat_id, text))
    conn.commit()
    conn.close()

def get_group_rules(chat_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT rules_text FROM groups WHERE chat_id = ?", (chat_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================
def get_commands_for_role(role):
    """Возвращает список доступных команд для роли"""
    commands = {
        'user': [
            '/start - Приветствие',
            '/help - Помощь',
            '/game - 🎮 Открыть игру',
            '/info - Информация о себе',
            '/rules - Правила группы'
        ],
        'helper': [
            '/warn - Предупреждение',
            '/unwarn - Снять предупреждение',
            '/info - Информация о пользователе'
        ],
        'moder': [
            '/mute - Замутить',
            '/unmute - Размутить',
            '/kick - Кикнуть',
            '/warn - Предупреждение',
            '/unwarn - Снять предупреждение',
            '/info - Информация о пользователе'
        ],
        'admin': [
            '/ban - Забанить',
            '/unban - Разбанить',
            '/mute - Замутить',
            '/unmute - Размутить',
            '/kick - Кикнуть',
            '/warn - Предупреждение',
            '/unwarn - Снять предупреждение',
            '/promote - Повысить',
            '/demote - Понизить',
            '/info - Информация о пользователе',
            '/stats - Статистика',
            '/logs - Логи',
            '/groups - Список групп',
            '/setwelcome - Приветствие',
            '/setrules - Правила',
            '/clean - Очистить',
            '/pin - Закрепить',
            '/unpin - Открепить',
            '/slowmode - Медленный чат'
        ],
        'fd1': [
            '/ban - Забанить',
            '/unban - Разбанить',
            '/mute - Замутить',
            '/unmute - Размутить',
            '/kick - Кикнуть',
            '/warn - Предупреждение',
            '/unwarn - Снять предупреждение',
            '/promote - Повысить (до helper/moder)',
            '/demote - Понизить',
            '/info - Информация о пользователе',
            '/stats - Статистика',
            '/logs - Логи',
            '/groups - Список групп',
            '/setwelcome - Приветствие',
            '/setrules - Правила',
            '/clean - Очистить',
            '/pin - Закрепить',
            '/unpin - Открепить',
            '/slowmode - Медленный чат'
        ],
        'fd2': [
            'ВСЕ КОМАНДЫ (включая назначение админов)',
            '/addadmin - Назначить админом',
            '/promote - Повысить до любой роли'
        ],
        'owner': [
            'ПОЛНЫЙ ДОСТУП КО ВСЕМ КОМАНДАМ',
            '/addadmin - Назначить админом',
            '/setrole - Установить любую роль'
        ]
    }
    return commands.get(role, commands['user'])

# ============================================
# КОМАНДЫ БОТА
# ============================================

# ---------- ОСНОВНЫЕ КОМАНДЫ ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    create_user(user.id, user.username, user.first_name)
    
    if user.id == OWNER_ID:
        set_user_role(user.id, 'owner')
    
    keyboard = [
        [InlineKeyboardButton("🎮 Открыть игру", web_app=WebAppInfo(url=GAME_URL))],
        [InlineKeyboardButton("📋 Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "Бот создан для управления группами.\n"
        "Нажми на кнопку, чтобы открыть игру ниже!🎮",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает команды в зависимости от роли"""
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    
    commands = get_commands_for_role(role)
    text = f"📖 <b>Доступные команды</b>\n\n"
    text += f"<i>Ваша роль: {role.upper()}</i>\n\n"
    text += "\n".join(commands)
    
    if role != 'user':
        text += f"\n\n👑 Уровень доступа: {ROLE_LEVELS.get(role, 0)}"
    
    await update.message.reply_text(text, parse_mode="HTML")

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Открывает игру"""
    keyboard = [[InlineKeyboardButton("🎮 Открыть игру", web_app=WebAppInfo(url=GAME_URL))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎮 <b>Кликер-игра!</b>\n\n"
        "Нажимай на кнопку и зарабатывай очки!\n"
        "Покупай улучшения и становись сильнее!",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о пользователе"""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    text = f"""
📋 <b>Информация о вас</b>

👤 <b>Имя:</b> {update.effective_user.full_name}
🔹 <b>Username:</b> @{update.effective_user.username or 'нет'}
🆔 <b>ID:</b> {user[0]}
👑 <b>Роль:</b> {user[3].upper()}
⚠️ <b>Предупреждений:</b> {user[6]}/3
{'🔒 <b>Забанен:</b> ' + user[5] if user[4] == 1 else ''}
"""
    await update.message.reply_text(text, parse_mode="HTML")

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает правила группы"""
    rules_text = get_group_rules(update.effective_chat.id)
    
    if rules_text:
        await update.message.reply_text(f"📋 <b>ПРАВИЛА:</b>\n\n{rules_text}", parse_mode="HTML")
    else:
        await update.message.reply_text("📋 Правила не установлены")

# ---------- УПРАВЛЕНИЕ РОЛЯМИ ----------
async def setrole_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установить роль пользователю (только owner)"""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ Только владелец может использовать эту команду!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("❌ /setrole @username [роль]\nДоступные роли: user, helper, moder, admin, fd1, fd2")
        return
    
    target = context.args[0].replace('@', '')
    new_role = context.args[1].lower()
    
    allowed_roles = ['user', 'helper', 'moder', 'admin', 'fd1', 'fd2']
    if new_role not in allowed_roles:
        await update.message.reply_text(f"❌ Доступные роли: {', '.join(allowed_roles)}")
        return
    
    user = get_user_by_username(target)
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    set_user_role(user[0], new_role)
    log_action(update.effective_user.id, 'setrole', user[0], new_role)
    await update.message.reply_text(f"✅ {user[1]} получил роль <b>{new_role.upper()}</b>!", parse_mode="HTML")

# ---------- ОСТАЛЬНЫЕ КОМАНДЫ (бан, мут и т.д.) ----------
# Все команды с проверкой ролей

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ /ban @username [причина]")
        return
    
    target = context.args[0].replace('@', '')
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Без причины"
    
    user = get_user_by_username(target)
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    if user[3] in ['admin', 'fd1', 'fd2', 'owner']:
        await update.message.reply_text("❌ Нельзя забанить администратора!")
        return
    
    ban_user(user[0], reason)
    log_action(update.effective_user.id, 'ban', user[0], reason)
    await update.message.reply_text(f"🔨 {user[1]} забанен!\nПричина: {reason}")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ /unban @username")
        return
    
    target = context.args[0].replace('@', '')
    user = get_user_by_username(target)
    
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    unban_user(user[0])
    log_action(update.effective_user.id, 'unban', user[0])
    await update.message.reply_text(f"✅ {user[1]} разбанен!")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_moder(update.effective_user.id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("❌ /mute @username [время в минутах]")
        return
    
    target = context.args[0].replace('@', '')
    minutes = int(context.args[1]) if len(context.args) > 1 else 5
    
    user = get_user_by_username(target)
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            user[0],
            ChatPermissions(can_send_messages=False),
            until_date=datetime.now() + timedelta(minutes=minutes)
        )
        mute_user(user[0], minutes)
        log_action(update.effective_user.id, 'mute', user[0], f'{minutes} мин')
        await update.message.reply_text(f"🔇 {user[1]} замучен на {minutes} мин!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_moder(update.effective_user.id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ /unmute @username")
        return
    
    target = context.args[0].replace('@', '')
    user = get_user_by_username(target)
    
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            user[0],
            ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        unmute_user(user[0])
        log_action(update.effective_user.id, 'unmute', user[0])
        await update.message.reply_text(f"✅ {user[1]} размучен!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_moder(update.effective_user.id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ Команда только в группах!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ /kick @username")
        return
    
    target = context.args[0].replace('@', '')
    user = get_user_by_username(target)
    
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, user[0])
        await context.bot.unban_chat_member(update.effective_chat.id, user[0])
        log_action(update.effective_user.id, 'kick', user[0])
        await update.message.reply_text(f"👢 {user[1]} кикнут!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_helper(update.effective_user.id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("❌ /warn @username [причина]")
        return
    
    target = context.args[0].replace('@', '')
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Без причины"
    
    user = get_user_by_username(target)
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    warnings = add_warning(user[0], reason, update.effective_user.id)
    await update.message.reply_text(f"⚠️ {user[1]} получил предупреждение!\nПричина: {reason}\nВсего: {warnings}/3")
    
    if warnings >= 3:
        ban_user(user[0], "3 предупреждения")
        await update.message.reply_text(f"🔨 {user[1]} забанен (3 предупреждения)!")

async def unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_helper(update.effective_user.id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ /unwarn @username")
        return
    
    target = context.args[0].replace('@', '')
    user = get_user_by_username(target)
    
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    remove_warning(user[0])
    log_action(update.effective_user.id, 'unwarn', user[0])
    await update.message.reply_text(f"✅ Предупреждение снято с {user[1]}!")

async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_fd1(update.effective_user.id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("❌ /promote @username [роль]\nДоступно: helper, moder")
        return
    
    target = context.args[0].replace('@', '')
    new_role = context.args[1].lower()
    
    if new_role not in ['helper', 'moder']:
        await update.message.reply_text("❌ Доступные роли: helper, moder")
        return
    
    user = get_user_by_username(target)
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    if user[3] in ['admin', 'fd1', 'fd2', 'owner']:
        await update.message.reply_text("❌ Нельзя повысить администратора!")
        return
    
    set_user_role(user[0], new_role)
    log_action(update.effective_user.id, 'promote', user[0], new_role)
    await update.message.reply_text(f"⬆️ {user[1]} повышен до <b>{new_role.upper()}</b>!", parse_mode="HTML")

async def demote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_fd1(update.effective_user.id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ /demote @username")
        return
    
    target = context.args[0].replace('@', '')
    user = get_user_by_username(target)
    
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    if user[0] == OWNER_ID:
        await update.message.reply_text("❌ Нельзя понизить владельца!")
        return
    
    if user[3] in ['fd1', 'fd2', 'admin']:
        await update.message.reply_text("❌ Нельзя понизить старшего администратора!")
        return
    
    set_user_role(user[0], 'user')
    log_action(update.effective_user.id, 'demote', user[0])
    await update.message.reply_text(f"⬇️ {user[1]} понижен до <b>USER</b>!", parse_mode="HTML")

async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_fd2(update.effective_user.id) and not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ /addadmin @username")
        return
    
    target = context.args[0].replace('@', '')
    user = get_user_by_username(target)
    
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    set_user_role(user[0], 'admin')
    log_action(update.effective_user.id, 'addadmin', user[0])
    await update.message.reply_text(f"👑 {user[1]} назначен администратором!", parse_mode="HTML")

# ---------- СТАТИСТИКА И ЛОГИ ----------
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    text = f"""
📊 <b>СТАТИСТИКА</b>

👥 <b>Пользователи:</b>
• Всего: {get_total_users()}
• Забанено: {get_banned_count()}
• Админов: {get_role_count('admin')}
• FD1: {get_role_count('fd1')}
• FD2: {get_role_count('fd2')}
• Модераторов: {get_role_count('moder')}
• Хелперов: {get_role_count('helper')}

👑 <b>Владелец:</b> @Owner
"""
    await update.message.reply_text(text, parse_mode="HTML")

async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    logs_data = get_recent_logs(10)
    
    if not logs_data:
        await update.message.reply_text("📝 Логов нет")
        return
    
    text = "📝 <b>ПОСЛЕДНИЕ ЛОГИ:</b>\n\n"
    for log in logs_data:
        user = get_user(log[1])
        username = user[1] if user else str(log[1])
        text += f"• {username}: {log[2]} → {log[3]}\n"
    
    await update.message.reply_text(text, parse_mode="HTML")

async def groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    groups_data = get_all_groups()
    
    if not groups_data:
        await update.message.reply_text("📋 Бот не добавлен ни в одну группу")
        return
    
    text = "📋 <b>ГРУППЫ:</b>\n\n"
    for group in groups_data:
        text += f"• {group[1]} (ID: {group[0]})\n"
    
    await update.message.reply_text(text, parse_mode="HTML")

# ---------- ГРУППОВЫЕ КОМАНДЫ ----------
async def setwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ /setwelcome [текст приветствия]")
        return
    
    text = ' '.join(context.args)
    set_group_welcome(update.effective_chat.id, text)
    await update.message.reply_text(f"✅ Приветствие установлено!")

async def setrules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ /setrules [текст правил]")
        return
    
    text = ' '.join(context.args)
    set_group_rules(update.effective_chat.id, text)
    await update.message.reply_text(f"✅ Правила установлены!")

async def clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    count = int(context.args[0]) if context.args else 10
    
    if count > 100:
        await update.message.reply_text("❌ Максимум 100 сообщений")
        return
    
    try:
        await update.message.reply_text(f"🧹 Удалено {count} сообщений")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение")
        return
    
    try:
        await update.message.reply_to_message.pin()
        await update.message.reply_text("📌 Сообщение закреплено!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def unpin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    try:
        await context.bot.unpin_chat_message(update.effective_chat.id)
        await update.message.reply_text("📌 Сообщение откреплено!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def slowmode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ /slowmode [секунды]")
        return
    
    try:
        seconds = int(context.args[0])
        await context.bot.set_chat_slow_mode_delay(update.effective_chat.id, seconds)
        await update.message.reply_text(f"🐢 Режим медленного чата: {seconds} сек")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

# ============================================
# CALLBACK
# ============================================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "help":
        await help_command(update, context)

# ============================================
# ЗАПУСК
# ============================================
async def main():
    print("🚀 Запуск бота...")
    init_db()
    print("✅ База данных инициализирована")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Основные команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("game", game_command))
    app.add_handler(CommandHandler("info", info_command))
    app.add_handler(CommandHandler("rules", rules_command))
    
    # Управление ролями
    app.add_handler(CommandHandler("setrole", setrole_command))
    app.add_handler(CommandHandler("addadmin", addadmin))
    app.add_handler(CommandHandler("promote", promote))
    app.add_handler(CommandHandler("demote", demote))
    
    # Модерация
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("unwarn", unwarn))
    
    # Информация
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("logs", logs))
    app.add_handler(CommandHandler("groups", groups))
    
    # Групповые
    app.add_handler(CommandHandler("setwelcome", setwelcome))
    app.add_handler(CommandHandler("setrules", setrules))
    app.add_handler(CommandHandler("clean", clean))
    app.add_handler(CommandHandler("pin", pin))
    app.add_handler(CommandHandler("unpin", unpin))
    app.add_handler(CommandHandler("slowmode", slowmode))
    
    # Callback
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("✅ Бот запущен!")
    print("🤖 Бот готов к работе!")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())