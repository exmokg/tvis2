#Импорты
# -*-coding: utf-8 -*-

import aiogram
import asyncio
import sqlite3
import random
from random import randint
import logging
import time
from asyncio import sleep
from datetime import datetime, timedelta
from time import gmtime, strftime, localtime
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
import os, re, configparser, requests
from aiogram.types import ContentType
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.handler import CancelHandler, current_handler
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.utils.markdown import quote_html
from aiogram.utils.exceptions import Throttled
import psutil
import config
import users
import chats

class ChRass(StatesGroup):
    msg = State()

class Rass(StatesGroup):
    msg = State()

class Quest(StatesGroup):
    msg = State()

#Бот
bot = aiogram.Bot(config.bot_token, parse_mode='HTML')
dp = Dispatcher(bot, storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)


def rate_limit(limit, key=None):
    def decorator(func):
        setattr(func, 'throttling_rate_limit', limit)
        if key:
            setattr(func, 'throttling_key', key)
        return func

    return decorator


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, limit=0, key_prefix='antiflood_'):
        self.rate_limit = limit
        self.prefix = key_prefix
        super(ThrottlingMiddleware, self).__init__()

    async def on_process_message(self, message, data):
        handler = current_handler.get()
        dispatcher = Dispatcher.get_current()
        
        if handler:
            limit = getattr(handler, 'throttling_rate_limit', self.rate_limit)
            key = getattr(handler, 'throttling_key', f"{self.prefix}_{handler.__name__}")
        else:
            limit = self.rate_limit
            key = f"{self.prefix}_message"

        if limit <= 0:
            return

        try:
            await dispatcher.throttle(key, rate=limit)
        except Throttled as t:
            await self.message_throttled(message, t)
            raise CancelHandler()

    async def message_throttled(self, message, throttled):
        handler = current_handler.get()

        if handler:
            key = getattr(handler, 'throttling_key', f"{self.prefix}_{handler.__name__}")
        else:
            key = f"{self.prefix}_message"

        if throttled.exceeded_count <= 2:
            await message.reply('❎ | Не спамь!')


#Обращение
@dp.message_handler(commands=['обращение', 'q', 'вопрос'], commands_prefix='!./')
async def cmd_quest(message: types.Message):
    id = message.from_user.id
    await message.answer(f'📥 | <b>Отправьте текст/фото для обращения:</b>')
    await Quest.msg.set()

@dp.message_handler(content_types=ContentType.ANY, state=Quest.msg)
async def quest_msgl(message: types.Message, state: FSMContext):
    await state.finish()
    owner = config.owner
    name = message.from_user.get_mention(as_html=True)
    bot_msg = await message.answer(f'Обращение отправляется...')
    await bot.send_message(owner, f'Получено обращение!\n\nОтправитель: {name}\nID: {message.from_user.id}\nЮзернейм: @{message.from_user.username}\n\nОбращение:')
    await message.copy_to(owner)
    await bot_msg.edit_text(f'📤 Обращение отправлено!')

#bot_msg
@dp.message_handler(lambda msg: msg.text.lower() == 'бот')
async def bot_msg(message):
    id = message.from_user.id
    users.cursor.execute(f"SELECT id from users WHERE id = '{id}'")
    if users.cursor.fetchone() is None:
        await message.reply(f'Работает!\nВведите /start')
    else:
        await message.answer(f'Работает!')

#Девборд
@dp.message_handler(commands=['дев', 'dev'], commands_prefix='!./')
async def adm_ui(message):
    status = users.cursor.execute("SELECT status from users where id = ?", (message.from_user.id,)).fetchone()
    status = (status[0])
    if str(status) == 'Создатель бота':
        admin_menu = InlineKeyboardMarkup()
        statistics_bt = InlineKeyboardButton(text = '📊 Статистика', callback_data = 'stat')
        mail_bt = InlineKeyboardButton(text = '✉️ Рассылка', callback_data = 'rassilka')
        mail_bt2 = InlineKeyboardButton(text = '💬 Чат рассылка', callback_data = 'chat_rassilka')
        ping_bt = InlineKeyboardButton(text = '🖥 Ресурсы бота', callback_data = 'ping')
        cancel_del_menu = InlineKeyboardMarkup()
        cancel_del_bt = InlineKeyboardButton(text = '❌ Закрыть ❌', callback_data = 'cancel_del')
        admin_menu.add(statistics_bt, ping_bt)
        admin_menu.add(mail_bt, mail_bt2)
        admin_menu.add(cancel_del_bt)
        await message.answer('🛠 Выберите пункт меню:', reply_markup=admin_menu)
    else:
        await message.reply(f'Вы не разработчик!')

@dp.callback_query_handler(text='cancel_del')
async def handle_cdel_button(c: types.CallbackQuery):
    status = users.cursor.execute("SELECT status from users where id = ?", (c.from_user.id,)).fetchone()
    status = (status[0])
    if str(status) == 'Создатель бота':
        await c.message.delete()
    else:
        pass

@dp.callback_query_handler(text='stat')
async def handle_stat_button(c: types.CallbackQuery):
    status = users.cursor.execute("SELECT status from users where id = ?", (c.from_user.id,)).fetchone()
    status = (status[0])
    if str(status) == 'Создатель бота':
        cancel_menu = InlineKeyboardMarkup()
        cancel_bt = InlineKeyboardButton(text = '🚫 Отмена', callback_data = 'cancel')
        cancel_menu.add(cancel_bt)
        us = users.cursor.execute('SELECT * FROM users').fetchall()
        ch = chats.cursor.execute('SELECT * FROM chats').fetchall()
        ls = users.cursor.execute('SELECT * FROM users WHERE ls is 1').fetchall()
        await c.message.edit_text(f"""#СТАТИСТИКА
Юзеров: <b>{len(us)}</b> 👤
Чатов: <b>{len(ch)}</b> 👥
Л/С: <b>{len(ls)}</b> ✅""", reply_markup = cancel_menu)
    else:
        pass

@dp.callback_query_handler(text='ping')
async def handle_ping_button(c: types.CallbackQuery):
    status = users.cursor.execute("SELECT status from users where id = ?", (c.from_user.id,)).fetchone()
    status = (status[0])
    if str(status) == 'Создатель бота':
        cancel_menu = InlineKeyboardMarkup()
        cancel_bt = InlineKeyboardButton(text = '🚫 Отмена', callback_data = 'cancel')
        cancel_menu.add(cancel_bt)
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        a = time.time()
        bot_msg = await c.message.edit_text(text='Проверка...')
        if bot_msg:
            b = time.time()
        await c.message.edit_text(f'Пинг: <b>{round((b-a)*1000, 2)}</b> мс\nОЗУ: <b>{mem}</b>% \nCPU: <b>{cpu}</b>%', reply_markup = cancel_menu)
    else:
        pass

@dp.callback_query_handler(text='cancel')
async def cancel_wnum_button_handler(c: types.callback_query):
    status = users.cursor.execute("SELECT status from users where id = ?", (c.from_user.id,)).fetchone()
    status = (status[0])
    if str(status) == 'Создатель бота':
        admin_menu = InlineKeyboardMarkup()
        statistics_bt = InlineKeyboardButton(text = '📊 Статистика', callback_data = 'stat')
        mail_bt = InlineKeyboardButton(text = '✉️ Рассылка', callback_data = 'rassilka')
        mail_bt2 = InlineKeyboardButton(text = '💬 Чат рассылка', callback_data = 'chat_rassilka')
        ping_bt = InlineKeyboardButton(text = '🖥 Ресурсы бота', callback_data = 'ping')
        cancel_del_menu = InlineKeyboardMarkup()
        cancel_del_bt = InlineKeyboardButton(text = '❌ Закрыть ❌', callback_data = 'cancel_del')
        admin_menu.add(statistics_bt, ping_bt)
        admin_menu.add(mail_bt, mail_bt2)
        admin_menu.add(cancel_del_bt)
        await c.message.edit_text('🛠 Выберите пункт меню:', reply_markup=admin_menu)
    else:
        pass

#Рассылка
#Для юзеров
@dp.callback_query_handler(text="rassilka")
async def send_rass(call: types.CallbackQuery):
    status = users.cursor.execute("SELECT status from users where id = ?", (call.from_user.id,)).fetchone()
    status = (status[0])
    if str(status) == 'Создатель бота':
        await call.message.edit_text(text='🖋 Введите текст/фото для рассылки:')
        await Rass.msg.set()
    else:
        pass

@dp.message_handler(content_types=ContentType.ANY, state=Rass.msg)
async def rassilka_msgl(message: types.Message, state: FSMContext):
    await state.finish()
    users.cursor.execute(f"SELECT id FROM users")
    users_query = users.cursor.fetchall()
    user_ids = [user[0] for user in users_query]
    nowtim = time.time()
    confirm = []
    decline = []
    bot_msg = await message.answer(f'Рассылка началась...')
    for i in user_ids:
        try:
            await message.copy_to(i)
            confirm.append(i)
        except:
            decline.append(i)
        await asyncio.sleep(0.15)
    nowtime = time.time()
    uptime = round(nowtime - nowtim)
    uptimestr = str(time.strftime("%H:%M:%S", time.gmtime(int(uptime))))
    await bot_msg.edit_text(f'📣 Рассылка завершена!\n\n✅ Успешно: {len(confirm)}\n❌ Неуспешно: {len(decline)}\n⌚ Время: {str(uptimestr)}')

#Для чатов
@dp.callback_query_handler(text="chat_rassilka")
async def send_rass(call: types.CallbackQuery):
    status = users.cursor.execute("SELECT status from users where id = ?", (call.from_user.id,)).fetchone()
    status = (status[0])
    if str(status) == 'Создатель бота':
        await call.message.edit_text(text='🖋 Введите текст/фото для рассылки:')
        await ChRass.msg.set()
    else:
        pass

@dp.message_handler(content_types=ContentType.ANY, state=ChRass.msg)
async def rassilka_msgl(message: types.Message, state: FSMContext):
    await state.finish()
    chats.cursor.execute(f"SELECT chat_id FROM chats")
    chats_query = chats.cursor.fetchall()
    chat_ids = [chat[0] for chat in chats_query]
    nowtim = time.time()
    confirm = []
    decline = []
    bot_msg = await message.answer(f'Рассылка началась...')
    for i in chat_ids:
        try:
            await message.copy_to(i)
            confirm.append(i)
        except:
            decline.append(i)
        await asyncio.sleep(0.15)
    nowtime = time.time()
    uptime = round(nowtime - nowtim)
    uptimestr = str(time.strftime("%H:%M:%S", time.gmtime(int(uptime))))
    await bot_msg.edit_text(f'📣 Рассылка завершена!\n\n✅ Успешно: {len(confirm)}\n❌ Неуспешно: {len(decline)}\n⌚ Время: {str(uptimestr)}')

#invited (@Penggrin)
@dp.message_handler(content_types=types.ContentTypes.NEW_CHAT_MEMBERS)
async def new_chat_member(message: types.Message):
    if message.new_chat_members[0]['id'] != 5685921196:
        welcome = (chats.cursor.execute("SELECT welcome FROM chats WHERE chat_id = ?", (message.chat.id,)).fetchone())[0]
        await message.answer(f"{welcome}")
        return

    result = """<b>Приветствую!</b> 👋
Я солевой бот PARANOIK. 
Чтобы начать работу, выдайте мне пожалуйста права администратора. 

Узнать полный список функционала можно с помощью команды /help

🗞 <a href="https://t.me/UFCRussia">Канал с новостями</a>

💬 <a href="https://t.me/UFCRussiaChat">Наша общая беседа</a>"""

    await message.answer(result)

    chats.cursor.execute(f"SELECT chat_id FROM chats WHERE chat_id = '{message.chat.id}'")
    if chats.cursor.fetchone():
        return

    chats.cursor.execute("INSERT INTO chats VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", (message.chat.id, message.chat.title, message.chat.username, "разрешено", 0, datetime.now().strftime("%d.%m.%Y"), "Обычный", "Отсутствуют", 'да', "Не указаны!", "Добро пожаловать в чат!"))
    chats.connect.commit()

    await bot.send_message(config.owner, f'#НОВЫЙ_ЧАТ\n👥 Название: {message.chat.title}\n📎 Ссылка: @{message.chat.username}\n✅ ID: <code>{message.chat.id}</code>')

#start_cmd
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    now = datetime.now()
    time_dice = current_date = datetime.now() - timedelta(seconds=18000)
    current = current_date.time()
    regdata = now.strftime("%d.%m.%Y")
    ttime = current.strftime('%H:%M:%S')
    bio = "Не установлено..."
    start_str = """<b>Приветствую!</b> 👋
Я солевой бот PARANOIK.

Узнать полный список функционала можно с помощью команды /help

🗞 <a href="https://t.me/UFCRussia">Канал с новостями</a>

💬 <a href="https://t.me/UFCRussiaChat">Наша общая беседа</a>"""

    if message.chat.type == 'private':
        botchatkb = InlineKeyboardMarkup()
        botchatkb.add(InlineKeyboardButton(text="Написать администратору чата", url='https://t.me/nakatika_naebuka'))

        await message.reply(start_str, reply_markup=botchatkb)

        users.cursor.execute("SELECT id FROM users WHERE id = {}".format(message["from"]["id"]))
        if users.cursor.fetchone():
            return

        users.cursor.execute(
            "INSERT INTO users VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
            (message["from"]["id"], message["from"]["first_name"], message["from"]["username"], "Пользователь", 30000, 1000000000, 0, 0, 0, 0, 0, 0, 0, 0, 0, regdata, ttime, 0, bio, 0, 1, "00:000:00", 0)
        )
        users.connect.commit()
        await bot.send_message(
            config.owner,
            "Новый пользователь!\nНик: {}\nID: {}\nЮзернейм: @{}\nЗарегистрировался(ась) в л/с.".format(message["from"]["first_name"], message["from"]["id"], message["from"]["username"])
        )
    else:
        users.cursor.execute("SELECT id FROM users WHERE id = {}".format(message["from"]["id"]))
        if users.cursor.fetchone():
            await message.reply('<b>Приветствую!</b> 👋\nЯ солевой бот PARANOIK.\n\nУзнать полный список функционала можно с помощью команды /help\n\n🗞 <a href="https://t.me/UFCRussia">Канал с новостями</a>\n\n💬 <a href="https://t.me/UFCRussiaChat">Наша общая беседа</a>')
            return

        users.cursor.execute(
            "INSERT INTO users VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
            (message["from"]["id"], message["from"]["first_name"], message["from"]["username"], "Пользователь", 30000, 1000000000, 0, 0, 0, 0, 0, 0, 0, 0, 0, regdata, ttime, 0, bio, 0, 1, "00:00:00", 0)
        )
        users.connect.commit()
        await bot.send_message(
            config.owner,
            "Новый пользователь!\nНик: {}\nID: {}\nЮзернейм: @{}\nЗарегистрировался(ась) в чате.".format(message["from"]["first_name"], message["from"]["id"], message["from"]["username"])
        )

        await message.reply('<b>Приветствую!</b> 👋\nЯ солевой бот PARANOIK.\n\nУзнать полный список функционала можно с помощью команды /help\n\n🗞 <a href="https://t.me/UFCRussia">Канал с новостями</a>\n\n💬 <a href="https://t.me/UFCRussiaChat">Наша общая беседа</a>')
    
    args = message.text.split()
    if len(args) <= 1:
        return

    try:
        users.cursor.execute('UPDATE users SET invited_users = invited_users + 1 WHERE id=?', (int(args[1]),))
        await bot.send_message(int(args[1]), "❤️ Кто-то только что зарегистрировался по твоей солевой ссылке!")
    except Exception:
        pass

#deluser
@dp.message_handler(commands=['deluser'])
async def deluser(message: types.Message):
    reply = message.reply_to_message
    status = (users.cursor.execute("SELECT status from users where id = ?", (message.from_user.id,)).fetchone())[0]

    if (status.lower() == 'создатель бота') or (status.lower() == "администратор"):
        if reply:
            users.cursor.execute("DELETE FROM users WHERE id = ?", (reply.from_user.id,))
            await message.reply(
                f"✅ | <b>{reply.from_user.get_mention(as_html=True)}</b> был успешно удалён из базы данных бота",
                parse_mode="html"
            )
    else:
        return await message.reply("❗ | У вас недостаточно прав для этого действия!")

#Передать
@dp.message_handler(regexp=r"(^Передать|передать) ?(\d+)?")
async def send_money(message: types.Message):
    command_parse = re.compile(r"(^Передать|передать) ?(\d+)?")
    parsed = command_parse.match(message.text)
    balance = users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone()
    balance = (balance[0])
    suma = parsed.group(2)
    name1 = message.reply_to_message.from_user.get_mention(as_html=True)
    name2 = message.from_user.get_mention(as_html=True)
    suma = int(suma)
    data = {}
    data["suma"] = suma
    data['user_id'] = message.reply_to_message.from_user.id
    data1 = {}
    data1["suma"] = suma
    data1['user_id'] = message.from_user.id
    id = message.from_user.id
    users.cursor.execute(f"SELECT id from users WHERE id = '{id}'")
    if users.cursor.fetchone() is None:
        await message.reply(f'Вы не зарегистрированы!\nВведите /start')
    else:
        if int(balance) >= suma:
            users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
            users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", data1)
            await message.answer(f"👤 | Пользователь: {name2}\n💸 | Передал(-а): <code>{suma}💰</code>\n👤 | Пользователю: {name1}", parse_mode='html')
        else:
            await message.reply(f"❎ | У вас недостаточно монет для передачи!", parse_mode='html')
            users.connect.commit()

#Отдать
@dp.message_handler(regexp=r"(^Отдать|отдать) ?(\d+)?")
async def send_money(message: types.Message):
    balance = users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone()
    balance = (balance[0])
    command_parse = re.compile(r"(^Отдать|отдать) ?(\d+)?")
    parsed = command_parse.match(message.text)
    suma = parsed.group(2)
    name1 = message.reply_to_message.from_user.get_mention(as_html=True)
    name2 = message.from_user.get_mention(as_html=True)
    suma = int(suma)
    data = {}
    data["suma"] = suma
    data['user_id'] = message.reply_to_message.from_user.id
    data1 = {}
    data1["suma"] = suma
    data1['user_id'] = message.from_user.id
    id = message.from_user.id
    users.cursor.execute(f"SELECT id from users WHERE id = '{id}'")
    if users.cursor.fetchone() is None:
        await message.reply(f'Вы не зарегистрированы!\nВведите /start')
    else:
        if int(balance) >= suma:
            users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
            users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", data1)
            await message.answer(f"👤 | Пользователь: {name2}\n💸 | Передал(-а): <code>{suma}💰</code>\n👤 | Пользователю: {name1}", parse_mode='html')
        else:
            await message.reply(f"❎ | У вас недостаточно монет для передачи!", parse_mode='html')
            users.connect.commit()

#helpui
@dp.message_handler(commands=['help', 'хелп', 'команды'], commands_prefix='!./')
async def help_ui(message):
    help_menu = InlineKeyboardMarkup()
    osnova_bt = InlineKeyboardButton(text = '📖 Основные', callback_data = 'osnova')
    games_bt = InlineKeyboardButton(text = '🎰 Игровые', callback_data = 'games')
    moders_bt = InlineKeyboardButton(text = '👮‍ Для модераторов', callback_data = 'moders')
    rolpl_bt = InlineKeyboardButton(text = '🎭 Role Play', callback_data = 'rolpl')
    cancel_help_bt = InlineKeyboardButton(text = '🚫 Закрыть', callback_data = 'cancel_help')
    help_menu.add(osnova_bt, games_bt)
    help_menu.add(rolpl_bt, moders_bt)
    help_menu.add(cancel_help_bt)
    await message.answer('Все команды бота:', reply_markup=help_menu)

@dp.callback_query_handler(text='cancel_help')
async def handle_help_cdel_button(c: types.CallbackQuery):
    await c.message.delete()

@dp.callback_query_handler(text='osnova')
async def handle_osnova_button(c: types.CallbackQuery):
    cancel_help_menu = InlineKeyboardMarkup()
    cancel_help_bt = InlineKeyboardButton(text = ' Назад', callback_data = 'cancelhelp')
    cancel_help_menu.add(cancel_help_bt)
    await c.message.edit_text(f"""📖 Основные команды:

✅ /start — начало пользования. 
📚 /help — список команд бота. 
👤 Профиль — открыть свой профиль в боте. 
✏️ /bio (текст) — установить описание. 
🗒 Био — вызвать описание. 
🏷 /name — сменить свой ник. 
💸 Передать (кол-во) — передать монеты пользователю.""", reply_markup=cancel_help_menu)

@dp.callback_query_handler(text='games')
async def handle_games_button(c: types.CallbackQuery):
    cancel_help_menu = InlineKeyboardMarkup()
    cancel_help_bt = InlineKeyboardButton(text = 'Назад', callback_data = 'cancelhelp')
    cancel_help_menu.add(cancel_help_bt)
    await c.message.edit_text(f"""🎰 Игровые команды:

💰 Баланс — баланс пользователя, синонимы команды: "Б".
🏦 Пополнить счёт (сумма) — пополнить свой банковский счёт. 
🏦 Снять со счёта (сумма) — снять деньги со своего банковского счёта. 
🕹 Мои игры — список всех ваших игр. 
🎱 Выбери от (число) до (число) — выбирает случайное число в указанном диапазоне. 
🎰 Казино (ставка) — игра в казино. 
🎲 Куб [1-6] (ставка) — игра в кости. 
🎯 Дартс (ставка) — игра в дартс. 
🏀 Бас (ставка) — игра в баскетбол. 
🎳 Боул (ставка) — игра в боулинг. 
⚽ Фут (ставка) — игра в футбол. 
🐇Охота (ставка) — сходить на охоту. 
🧩 Слоты (ставка) — игра в слоты.""", reply_markup=cancel_help_menu)

@dp.callback_query_handler(text='moders')
async def handle_moders_button(c: types.CallbackQuery):
    cancel_help_menu = InlineKeyboardMarkup()
    cancel_help_bt = InlineKeyboardButton(text = 'Назад', callback_data = 'cancelhelp')
    cancel_help_menu.add(cancel_help_bt)
    await c.message.edit_text(f"""👮‍ Команды для администраторов чата:

🕹 Разрешить игры —  разрешить участникам играть в чате. 
🕹 Запретить игры —  запретить участникам играть в чате. 
👮‍♂ Вкл модер — включить команды для модераторов в чате. 
👮‍♂ Выкл модер — выключить команды для модераторов в чате. 
🔇 /mute (время) (причина) — замутить пользователя. 
🔈 /unmute — размутить пользователя. 
🔴 /ban — забанить пользователя. 
🟢 /unban — разбанить пользователя. 
🗑 /del — удалить сообщение. 
🗓 /welcome (текст) — установить приветствие для новых пользователей. 
📜 /rules (текст) — установить правила чата. 
📖 Правила —  вызвать правила чата. 
📛 /report — отправить жалобу админам на участника чата.""", reply_markup=cancel_help_menu)

@dp.callback_query_handler(text='rolpl')
async def handle_rolpl_button(c: types.CallbackQuery):
    cancel_help_menu = InlineKeyboardMarkup()
    cancel_help_bt = InlineKeyboardButton(text = 'Назад', callback_data = 'cancelhelp')
    cancel_help_menu.add(cancel_help_bt)
    await c.message.edit_text(f"""🎭 Role play команды:

💬 /rp — кастомная РП команда. 
🍆 /dick — увеличить ялдак. 
🧰 /work — пойти на работу. 
🏆 Топ б — топ 15 богачей бота. 
🏆 Топ х — топ 15 ялдаков бота. 
🏆 Топ и — топ 15 игроков бота.""", reply_markup=cancel_help_menu)

@dp.callback_query_handler(text='cancelhelp')
async def cancel_help_button_handler(c: types.callback_query):
    help_menu = InlineKeyboardMarkup()
    osnova_bt = InlineKeyboardButton(text = '📖 Основные', callback_data = 'osnova')
    games_bt = InlineKeyboardButton(text = '🎰 Игровые', callback_data = 'games')
    moders_bt = InlineKeyboardButton(text = '👮‍ Для модераторов', callback_data = 'moders')
    rolpl_bt = InlineKeyboardButton(text = '🎭 Role Play', callback_data = 'rolpl')
    cancel_help_bt = InlineKeyboardButton(text = '🚫 Закрыть', callback_data = 'cancel_help')
    help_menu.add(osnova_bt, games_bt)
    help_menu.add(rolpl_bt, moders_bt)
    help_menu.add(cancel_help_bt)
    await c.message.edit_text(text='Все команды бота:', reply_markup=help_menu)

#work
@dp.message_handler(commands=['work', 'работа', 'работать'], commands_prefix='+!./')
async def work_cmd(message: types.Message):
    emoji = random.choice(["😴", "😶‍🌫️", "🫠", "🥶", "🤥", "🫡", "🤨", "😐", "🗿"])
    user_id = message['from']['id']
    users.cursor.execute("SELECT work_time FROM users WHERE id = {}".format(user_id))
    ltime = users.cursor.fetchone()[0]
    current_date_time = datetime.now()
    current_time = current_date_time.time()
    q = current_time.strftime('%H:%M:%S')
    a, b, t1, t2 = f'{ltime}'.split(':'), f'{q}'.split(':'), 0, 0
    for i in range(2, -1, -1):
        t1, t2 = t1 + 60**i*int(a[2-i]), t2 + 60**i*int(b[2-i])
    a = (86400 - t1) * int(t2 < t1) + t2 - t1 * int(not (t2 < t1))
    if a >= 7200:
        money_r = randint(5000, 15000)
        data = {}
        data["rand"] = (money_r)
        data['user_id'] = user_id
        balance = users.cursor.execute("SELECT balance FROM users WHERE id = ?",(user_id,)).fetchone()
        bal = (balance[0])
        await message.reply("👨‍💼 | Вы успешно сходили на работу и заработали: <b>{}💰</b>  \n💳 | Ваш баланс: <b>{}💰</b>".format(money_r, int(bal+money_r)))
        users.cursor.execute("""UPDATE users SET balance = balance + :rand WHERE id = :user_id;""", data)
        users.cursor.execute("UPDATE users SET work_time = ? WHERE id = ?", (q, user_id))
        users.connect.commit()
    else:
        balance = users.cursor.execute("SELECT balance FROM users WHERE id = ?",(user_id,)).fetchone()
        bal = (balance[0])
        await message.reply(f"{emoji} | Ходить на работу можно раз в 2 часа, идите посолитесь!\n💳 | Сейчас ваш баланс: <b>{bal}</b>💰")

#chatwelcome
@dp.message_handler(commands=["welcome"])
async def rules_cmd(message: types.Message):
    if message.chat.type == "supergroup" or message.chat.type == "group":
        user_id = message.from_user.id
        chat_id = message.chat.id
        new_welcome = message.get_args()
        admins_list = [admin.user.id for admin in await bot.get_chat_administrators(chat_id=chat_id)]
        if user_id in admins_list:
            if new_welcome:
                chats.cursor.execute("UPDATE chats SET welcome=? WHERE chat_id=?", (new_welcome, chat_id,))
                chats.connect.commit()
                await message.answer("👋 Приветствие чата было успешно изменено!")
            else:
                await message.answer("💬 Вы не указали новое приветствие!")
        else:
            await message.answer("🛡️ Вы не являетесь администратором этого чата!")
    else:
        await message.answer("Эта команда работает только в чатах!")

#chatwelcome_msg
@dp.message_handler(lambda msg: msg.text.lower() == 'приветствие')
async def chatwelcome_msg(message):
    if message.chat.type == "supergroup" or message.chat.type == "group":
        chat_id = message.chat.id
        chat_welcome = chats.cursor.execute("SELECT welcome FROM chats WHERE chat_id = ?", (chat_id,)).fetchone()
        welcome = (chat_welcome[0])
        await message.answer("👋 Приветствие чата:\n{}".format(welcome))
    else:
        await message.answer("Эта команда работает только в чатах!")

#Растить хуй
@dp.message_handler(commands=['хуй', 'ялдак', 'dick'], commands_prefix='+!./')
async def dick_cmd(message: types.Message):
    msg = message
    name = users.cursor.execute("SELECT name from users where id = ?",(msg.from_user.id,)).fetchone()
    name = (name[0])
    emoji = random.choice(["😶‍🌫️", "🫡", "🥶", "🤥", "😴", "🫠", "🤨", "😐", "🗿"])
    id = msg['from']['id']
    users.cursor.execute(f"SELECT dick_time FROM users WHERE id = '{id}'")
    ltime = users.cursor.fetchone()[0]
    current_date_time = datetime.now()
    current_time = current_date_time.time()
    q = current_time.strftime('%H:%M:%S')
    a, b, t1, t2 = f'{ltime}'.split(':'), f'{q}'.split(':'), 0, 0
    
    for i in range(2, -1, -1):
        t1, t2 = t1 + 60**i*int(a[2-i]), t2 + 60**i*int(b[2-i])
    a = (86400 - t1) * int(t2 < t1) + t2 - t1 * int(not (t2 < t1))
    
    if a >= 7200:
        dick_r = randint(-15, 30)
        data = {}
        data["rand"] = (dick_r)
        data['user_id'] = msg.from_user.id
        dick = users.cursor.execute("SELECT dick from users where id = ?",(msg.from_user.id,)).fetchone()
        dick = (dick[0])

        if dick_r > 0:
            await msg.reply(f'💦 | Вы увеличили свой ялдак на <b>{dick_r} см.</b>\n🍆 | Теперь его длина: <b>{dick + dick_r} см.</b>', parse_mode='html')
        else:
            await msg.reply(f'✂️ | Вы засолили свой ялдак на <b>{dick_r} см.</b>\n🍆 | Теперь его длина: <b>{dick + dick_r} см.</b>', parse_mode='html')
        
        users.cursor.execute("""UPDATE users SET dick = dick + :rand WHERE id = :user_id;""", data)
        users.cursor.execute('UPDATE users SET dick_time = ? WHERE id = ?', (q, id))
        users.connect.commit()
    else:
        dick = users.cursor.execute("SELECT dick from users where id = ?",(msg.from_user.id,)).fetchone()
        dick = (dick[0])
        await msg.reply(f'{emoji} | Увеличивать ялдак можно раз в 2 часа, приходи позже!\n🍆 | Сейчас его длина: <b>{dick} см.</b>', parse_mode='html')

#Установить ставку
@dp.message_handler(commands=['setstavka'])
async def setbal(message: types.Message):
    args = message.get_args()
    summ = int(args)
    users.cursor.execute("SELECT stavka FROM users WHERE id=?", (message.from_user.id,))
    data = users.cursor.fetchone()
    if data is None:
        await message.reply("Не найден в базе данных!")
    stts = users.cursor.execute("SELECT status from users where id = ?", (message.from_user.id,)).fetchone()
    status = (stts[0])
    if str(status) == 'Создатель бота':
        reply = message.reply_to_message
        if reply:
            replyuser = reply.from_user
            users.cursor.execute(f'UPDATE users SET stavka=? WHERE id=?', (summ, replyuser.id,))
            users.connect.commit()
            await message.reply(f"Максимальная ставка для {replyuser.full_name} изменена на {args} 💰")
    elif str(status) == 'Администратор':
        reply = message.reply_to_message
        if reply:
            replyuser = reply.from_user
            users.cursor.execute(f'UPDATE users SET stavka=? WHERE id=?', (summ, replyuser.id,))
            users.connect.commit()
            await message.reply(f"Максимальная ставка для {replyuser.full_name} изменена на {args} 💰")
        else:
            await message.reply(f"❗ | Необходим реплай!")
    else:
        return await message.reply(f"❗ | У вас недостаточно прав для того, чтобы взаимодействовать со ставками пользователей!")

#Установить хуй
@dp.message_handler(commands=['setdick'])
async def setdick(message: types.Message):
    args = message.get_args()
    summ = int(args)
    users.cursor.execute("SELECT dick FROM users WHERE id=?", (message.from_user.id,))
    data = users.cursor.fetchone()
    if data is None:
        await message.reply("Не найден в базе данных!")
    stts = users.cursor.execute("SELECT status from users where id = ?", (message.from_user.id,)).fetchone()
    status = (stts[0])
    if str(status) == 'Создатель бота':
        reply = message.reply_to_message
        if reply:
            replyuser = reply.from_user
            users.cursor.execute(f'UPDATE users SET dick=? WHERE id=?', (summ, replyuser.id,))
            users.connect.commit()
            await message.answer(f"Пользователю {replyuser.full_name}\nИзменили размер ялдака на {summ} см.")
    elif str(status) == 'Администратор':
        reply = message.reply_to_message
        if reply:
            replyuser = reply.from_user
            users.cursor.execute(f'UPDATE users SET dick=? WHERE id=?', (args, replyuser.id,))
            users.connect.commit()
            await message.answer(f"Пользователю {replyuser.full_name}\nИзменлили размер ялдака на <code>{summ} см.</code>")
        else:
            await message.reply(f"❗ | Необходим реплай!")
    else:
        return await message.reply(f"❗ | Ниялдакасе у вас недостаточно прав для того, чтобы взаимодействовать с ялдаками пользователей! 🙂")

#Своя рп
@dp.message_handler(commands=['rp'])
async def custom_rp(message: types.Message):
    args = message.get_args()
    reply = message.reply_to_message
    status = users.cursor.execute("SELECT status from users where id = ?", (message.from_user.id,)).fetchone()
    status = (status[0])
    id = message.from_user.id
    users.cursor.execute(f"SELECT id from users WHERE id = '{id}'")
    if users.cursor.fetchone() is None:
        await message.reply(f'Вы не зарегистрированы!\nВведите /start')
    else:
        if str(status) == 'Пользователь' or str(status) == 'Администратор' or str(status) == 'Создатель бота':
            if reply:
                if args:
                    name1 = message.from_user.get_mention(as_html=True)
                    name2 = message.reply_to_message.from_user.get_mention(as_html=True)
                    await message.answer(f'💬 | {name1} {args} {name2}')
                else:
                    await message.answer(f'📝 | Введите РП действие, пример: "/rp поцеловал"')
            else:
                if args:
                    name1 = message.from_user.get_mention(as_html=True)
                    await message.answer(f'💬 | {name1} {args}')
                else:
                    await message.answer(f'📝 | Введите РП действие, пример: "/rp пошёл в магазин"')
        else:
            await message.reply(f'Данная команда доступна лишь пользователям с VIP статусом 💎')

#Био
@dp.message_handler(commands=['bio'])
async def setbio(message: types.Message):
    args = message.get_args()
    name = message.from_user.get_mention(as_html=True)
    users.cursor.execute("SELECT bio FROM users WHERE id=?", (message.from_user.id,))
    data = users.cursor.fetchone()
    vip = users.cursor.execute("SELECT status from users where id = ?", (message.from_user.id,)).fetchone()
    vip = (vip[0])
    id = message.from_user.id
    users.cursor.execute(f"SELECT id from users WHERE id = '{id}'")
    if users.cursor.fetchone() is None:
        await message.reply(f'Вы не зарегистрированы!\nВведите /start')
    else:
        if str(vip) == 'Создатель бота' or str(vip) == 'Администратор' or str(vip) == 'Пользователь':
            if len(args) <= 350:
                if args:
                    if data is None:
                        return await message.reply("Не найден в базе данных!")
                    users.cursor.execute(f'UPDATE users SET bio=? WHERE id=?', (args, message.from_user.id,))
                    users.connect.commit()
                    await message.answer(f"📄 | Описание {str(name)} изменено!")
                else:
                    await message.reply('❎ | Ваше описание не может быть пустым!')
            else:
                await message.reply('❎ | Максимальная длина описания 350 символов!')
        else:
            await message.reply(f'Данная команда доступна лишь пользователям с VIP статусом 💎')

#Описание
@dp.message_handler(lambda message: message.text.lower() == 'био')
async def bio_text(message: types.Message):
    bio = users.cursor.execute("SELECT bio from users where id = ?", (message.from_user.id,)).fetchone()
    bio = (bio[0])
    vip = users.cursor.execute("SELECT status from users where id = ?", (message.from_user.id,)).fetchone()
    vip = (vip[0])
    id = message.from_user.id
    users.cursor.execute(f"SELECT id from users WHERE id = '{id}'")
    if users.cursor.fetchone() is None:
        await message.reply(f'Вы не зарегистрированы!\nВведите /start')
    else:
        if str(vip) == 'Создатель бота' or str(vip) == 'Администратор' or str(vip) == 'Пользователь':
            await message.reply(f'🗓 | Ваше описание профиля:\n{bio}')
        else:
            await message.reply(f'Данная команда доступна лишь пользователям с VIP статусом 💎')

#profile_msg
@dp.message_handler(lambda msg: ((msg.text.lower() == 'инфа') or (msg.text.lower() == "профиль")))
async def profile_msg(message):
    balance = (users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone())[0]
    name = (users.cursor.execute("SELECT name from users where id = ?", (message.from_user.id,)).fetchone())[0]
    status = (users.cursor.execute("SELECT status from users where id = ?", (message.from_user.id,)).fetchone())[0]
    games = (users.cursor.execute("SELECT games from users where id = ?", (message.from_user.id,)).fetchone())[0]
    stavka = (users.cursor.execute("SELECT stavka from users where id = ?", (message.from_user.id,)).fetchone())[0]
    dick = (users.cursor.execute("SELECT dick from users where id = ?", (message.from_user.id,)).fetchone())[0]
    regdata = (users.cursor.execute("SELECT regdata from users where id = ?", (message.from_user.id,)).fetchone())[0]
    invited_users = (users.cursor.execute("SELECT invited_users from users where id = ?", (message.from_user.id,)).fetchone())[0]

    users.cursor.execute(f"SELECT id from users WHERE id = '{message.from_user.id}'")
    if users.cursor.fetchone() is None:
        await message.reply(f'Вы не зарегистрированы!\nВведите /start')
    else:
        await message.reply(f"""📈 | Профиль пользователя
🏷 Никнейм: {name}
👤 Статус: {status}
💰 Баланс: <code>{balance}</code>
💰 Ставка: <code>{stavka}</code>
🎮 Всего игр: <b>{games}</b>
🍆 Длина ялдака: <b>{dick}</b> см.
🔗 Реферальная ссылка: <code>t.me/ELAS_game_bot?start={message.from_user.id}</code>
👥 Всего приглашено людей: {invited_users}
🕰 Дата регистрации: {regdata}""", parse_mode='html')

#stata_msg
@dp.message_handler(lambda msg: msg.text.lower() == 'стата')
async def stata_msg(message):
    msg = message
    balance = users.cursor.execute("SELECT balance from users where id = ?", (msg.from_user.id,)).fetchone()
    balance = (balance[0])
    name = users.cursor.execute("SELECT name from users where id = ?", (msg.from_user.id,)).fetchone()
    name = (name[0])
    status = users.cursor.execute("SELECT status from users where id = ?", (msg.from_user.id,)).fetchone()
    status = (status[0])
    games = users.cursor.execute("SELECT games from users where id = ?", (msg.from_user.id,)).fetchone()
    games = (games[0])
    stavka = users.cursor.execute("SELECT stavka from users where id = ?", (msg.from_user.id,)).fetchone()
    stavka = (stavka[0])
    dick = users.cursor.execute("SELECT dick from users where id = ?", (msg.from_user.id,)).fetchone()
    dick = (dick[0])
    regdata = users.cursor.execute("SELECT regdata from users where id = ?", (msg.from_user.id,)).fetchone()
    regdata = (regdata[0])
    id = message.from_user.id
    users.cursor.execute(f"SELECT id from users WHERE id = '{id}'")
    if users.cursor.fetchone() is None:
        await message.reply(f'Вы не зарегистрированы!\nВведите /start')
    else:
        await msg.reply(f"""📈 | Профиль пользователя
📎 Никнейм: {name}
👤 Статус: {status}
💰 Баланс: <code>{balance}</code>
💰 Ставка: <code>{stavka}</code>
🎮 Всего игр: <b>{games}</b>
🍆 Длина ялдака: <b>{dick}</b> см.
🕰 Дата регистрации: {regdata}""", parse_mode='html')

#info_msg
@dp.message_handler(lambda msg: msg.text.lower() == 'инфо')
async def info_msg(message):
    msg = message
    balance = users.cursor.execute("SELECT balance from users where id = ?", (msg.from_user.id,)).fetchone()
    balance = (balance[0])
    name = users.cursor.execute("SELECT name from users where id = ?", (msg.from_user.id,)).fetchone()
    name = (name[0])
    status = users.cursor.execute("SELECT status from users where id = ?", (msg.from_user.id,)).fetchone()
    status = (status[0])
    games = users.cursor.execute("SELECT games from users where id = ?", (msg.from_user.id,)).fetchone()
    games = (games[0])
    stavka = users.cursor.execute("SELECT stavka from users where id = ?", (msg.from_user.id,)).fetchone()
    stavka = (stavka[0])
    dick = users.cursor.execute("SELECT dick from users where id = ?", (msg.from_user.id,)).fetchone()
    dick = (dick[0])
    regdata = users.cursor.execute("SELECT regdata from users where id = ?", (msg.from_user.id,)).fetchone()
    regdata = (regdata[0])
    id = message.from_user.id
    users.cursor.execute(f"SELECT id from users WHERE id = '{id}'")
    if users.cursor.fetchone() is None:
        await message.reply(f'Вы не зарегистрированы!\nВведите /start')
    else:
        await msg.reply(f"""📈 | Профиль пользователя
📎 Никнейм: {name}
👤 Статус: {status}
💰 Баланс: <code>{balance}</code>
💰 Ставка: <code>{stavka}</code>
🎮 Всего игр: <b>{games}</b>
🍆 Длина ялдака: <b>{dick}</b> см.
🕰 Дата регистрации: {regdata}""", parse_mode='html')

#admin_cmd
@dp.message_handler(commands=['admins_cmd'])
async def admins_cmd(message: types.Message):
    status = users.cursor.execute("SELECT status from users where id = ?", (message.from_user.id,)).fetchone()
    status = (status[0])
    if str(status) == 'Администратор' or str(status) == 'Создатель бота':
        await message.reply(f"""Команды для администраторв бота:
"Выдать (количество)" - выдать монеты пользоватлею
"Забрать (количество)" - забрать монеты у пользователя
/setbal - изменить баланс пользователю
/setdick - изменить длину ялдака пользователю
/setstavka - изменить макс. ставку для пользователя
/user_status или /chat_status - изменить статус пользователя/чата""")
    else:
        pass

#chatrules_msg
@dp.message_handler(lambda msg: msg.text.lower() == 'правила')
async def chatrules_msg(message):
    if message.chat.type == "supergroup" or message.chat.type == "group":
        chat_id = message.chat.id
        chat_rules = chats.cursor.execute("SELECT rules FROM chats WHERE chat_id = ?", (chat_id,)).fetchone()
        rules = (chat_rules[0])
        await message.answer("Правила чата:\n\n{}".format(rules))
    else:
        await message.answer("Эта команда работает только в чатах!")

#chatrules
@dp.message_handler(commands=["rules"])
async def rules_cmd(message: types.Message):
    if message.chat.type == "supergroup" or message.chat.type == "group":
        user_id = message.from_user.id
        chat_id = message.chat.id
        new_rules = message.get_args()
        admins_list = [admin.user.id for admin in await bot.get_chat_administrators(chat_id=chat_id)]
        if user_id in admins_list:
            if new_rules:
                chats.cursor.execute("UPDATE chats SET rules=? WHERE chat_id=?", (new_rules, chat_id,))
                chats.connect.commit()
                await message.answer("📑 Правила чата были успешно изменены!")
            else:
                await message.answer("💬 Вы не указали новые правила!")
        else:
            await message.answer("🛡️ Вы не являетесь администратором этого чата!")
    else:
        await message.answer("Эта команда работает только в чатах!")

#chatinfo
@dp.message_handler(commands=['chatinfo', 'чатинфо'], commands_prefix='./')
async def chatinfo_cmd(message: types.Message):
    msg = message
    chat_name = chats.cursor.execute("SELECT chat_name from chats where chat_id = ?", (msg.chat.id,)).fetchone()
    chat_name = (chat_name[0])
    chat_username = chats.cursor.execute("SELECT chat_username from chats where chat_id = ?", (msg.chat.id,)).fetchone()
    chat_username = (chat_username[0])
    chat_status = chats.cursor.execute("SELECT chat_status from chats where chat_id = ?", (msg.chat.id,)).fetchone()
    chat_status = (chat_status[0])
    chat_games = chats.cursor.execute("SELECT chat_games from chats where chat_id = ?", (msg.chat.id,)).fetchone()
    chat_games = (chat_games[0])
    game_rule = chats.cursor.execute("SELECT game_rule from chats where chat_id = ?", (msg.chat.id,)).fetchone()
    game_rule = (game_rule[0])
    reg_data = chats.cursor.execute("SELECT reg_data from chats where chat_id = ?", (msg.chat.id,)).fetchone()
    reg_data = (reg_data[0])
    members = await message.chat.get_members_count()
    admins_id = [(admin.user.id) for admin in await bot.get_chat_administrators(chat_id=message.chat.id)]
    if str(chat_status) == 'Официальный':
        stat = "✅"
    elif str(chat_status) == 'Администраторский':
        stat = "‍👨‍💻️"
    elif str(chat_status) == 'VIP чат':
        stat = "💎"
    elif str(chat_status) == 'Обычный':
        stat = "👥"
    if str(game_rule) == 'разрешено':
        rule = "✅"
    elif str(game_rule) == 'запрещено':
        rule = "❎"
    await msg.answer(f"""Информация о чате:
🗒️ | Название: {chat_name}
📎 | Ссылка: @{chat_username}
🕰 | Дата регистрации: {reg_data}
{stat} | Статус: {chat_status}
🎮 | Игр сыграно: {chat_games}
{rule} | Играть в чате {game_rule}
👤 | Количество участников: {members}
👮‍♂️ | Администраторов в чате: {len(admins_id)}""")

#set_name
@dp.message_handler(commands=['name'])
async def set_name(message: types.Message):
    msg = message
    args = msg.get_args()
    uname = msg.from_user.username
    id = msg.from_user.id
    users.cursor.execute("SELECT id FROM users WHERE id=?", (message.from_user.id,))
    data = users.cursor.fetchone()
    if len(args) <= 15:
        if args:
            if data is None:
                return await msg.reply("🤔 | Вы не были найдены в базе данных бота, введите /start для регистрации")
            users.cursor.execute(f'UPDATE users SET name=? WHERE id=?', (args, id,))
            users.cursor.execute(f'UPDATE users SET username=? WHERE id=?', (uname, id,))
            users.connect.commit()
            await msg.reply(f"📝 | Ваш ник изменён на «{args}»")
        else:
            await msg.reply('❎ | Ник не может быть пустым!')
    else:
        await msg.reply('❎ | Максимальная длина ника должна составлять 15 символов!')

#статусы
@dp.message_handler(lambda msg: msg.text.lower() == 'статусы')
async def statuses_msg(message):
    msg = message
    name = msg.from_user.get_mention
    await msg.answer(f"""Все статусы пользователей:
👤 | Пользователь - по умолчанию
👮‍♂️ | Администратор  - член команды администрации бота 
👨‍💻 | Создатель бота - кодер

Все статусы чатов:
👥 | Обычный - по умолчанию 
✅ | Официальный - официальные чаты сетки бота 
👨‍💻 | Администраторский - чаты для администраторов бота""")

#репорт
@dp.message_handler(commands=['r', 'report'])
async def cmd_report(message: types.Message):
    try:
        if message.text == '/report' or message.text == '/r' or not message.reply_to_message:
            await bot.send_message(message.chat.id, '📖 Введите причину репорта отвечая на сообщение с нарушением, пример: \n<code>/report спам/реклама</code>')
        else:
            members = await message.chat.get_member(message.reply_to_message.from_user.id)
            info = await bot.get_chat_member(message.chat.id, message.from_user.id)
            report = message.text.replace('/r ', '')
            report = report.replace('/report ', '')
            admins = await bot.get_chat_administrators('@' + message.chat.username)
            send = 0
            for admin in admins:
                if admin.user.username != 'HegaGameBot':
                    try:
                        await bot.send_message(admin.user.id, f'📬 Репорт по причине: ' + str(report) + f'\n\nhttps://t.me/{message.chat.username}/{message.reply_to_message.message_id}')
                    except:
                        pass
                    send += 1

            if send == 0:
                await bot.send_message(message.chat.id, '👮Админы не оповещены, для отправки им репортов надо чтобы они запустили меня в лс!')
            else:
                await bot.send_message(message.chat.id, '👮Админы оповещены!')
    except:
        pass

#+модер
@dp.message_handler(lambda msg: msg.text.lower() == 'вкл модер')
async def moder_on(message):
    name = message.from_user.get_mention()
    chat_username = message.chat.username
    admins_list = [admin.user.id for admin in await bot.get_chat_administrators(chat_id=message.chat.id)]
    stts = users.cursor.execute("SELECT status from users where id = ?", (message.from_user.id,)).fetchone()
    status = (stts[0])
    id = message.from_user.id
    users.cursor.execute(f"SELECT id from users WHERE id = '{id}'")
    if users.cursor.fetchone() is None:
        await message.reply(f'Вы не зарегистрированы!\nВведите /start')
    else:
        if message.from_user.id in admins_list or str(status) == 'Создатель бота':
            mod_cmd = chats.cursor.execute("SELECT mod_cmd from chats where chat_id = ?", (message.chat.id,)).fetchone()
            mod_cmd = (mod_cmd[0])
            if str(mod_cmd) == 'да':
                await message.reply(f'❎ | В этом чате команды для модераторов включены!')
            else:
                chats.cursor.execute('UPDATE chats SET mod_cmd = ? WHERE chat_id = ?', ("да", message.chat.id))
                chats.connect.commit()
                await message.answer(f'✅ | В этом чате команды для модераторов теперь разрешены!')
                await bot.send_message(config.owner, f'{name} разрешил модер. команды в чате @{chat_username}')
        else:
            await message.reply(f'👮‍♂️❎ | Вы не являетесь администратором этого чата!')

#-модер
@dp.message_handler(lambda msg: msg.text.lower() == 'выкл модер')
async def moder_off(message):
    name = message.from_user.get_mention()
    chat_username = message.chat.username
    admins_list = [admin.user.id for admin in await bot.get_chat_administrators(chat_id=message.chat.id)]
    stts = users.cursor.execute("SELECT status from users where id = ?", (message.from_user.id,)).fetchone()
    status = (stts[0])
    id = message.from_user.id
    users.cursor.execute(f"SELECT id from users WHERE id = '{id}'")
    if users.cursor.fetchone() is None:
        await message.reply(f'Вы не зарегистрированы!\nВведите /start')
    else:
        if message.from_user.id in admins_list or str(status) == 'Создатель бота':
            mod_cmd = chats.cursor.execute("SELECT mod_cmd from chats where chat_id = ?", (message.chat.id,)).fetchone()
            mod_cmd = (mod_cmd[0])
            if str(mod_cmd) == 'нет':
                await message.reply(f'❎ | В этом чате команды для модераторов выключены!')
            else:
                chats.cursor.execute('UPDATE chats SET mod_cmd = ? WHERE chat_id = ?', ("нет", message.chat.id))
                chats.connect.commit()
                await message.answer(f'✅ | В этом чате команды для модераторов теперь запрещены!')
                await bot.send_message(config.owner, f'{name} запретил модер. команды в чате @{chat_username}')
        else:
            await message.reply(f'👮‍♂️❎ | Вы не являетесь администратором этого чата!')

#Мут
@dp.message_handler(commands=['мут', 'mute'], commands_prefix='!?./', is_chat_admin=True)
async def mute(message):
    msg = message
    name1 = msg.from_user.get_mention()
    name2 = msg.reply_to_message.from_user.get_mention()
    mod_cmd = chats.cursor.execute("SELECT mod_cmd from chats where chat_id = ?", (message.chat.id,)).fetchone()
    mod_cmd = (mod_cmd[0])
    if str(mod_cmd) == 'да':
        if not message.reply_to_message:
            await message.reply("Эта команда должна быть ответом на сообщение!")
            return
        try:
            muteint = int(message.text.split()[1])
            mutetype = message.text.split()[2]
            comment = " ".join(message.text.split()[3:])
        except IndexError:
            await message.reply('❎ | Пример: <code>/мут 1 ч причина</code>')
            return
        if str(comment) != '':
            if mutetype == "ч" or mutetype == "часов" or mutetype == "час" or mutetype == "часа":
                await bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, types.ChatPermissions(False), until_date=timedelta(hours=muteint))
                await message.answer(f'👤 | Модератор: {name1}\n🔇 | Замутил(-а): {name2}\n🛡 ️| ID наказуемого: <code>{message.reply_to_message.from_user.id}</code>\n🕰 | Длительность мута: {muteint} {mutetype}\n💬 | Причина: {comment}')
            if mutetype == "м" or mutetype == "минут" or mutetype == "минуты" or mutetype == "минута":
                await bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, types.ChatPermissions(False), until_date=timedelta(minutes=muteint))
                await message.answer(f'👤 | Модератор: {name1}\n🔇 | Замутил(-а): {name2}\n🛡 ️| ID наказуемого: <code>{message.reply_to_message.from_user.id}</code>\n🕰 | Длительность мута: {muteint} {mutetype}\n💬 | Причина: {comment}')
            if mutetype == "д" or mutetype == "дней" or mutetype == "день" or mutetype == "дня":
                await bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, types.ChatPermissions(False), until_date=timedelta(days=muteint))
                await message.answer(f'👤 | Модератор: {name1}\n🔇 | Замутил(-а): {name2}\n🛡 ️| ID наказуемого: <code>{message.reply_to_message.from_user.id}</code>\n🕰 | Длительность мута: {muteint} {mutetype}\n💬 | Причина: {comment}')
        else:
            if mutetype == "ч" or mutetype == "часов" or mutetype == "час" or mutetype == "часа": 
                await bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, types.ChatPermissions(False), until_date=timedelta(hours=muteint))
                await message.answer(f'👤 | Модератор: {name1}\n🔇 | Замутил(-а): {name2}\n🛡 ️| ID наказуемого: <code>{message.reply_to_message.from_user.id}</code>\n🕰 | Длительность мута: {muteint} {mutetype}')
            if mutetype == "м" or mutetype == "минут" or mutetype == "минуты" or mutetype == "минута":
                await bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, types.ChatPermissions(False), until_date=timedelta(minutes=muteint))
                await message.answer(f'👤 | Модератор: {name1}\n🔇 | Замутил(-а): {name2}\n🛡 ️| ID наказуемого: <code>{message.reply_to_message.from_user.id}</code>\n🕰 | Длительность мута: {muteint} {mutetype}')
            if mutetype == "д" or mutetype == "дней" or mutetype == "день" or mutetype == "дня":
                await bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, types.ChatPermissions(False), until_date=timedelta(days=muteint))
                await message.answer(f'👤 | Модератор: {name1}\n🔇 | Замутил(-а): {name2}\n🛡 ️| ID наказуемого: <code>{message.reply_to_message.from_user.id}</code>\n🕰 | Длительность мута: {muteint} {mutetype}')
    else:
        pass

#Анмут
@dp.message_handler(commands=['анмут', 'размут', 'unmute'], commands_prefix='!?./', is_chat_admin=True)
async def unmute(message):
    msg = message
    name1 = msg.from_user.get_mention()
    name2 = msg.reply_to_message.from_user.get_mention()
    mod_cmd = chats.cursor.execute("SELECT mod_cmd from chats where chat_id = ?", (message.chat.id,)).fetchone()
    mod_cmd = (mod_cmd[0])
    if str(mod_cmd) == 'да':
        if not message.reply_to_message:
            await message.reply("Эта команда должна быть ответом на сообщение!")
            return
        await bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, types.ChatPermissions(True, True, True, True))
        await message.reply(f'👤 | Модератор: {name1}\n📢 | Размутил(-а): {name2}')
        await bot.send_message(message.reply_to_message.from_user.id, f'✅ | Вы больше не обеззвучены в чате: @{message.chat.username}')
    else:
        pass

# Бан | Кик
@dp.message_handler(commands=['бан', 'ban'], commands_prefix='!?./', is_chat_admin=True)
async def ban(message):
    msg = message
    name1 = msg.from_user.get_mention()
    name2 = msg.reply_to_message.from_user.get_mention()
    mod_cmd = chats.cursor.execute("SELECT mod_cmd from chats where chat_id = ?", (message.chat.id,)).fetchone()
    mod_cmd = (mod_cmd[0])
    if str(mod_cmd) == 'да':
        if not message.reply_to_message:
            await message.reply("Эта команда должна быть ответом на сообщение!")
            return
        try:
            banint = int(message.text.split()[1])
            bantype = message.text.split()[2]
            comment = " ".join(message.text.split()[3:])
        except IndexError:
            await message.reply('❎ | Пример: <code>/бан 1 ч причина</code>')
            return
        if str(comment) != '':
            if bantype == "ч" or bantype == "часов" or bantype == "час" or bantype == "часа": 
                await bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id, until_date=timedelta(hours=banint))
                await message.answer(f'👤 | Модератор: {name1}\n🔇 | Забанил(-а): {name2}\n🛡 ️| ID наказуемого: <code>{message.reply_to_message.from_user.id}</code>\n🕰 | Длительность бана: {banint} {bantype}\n💬 | петушары: {comment}')
            if bantype == "м" or bantype == "минут" or bantype == "минуты" or bantype  == "минута":
                await bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id, until_date=timedelta(minutes=banint))
                await message.answer(f'👤 | Модератор: {name1}\n🔇 | Забанил(-а): {name2}\n🛡 ️| ID петушары: <code>{message.reply_to_message.from_user.id}</code>\n🕰 | Длительность бана: {banint} {bantype}\n💬 | Причина: {comment}')
            if bantype == "д" or bantype == "дней" or bantype == "день" or bantype == "дня":
                await bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id, until_date=timedelta(days=banint))
                await message.answer(f'👤 | Модератор: {name1}\n🔇 | Забанил(-а): {name2}\n🛡 ️| ID петушары: <code>{message.reply_to_message.from_user.id}</code>\n🕰 | Длительность бана: {banint} {bantype}\n💬 | Причина: {comment}')
        else:
            if bantype == "ч" or bantype == "часов" or bantype == "час" or bantype == "часа":
                await bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id, until_date=timedelta(hours=banint))
                await message.answer(f'👤 | Модератор: {name1}\n🔇 | Забанил(-а): {name2}\n🛡 ️| ID петушары: <code>{message.reply_to_message.from_user.id}</code>\n🕰 | Длительность бана: {banint} {bantype}')
            if bantype == "м" or bantype == "минут" or bantype == "минуты" or bantype == "минута":
                await bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id, until_date=timedelta(minutes=banint))
                await message.answer(f'👤 | Модератор: {name1}\n🔇 | Забанил(-а): {name2}\n🛡 ️| ID петушары: <code>{message.reply_to_message.from_user.id}</code>\n🕰 | Длительность бана: {banint} {bantype}')
            if bantype == "д" or bantype == "дней" or bantype == "день" or bantype == "дня ":
                await bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id, until_date=timedelta(days=banint))
                await message.answer(f'👤 | Модератор: {name1}\n🔇 | Забанил(-а): {name2}\n🛡 ️| ID петушары: <code>{message.reply_to_message.from_user.id}</code>\n🕰 | Длительность бана: {banint} {bantype}')
    else:
        pass

#Разбан
@dp.message_handler(commands=['разбан', 'unban'], commands_prefix='!?./', is_chat_admin=True)
async def unban(message):
    msg = message
    name1 = msg.from_user.get_mention()
    name2 = msg.reply_to_message.from_user.get_mention()
    mod_cmd = chats.cursor.execute("SELECT mod_cmd from chats where chat_id = ?", (message.chat.id,)).fetchone()
    mod_cmd = (mod_cmd[0])
    if str(mod_cmd) == 'да':
        if not msg.reply_to_message:
            await msg.reply("Эта команда должна быть ответом на сообщение!")
            return
        await bot.restrict_chat_member(msg.chat.id, msg.reply_to_message.from_user.id, types.ChatPermissions(True, True, True, True))
        await msg.reply(f'👤 | Модератор: {name1}\n📢 | Разбанил(-а): {name2}')
        await bot.send_message(message.reply_to_message.from_user.id, f'✅ | Вы больше не забанены в чате: @{message.chat.username}')
    else:
        pass

#Удаление сообщения
@dp.message_handler(chat_type=[types.ChatType.SUPERGROUP, types.ChatType.GROUP], commands=['del'], commands_prefix='!/')
async def delete_message(message: types.Message):
    admins_list = [admin.user.id for admin in await bot.get_chat_administrators(chat_id=message.chat.id)]
    if message.from_user.id in admins_list:
        mod_cmd = chats.cursor.execute("SELECT mod_cmd from chats where chat_id = ?", (message.chat.id,)).fetchone()
        mod_cmd = (mod_cmd[0])
        if str(mod_cmd) == 'да':
            msg_id = message.reply_to_message.message_id
            await bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            await message.answer(f'🗳️ | Сообщение удалено!')
        else:
            pass

#Статистика игр
@dp.message_handler(lambda msg: msg.text.lower() == 'мои игры')
async def mygames(message):
    id = message.from_user.id
    users.cursor.execute(f"SELECT id from users WHERE id = '{id}'")
    if users.cursor.fetchone() is None:
        await message.reply(f'Вы не зарегистрированы!\nВведите /start')
    else:
        casino = users.cursor.execute("SELECT casino from users where id = ?", (message.from_user.id,)).fetchone()
        casino = (casino[0])
        kosti = users.cursor.execute("SELECT kosti from users where id = ?", (message.from_user.id,)).fetchone()
        kosti = (kosti[0])
        darts = users.cursor.execute("SELECT darts from users where id = ?", (message.from_user.id,)).fetchone()
        darts = (darts[0])
        bouling = users.cursor.execute("SELECT bouling from users where id = ?", (message.from_user.id,)).fetchone()
        bouling = (bouling[0])
        footbal = users.cursor.execute("SELECT footbal from users where id = ?", (message.from_user.id,)).fetchone()
        footbal = (footbal[0])
        basket = users.cursor.execute("SELECT basket from users where id = ?", (message.from_user.id,)).fetchone()
        basket = (basket[0])
        ohota = users.cursor.execute("SELECT ohota from users where id = ?", (message.from_user.id,)).fetchone()
        ohota = (ohota[0])
        slots = users.cursor.execute("SELECT slots from users where id = ?", (message.from_user.id,)).fetchone()
        slots = (slots[0])
        await message.answer(f"""📈 | Статистика ваших игр
Казино: <b>{casino}</b> 🎰
Кости: <b>{kosti}</b> 🎲
Дартс: <b>{darts}</b> 🎯
Боулинг: <b>{bouling}</b> 🎳
Футбол: <b>{footbal}</b> ⚽
Баскетбол: <b>{basket}</b> 🏀
Охота: <b>{ohota}</b> 🔫
Слоты: <b>{slots}</b> 🧩""")

#Разрешить игры
@dp.message_handler(lambda msg: msg.text.lower() == 'разрешить игры')
async def games_on(message):
    name = message.from_user.get_mention()
    chat_username = message.chat.username
    admins_list = [admin.user.id for admin in await bot.get_chat_administrators(chat_id=message.chat.id)]
    stts = users.cursor.execute("SELECT status from users where id = ?", (message.from_user.id,)).fetchone()
    status = (stts[0])
    id = message.from_user.id
    users.cursor.execute(f"SELECT id from users WHERE id = '{id}'")
    if users.cursor.fetchone() is None:
        await message.reply(f'Вы не зарегистрированы!\nВведите /start')
    else:
        if message.from_user.id in admins_list or str(status) == 'Создатель бота':
            game_rule = chats.cursor.execute("SELECT game_rule from chats where chat_id = ?", (message.chat.id,)).fetchone()
            game_rule = (game_rule[0])
            if str(game_rule) == 'разрешено':
                await message.reply(f'🎮❗| В этом чате игры уже разрешены!')
            else:
                chats.cursor.execute('UPDATE chats SET game_rule = ? WHERE chat_id = ?', ("разрешено", message.chat.id))
                chats.connect.commit()
                await message.answer(f'🎮✅ | В этом чате игры теперь разрешены!')
                await bot.send_message(config.owner, f'{name} разрешил игры в чате @{chat_username}')
        else:
            await message.reply(f'👮‍♂️❎ | Вы не являетесь администратором этого чата!')

#Запретить игры
@dp.message_handler(lambda msg: msg.text.lower() == 'запретить игры')
async def games_off(message):
    name = message.from_user.get_mention()
    chat_username = message.chat.username
    admins_list = [admin.user.id for admin in await bot.get_chat_administrators(chat_id=message.chat.id)]
    stts = users.cursor.execute("SELECT status from users where id = ?", (message.from_user.id,)).fetchone()
    status = (stts[0])
    id = message.from_user.id
    users.cursor.execute(f"SELECT id from users WHERE id = '{id}'")
    if users.cursor.fetchone() is None:
        await message.reply(f'Вы не зарегистрированы!\nВведите /start')
    else:
        if message.from_user.id in admins_list or str(status) == 'Создатель бота':
            game_rule = chats.cursor.execute("SELECT game_rule from chats where chat_id = ?", (message.chat.id,)).fetchone()
            game_rule = (game_rule[0])
            if str(game_rule) == 'запрещено':
                await message.reply(f'🎮❗| В этом чате игры уже запрещены!')
            else:
                chats.cursor.execute('UPDATE chats SET game_rule = ? WHERE chat_id = ?', ("запрещено", message.chat.id))
                chats.connect.commit()
                await message.answer(f'🎮❎ | В этом чате игры теперь запрещены!')
                await bot.send_message(config.owner, f'{name} запретил игры в чате @{chat_username}')
        else:
            await message.reply(f'👮‍♂️❎ | Вы не являетесь администратором этого чата!')

#Выдать
@dp.message_handler(regexp=r"(^Выдать|выдать) ?(\d+)?")
async def vidat(message: types.Message):
    command_parse = re.compile(r"(^Выдать|выдать) ?(\d+)?")
    parsed = command_parse.match(message.text)
    suma = parsed.group(2)
    name1 = message.from_user.get_mention(as_html=True)
    name2 = message.reply_to_message.from_user.get_mention(as_html=True)
    data = {}
    data["suma"] = suma
    data['user_id'] = message.reply_to_message.from_user.id
    stts = users.cursor.execute("SELECT status from users where id = ?", (message.from_user.id,)).fetchone()
    status = (stts[0])
    if str(status) == 'Администратор':
        if suma is None:
            await message.reply(f'Введите число!')
        else:
            users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
            await message.answer(f"Администратор: {name1}\nВыдал: {suma} 💰\nПользователю: {name2}", parse_mode='html')
            await bot.send_message(config.owner, f'{name1} выдал {suma}💰 пользователю {name2}')
    elif str(status) == 'Создатель бота':
        if suma is None:
            await message.reply(f'Введите число!')
        else:
            users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
            await message.answer(f"Администратор: {name1}\nВыдал: {suma} 💰\nПользователю: {name2}", parse_mode='html')
    else:
        await message.reply(f"🚫 | У вас недостаточно прав для того, чтобы взаимодействовать с балансами пользователей!", parse_mode='html')
    users.connect.commit()

#Забрать
@dp.message_handler(regexp=r"(^Забрать|забрать) ?(\d+)?")
async def zabrat(message: types.Message):
    command_parse = re.compile(r"(^Забрать|забрать) ?(\d+)?")
    parsed = command_parse.match(message.text)
    suma = parsed.group(2)
    name1 = message.from_user.get_mention(as_html=True)
    name2 = message.reply_to_message.from_user.get_mention(as_html=True)
    data = {}
    data["suma"] = suma
    data['user_id'] = message.reply_to_message.from_user.id
    stts = users.cursor.execute("SELECT status from users where id = ?", (message.from_user.id,)).fetchone()
    status = (stts[0])
    if str(status) == 'Администратор':
        if suma is None:
            await message.reply(f'Введите число!')
        else:
            users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", data)
            await message.answer(f"Администратор: {name1}\nЗабрал: {suma} 💰\nУ пользователя: {name2}", parse_mode='html')
            await bot.send_message(config.owner, f'{name1} забрал {suma}💰 у пользователя {name2}')
    elif str(status) == 'Создатель бота':
        if suma is None:
            await message.reply(f'Введите число!')
        else:
            users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", data)
            await message.answer(f"Администратор: {name1}\nЗабрал: {suma} 💰\nУ пользователя: {name2}", parse_mode='html')
    else:
        await message.reply(f"🚫 | У вас недостаточно прав для того, чтобы взаимодействовать с балансами пользователей!", parse_mode='html')
    users.connect.commit()

#Установить баланс
@dp.message_handler(commands=['setbal'])
async def setbal(message: types.Message):
    args = message.get_args()
    summ = int(args)
    users.cursor.execute("SELECT balance FROM users WHERE id=?", (message.from_user.id,))
    data = users.cursor.fetchone()
    if data is None:
        await message.reply("Не найден в базе данных!")
    stts = users.cursor.execute("SELECT status from users where id = ?", (message.from_user.id,)).fetchone()
    status = (stts[0])
    if str(status) == 'Создатель бота':
        reply = message.reply_to_message
        if reply:
            replyuser = reply.from_user
            users.cursor.execute(f'UPDATE users SET balance=? WHERE id=?', (summ, replyuser.id,))
            users.connect.commit()
            await message.answer(f"Пользователю: {replyuser.full_name}\nИзменлили баланс на: {summ} 💰")
    elif str(status) == 'Администратор':
        reply = message.reply_to_message
        if reply:
            replyuser = reply.from_user
            users.cursor.execute(f'UPDATE users SET balance=? WHERE id=?', (args, replyuser.id,))
            users.connect.commit()
            await message.answer(f"Пользователю: {replyuser.full_name}\nИзменлили баланс на: {summ} 💰")
        else:
            await message.reply(f"❗ | Необходим реплай!")
    else:
        return await message.reply(f"❗ | У вас недостаточно прав для того, чтобы взаимодействовать с балансами пользователей!")

#user_status
@dp.message_handler(commands=['user_status'])
async def set_user_status(message: types.Message):
    msg = message
    id = msg.from_user.id
    stata = msg.get_args()
    status = users.cursor.execute("SELECT status from users where id = ?", (message.from_user.id,)).fetchone()
    status = (status[0])
    name_link = users.cursor.execute("SELECT name from users where id = ?", (msg.reply_to_message.from_user.id,)).fetchone()
    name_link = (name_link[0])
    status_rep = users.cursor.execute("SELECT status from users where id = ?", (msg.reply_to_message.from_user.id,)).fetchone()
    status_rep = (status_rep[0])
    emoji = random.choice(["😐", "🤨", "😔", "😟"])
    if str(status) == 'Создатель бота' or int(id) == config.owner:
        if str(stata) == 'Создатель бота' or str(stata) == 'Администратор' or str(stata) == 'VIP юзер' or str(stata) == 'Пользователь':
            users.cursor.execute('UPDATE users SET status = ? WHERE id = ?', (stata, msg.reply_to_message.from_user.id))
            users.connect.commit()
            await msg.answer(f'✅ | Успешно!\nПользователь: {name_link}\nПолучил(-а) статус: {stata}')
        else:
            await msg.reply(f'{emoji} | Таких статусов нет!\nВведите "статусы", чтобы увидеть список доступных статусов')
    elif str(status) == 'Администратор':
        if msg['reply_to_message']['from']['id'] != msg['from']['id']:
            if str(stata) == 'VIP юзер' or str(stata) == 'Пользователь':
                if str(stata_rep) == 'Создатель бота' or str(stata_rep) == 'Администратор':
                    users.cursor.execute('UPDATE users SET status = ? WHERE id = ?', (stata, msg.reply_to_message.from_user.id))
                    users.connect.commit()
                    await msg.answer(f'✅ | Успешно!\nПользователь: {name_link}\nПолучил(-а) статус: {stata}')
                else:
                    await msg.reply(f'{emoji} | У вас недостаточный ранг, чтобы менять статус этого пользователя!')
            else:
                await msg.reply(f'{emoji} | Таких статусов нет или у вас недостаточный ранг для изменения статуса этого пользователя!')
        else:
            await msg.reply(f'{emoji} | Нельзя выдать статус самому себе')
    else:
        await msg.reply(f'{emoji} | Вы не являетесь администратором бота!')

#chat_status
@dp.message_handler(commands=['chat_status'])
async def set_chat_status(message: types.Message):
    msg = message
    stata = msg.get_args()
    status = users.cursor.execute("SELECT status from users where id = ?", (message.from_user.id,)).fetchone()
    status = (status[0])
    chat_status = chats.cursor.execute("SELECT chat_status from chats where chat_id = ?", (msg.chat.id,)).fetchone()
    chat_status = (chat_status[0])
    emoji = random.choice(["😐", "🤨", "😔", "😟"])
    if str(status) == 'Создатель бота':
        if str(stata) == 'Официальный' or str(stata) == 'Администраторский' or str(stata) == 'VIP чат' or str(stata) == 'Обычный':
            chats.cursor.execute('UPDATE chats SET chat_status = ? WHERE chat_id = ?', (stata, msg.chat.id))
            chats.connect.commit()
            await msg.answer(f'✅ | Успешно!\nЭтот чат получил статус: {stata}')
        else:
            await msg.reply(f'{emoji} | Таких статусов нет!\nВведите "статусы", чтобы увидеть список доступных статусов')
    elif str(status) == 'Администратор':
        if str(stata) == 'Официальный' or str(stata) == 'VIP чат' or str(stata) == 'Обычный':
            if str(chat_status) != 'Администраторский':
                chats.cursor.execute('UPDATE chats SET chat_status = ? WHERE chat_id = ?', (stata, msg.chat.id))
                chats.connect.commit()
                await msg.answer(f'✅ | Успешно!\nЭтот чат получил статус: {stata}')
            else:
                await msg.reply(f'{emoji} | У вас недостаточный ранг, чтобы менять статус этого чата!')
        else:
            await msg.reply(f'{emoji} | Таких статусов нет или у вас недостаточный ранг для изменения статуса этого чата!')
    else:
        await msg.reply(f'{emoji} | Вы не являетесь администратором бота!')

#Рандом
@dp.message_handler(regexp=r"(^Выбери|выбери) (^От|от) ?(\d+)? (^До|до) ?(\d+)?")
async def random_vybor(message: types.Message):

    name1 = message.from_user.get_mention(as_html=True)
    command_parse = re.compile(r"(^Выбери|выбери) (^От|от) ?(\d+)? (^До|до) ?(\d+)?")

    parsed = command_parse.match(message.text)
    random1 = parsed.group(3)
    random2 = parsed.group(5)
    rand1 = int(random1)
    rand2 = int(random2)
    
    rand = int(randint(rand1, rand2))
    try:
        await message.answer(f"🎱 | {name1}, я выбираю - <b>{rand}</b>")
    except:
        await message.reply(f'❎ | Введите числа!\nПример:<code>Выбери от 1 до 100</code>')
        return

#Слоты
@dp.message_handler(regexp=r"(^Слоты|слоты) ?(\d+)?")
async def slots(message: types.Message):
    msg = message
    name1 = message.from_user.get_mention(as_html=True)
    command_parse = re.compile(r"(^Слоты|слоты) ?(\d+)?")
    parsed = command_parse.match(message.text)
    summ = parsed.group(2)
    summ = int(summ)
    balance = users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone()
    balance = (balance[0])
    stavka = users.cursor.execute("SELECT stavka from users where id = ?", (message.from_user.id,)).fetchone()
    stavka = (stavka[0])
    sm = ["🍬", "💎", "☃️", "🍭", "🔮️"]
    one = random.choice(sm)
    two = random.choice(sm)
    three = random.choice(sm)
    ss = await message.answer(f'Ставка: <code>{summ}💰</code>\n\n        |🌫️|🌫️|🌫️|', parse_mode='html')
    if message.chat.type == 'private':
        if int(summ) <= int(stavka):
            if int(balance) >= summ:
                await asyncio.sleep(2)
                await ss.edit_text(f'Ставка: <code>{summ}💰</code>\n\n        |{one}|🌫️|🌫️|')
                await asyncio.sleep(2)
                await ss.edit_text(f'Ставка: <code>{summ}💰</code>\n\n        |{one}|{two}|🌫️|')
                await asyncio.sleep(2)
                await ss.edit_text(f'Ставка: <code>{summ}💰</code>\n\n        |{one}|{two}|{three}|')
                await asyncio.sleep(1)
                if((one == "🍬") and (two == "🍬") and (three == "🍬")):
                    summ2 = summ * 3
                    data = {}
                    data["suma"] = int(summ2)
                    data['user_id'] = message.from_user.id
                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                    await ss.edit_text( f'{name1}, вам выпало три подряд!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                elif((one == "🍬") and (two == "🍬") and (three != "🍬")):
                    summ2 = summ * 2
                    data = {}
                    data["suma"] = int(summ2)
                    data['user_id'] = message.from_user.id
                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                    await ss.edit_text(f'{name1}, вам выпала пара!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                elif((one != "🍬") and (two == "🍬") and (three == "🍬")):
                    summ2 = summ * 2
                    data = {}
                    data["suma"] = int(summ2)
                    data['user_id'] = message.from_user.id
                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                    await ss.edit_text(f'{name1}, вам выпала пара!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>')      
                elif((one == "💎") and (two == "💎") and (three == "💎")):
                    summ2 = summ * 7
                    data = {}
                    data["suma"] = int(summ2)
                    data['user_id'] = message.from_user.id
                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                    await ss.edit_text(f'{name1}, вам выпало три подряд!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                elif((one == "💎") and (two == "💎") and (three != "💎")):
                    summ2 = summ * 2
                    data = {}
                    data["suma"] = int(summ2)
                    data['user_id'] = message.from_user.id
                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                    await ss.edit_text(f'{name1}, вам выпала пара!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                elif((one != "💎") and (two == "💎") and (three == "💎")):
                    summ2 = summ * 2
                    data = {}
                    data["suma"] = int(summ2)
                    data['user_id'] = message.from_user.id
                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                    await ss.edit_text(f'{name1}, вам выпала пара!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                elif((one == "☃️") and (two == "☃️") and (three == "☃️")):
                    summ2 = summ * 3
                    data = {}
                    data["suma"] = int(summ2)
                    data['user_id'] = message.from_user.id
                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                    await ss.edit_text(f'{name1}, вам выпало три подряд!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                elif((one == "☃️") and (two == "☃️") and (three != "☃️")):
                    summ2 = summ * 2
                    data = {}
                    data["suma"] = int(summ2)
                    data['user_id'] = message.from_user.id
                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                    await ss.edit_text(f'{name1}, вам выпала пара!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                elif((one != "☃️") and (two == "☃️") and (three == "☃️")):
                    summ2 = summ * 2
                    data = {}
                    data["suma"] = int(summ2)
                    data['user_id'] = message.from_user.id
                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                    await ss.edit_text(f'{name1}, вам выпала пара!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                elif((one == "🍭") and (two == "🍭") and (three == "🍭")):
                    summ2 = summ * 2
                    data = {}
                    data["suma"] = int(summ2)
                    data['user_id'] = message.from_user.id
                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                    await ss.edit_text(f'{name1}, вам выпало три подряд!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                elif((one == "🍭") and (two == "🍭") and (three != "🍭")):
                    summ2 = summ * 1
                    data = {}
                    data["suma"] = int(summ2)
                    data['user_id'] = message.from_user.id
                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                    await ss.edit_text(f'{name1}, вам выпала пара!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                elif((one != "🍭") and (two == "🍭") and (three == "🍭")):
                    summ2 = summ * 1
                    data = {}
                    data["suma"] = int(summ2)
                    data['user_id'] = message.from_user.id
                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                    await ss.edit_text(f'{name1}, вам выпала пара!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                elif((one == "🔮️") and (two == "🔮️") and (three == "🔮️")):
                    summ2 = summ * 2
                    data = {}
                    data["suma"] = int(summ2)
                    data['user_id'] = message.from_user.id
                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                    await ss.edit_text(f'{name1}, вам выпало три подряд!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                elif((one == "🔮️") and (two == "🔮️") and (three != "🔮️")):
                    summ2 = summ * 1
                    data = {}
                    data["suma"] = int(summ2)
                    data['user_id'] = message.from_user.id
                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                    await ss.edit_text(f'{name1}, вам выпала пара!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                elif((one != "🔮️") and (two == "🔮️") and (three == "🔮️")):
                    summ2 = summ * 1
                    data = {}
                    data["suma"] = int(summ2)
                    data['user_id'] = message.from_user.id
                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                    await ss.edit_text(f'{name1}, вам выпала пара!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                else:
                    summ2 = summ * 1
                    data = {}
                    data["suma"] = int(summ2)
                    data['user_id'] = message.from_user.id
                    users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", data)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                    await ss.edit_text(f'{name1}, совпадений нет!\n\n        |{one}|{two}|{three}|\n\nВы проиграли: <code>{summ2}💰</code>', parse_mode='html')
            elif int(balance) < summ:
                await ss.edit_text(f'❎ | У вас нет столько монет!\n💳 | Ваш баланс: {balance}💰', parse_mode='html')
        else:
            await ss.edit_text(f'❎ | Ваша максимальная ставка: {stavka}💰', parse_mode='html')
    else:
        game_rule = chats.cursor.execute("SELECT game_rule from chats where chat_id = ?", (msg.chat.id,)).fetchone()
        game_rule = (game_rule[0])
        if str(game_rule) == 'разрешено':
            if int(summ) <= int(stavka):
                if int(balance) >= summ:
                    await asyncio.sleep(2)
                    await ss.edit_text(f'Ставка: {summ}💰\n\n        |{one}|🌫️|🌫️|')
                    await asyncio.sleep(2)
                    await ss.edit_text(f'Ставка: {summ}💰\n\n        |{one}|{two}|🌫️|')
                    await asyncio.sleep(2)
                    await ss.edit_text(f'Ставка: {summ}💰\n\n        |{one}|{two}|{three}|')
                    await asyncio.sleep(1)
                    if((one == "🍬") and (two == "🍬") and (three == "🍬")):
                        summ2 = summ * 3
                        data = {}
                        data["suma"] = int(summ2)
                        data['user_id'] = message.from_user.id
                        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                        await ss.edit_text( f'{name1}, вам выпало три подряд!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                    elif((one == "🍬") and (two == "🍬") and (three != "🍬")):
                        summ2 = summ * 2
                        data = {}
                        data["suma"] = int(summ2)
                        data['user_id'] = message.from_user.id
                        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                        await ss.edit_text(f'{name1}, вам выпала пара!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                    elif((one != "🍬") and (two == "🍬") and (three == "🍬")):
                        summ2 = summ * 2
                        data = {}
                        data["suma"] = int(summ2)
                        data['user_id'] = message.from_user.id
                        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                        await ss.edit_text(f'{name1}, вам выпала пара!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>')      
                    elif((one == "💎") and (two == "💎") and (three == "💎")):
                        summ2 = summ * 7
                        data = {}
                        data["suma"] = int(summ2)
                        data['user_id'] = message.from_user.id
                        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                        await ss.edit_text(f'{name1}, вам выпало три подряд!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                    elif((one == "💎") and (two == "💎") and (three != "💎")):
                        summ2 = summ * 2
                        data = {}
                        data["suma"] = int(summ2)
                        data['user_id'] = message.from_user.id
                        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                        await ss.edit_text(f'{name1}, вам выпала пара!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                    elif((one != "💎") and (two == "💎") and (three == "💎")):
                        summ2 = summ * 2
                        data = {}
                        data["suma"] = int(summ2)
                        data['user_id'] = message.from_user.id
                        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                        await ss.edit_text(f'{name1}, вам выпала пара!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                    elif((one == "☃️") and (two == "☃️") and (three == "☃️")):
                        summ2 = summ * 3
                        data = {}
                        data["suma"] = int(summ2)
                        data['user_id'] = message.from_user.id
                        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                        await ss.edit_text(f'{name1}, вам выпало три подряд!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                    elif((one == "☃️") and (two == "☃️") and (three != "☃️")):
                        summ2 = summ * 2
                        data = {}
                        data["suma"] = int(summ2)
                        data['user_id'] = message.from_user.id
                        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                        await ss.edit_text(f'{name1}, вам выпала пара!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                    elif((one != "☃️") and (two == "☃️") and (three == "☃️")):
                        summ2 = summ * 2
                        data = {}
                        data["suma"] = int(summ2)
                        data['user_id'] = message.from_user.id
                        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                        await ss.edit_text(f'{name1}, вам выпала пара!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                    elif((one == "🍭") and (two == "🍭") and (three == "🍭")):
                        summ2 = summ * 2
                        data = {}
                        data["suma"] = int(summ2)
                        data['user_id'] = message.from_user.id
                        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                        await ss.edit_text(f'{name1}, вам выпало три подряд!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                    elif((one == "🍭") and (two == "🍭") and (three != "🍭")):
                        summ2 = summ * 1
                        data = {}
                        data["suma"] = int(summ2)
                        data['user_id'] = message.from_user.id
                        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                        await ss.edit_text(f'{name1}, вам выпала пара!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                    elif((one != "🍭") and (two == "🍭") and (three == "🍭")):
                        summ2 = summ * 1
                        data = {}
                        data["suma"] = int(summ2)
                        data['user_id'] = message.from_user.id
                        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                        await ss.edit_text(f'{name1}, вам выпала пара!\n\n        {one}|{two}|{three}\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                    elif((one == "🔮️") and (two == "🔮️") and (three == "🔮️")):
                        summ2 = summ * 2
                        data = {}
                        data["suma"] = int(summ2)
                        data['user_id'] = message.from_user.id
                        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                        await ss.edit_text(f'{name1}, вам выпало три подряд!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                    elif((one == "🔮️") and (two == "🔮️") and (three != "🔮️")):
                        summ2 = summ * 1
                        data = {}
                        data["suma"] = int(summ2)
                        data['user_id'] = message.from_user.id
                        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                        await ss.edit_text(f'{name1}, вам выпала пара!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                    elif((one != "🔮️") and (two == "🔮️") and (three == "🔮️")):
                        summ2 = summ * 1
                        data = {}
                        data["suma"] = int(summ2)
                        data['user_id'] = message.from_user.id
                        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                        await ss.edit_text(f'{name1}, вам выпала пара!\n\n        |{one}|{two}|{three}|\n\nВы выиграли: <code>{summ2}💰</code>', parse_mode='html')
                    else:
                        summ2 = summ * 1
                        data = {}
                        data["suma"] = int(summ2)
                        data['user_id'] = message.from_user.id
                        users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", data)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET slots = slots + 1 WHERE id=?', (message.from_user.id,))
                        await ss.edit_text(f'{name1}, совпадений нет!\n\n        |{one}|{two}|{three}|\n\nВы проиграли: <code>{summ2}💰</code>', parse_mode='html')
                elif int(balance) < summ:
                    await ss.edit_text(f'❎ | У вас нет столько монет!\n💳 | Ваш баланс: {balance}💰', parse_mode='html')
            else:
                await ss.edit_text(f'❎ | Ваша максимальная ставка: {stavka}💰', parse_mode='html')
        else:
            await ss.edit_text(f'🚫 | В этом чате запрещено играть!')


# @Penggrin
def get_casino_values(dice_value):
    casino = ["BAR", "Виноград", "Лимон", "Семь"]
    return [casino[(dice_value - 1) // i % 4] for i in (1, 4, 16)]


# @Penggrin
def get_casino_result(dice, bet, bonus_users):
    data = get_casino_values(dice)

    if not (data[0] == data[1] == data[2]):
        return (False, bet, data)
    
    if data[0] == "Семь":
        return (True, bet * (10 + (0.35 * bonus_users)), data)

    return (True, bet * (5 + (0.35 * bonus_users)), data)
    


#Казино (@Penggrin)
@rate_limit(limit=1.5)
@dp.message_handler(regexp=r"(^Казино|казино) ?(\d+)?")
async def kazino(message: types.Message):
    stavka = int((users.cursor.execute("SELECT stavka from users where id = ?", (message.from_user.id,)).fetchone())[0])
    balance = int((users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone())[0])
    invited_users = int((users.cursor.execute("SELECT invited_users from users where id = ?", (message.from_user.id,)).fetchone())[0])

    name = message.from_user.get_mention(as_html=True)
    args = message.text.lower().split()

    if len(args) < 2:
        await message.reply("❎ | Вы не указали ставку!")
        return

    if int(args[1]) < 1:
        await message.reply("❎ | Ставка не может быть меньше нуля!")
        return

    bet = int(args[1])

    if message.chat.type != 'private':
        game_rule = chats.cursor.execute("SELECT game_rule from chats where chat_id = ?", (message.chat.id,)).fetchone()
        game_rule = (game_rule[0])
        if game_rule != "разрешено":
            await message.reply(f'🚫 | В этом чате запрещено играть!')
            return

    if bet > stavka:
        await message.reply(f'❎ | Максимальная ставка: {stavka}💰')
        return
    if balance < bet:
        await message.reply(f'❎ | У вас нет столько монет!\n💳 | Ваш баланс: {balance}💰')
        return

    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
    users.cursor.execute(f'UPDATE users SET casino = casino + 1 WHERE id=?', (message.from_user.id,))
    if message.chat.type != 'private':
        chats.cursor.execute(f'UPDATE chats SET chat_games = chat_games + 1 WHERE chat_id=?', (message.chat.id,))

    dice = (await bot.send_dice(message.chat.id, emoji="🎰")).dice.value
    result = get_casino_result(dice, bet, invited_users)
    await sleep(2)
    if result[0]: # 7-7-7, bar-bar-bar, etc
        users.cursor.execute(
            """UPDATE users SET balance = :sum WHERE id = :user_id;""",
            {"user_id": message.from_user.id, "sum": balance + result[1]}
        )

        await message.reply(
            f'🎰 | Вам выпала комбинация: {result[2][0]}, {result[2][1]}, {result[2][2]} (№{dice})\n'
            f'💸 | Вы выиграли: <b>{result[1]}💰</b>\n'
            f'💳 | Ваш баланс: <b>{balance + result[1]}💰</b>',
            parse_mode='html'
        )
    else: # 7-bar-bar, bar-7-7, etc
        users.cursor.execute(
            """UPDATE users SET balance = :sum WHERE id = :user_id;""",
            {"user_id": message.from_user.id, "sum": balance - result[1]}
        )

        await message.reply(
            f'🎰 | Вам выпала комбинация: {result[2][0]}, {result[2][1]}, {result[2][2]} (№{dice})\n'
            f'💸 | Вы проиграли: <b>{result[1]}💰</b>\n'
            f'💳 | Ваш баланс: <b>{balance - result[1]}💰</b>',
            parse_mode='html'
        )

    users.connect.commit()
    if message.chat.type != 'private':
        chats.connect.commit()


#Куб
@dp.message_handler(regexp=r"(^Куб|куб) ?(\d+)? ?(\d+)?")
async def kub(message: types.Message):
    msg = message
    command_parse = re.compile(r"(^Куб|куб) ?(\d+)? ?(\d+)?")
    parsed = command_parse.match(message.text)
    stavka = users.cursor.execute("SELECT stavka from users where id = ?", (message.from_user.id,)).fetchone()
    stavka = (stavka[0])
    dice_value = parsed.group(2)
    dice_value = int(dice_value)
    summ = parsed.group(3)
    summ = int(summ)
    name1 = message.from_user.get_mention(as_html=True)
    if message.chat.type == 'private':
        if summ <= int(stavka):
            if dice_value > 6:
                await message.reply(f"❎ | Введите сообщение в формате: \n<b>Куб (число от 1 до 6) (ставка)</b>", parse_mode='html')
            else:
                if not summ:
                    await message.reply(f"❎ | Введите сообщение в формате: \n<b>Куб (число от 1 до 6) (ставка)</b>", parse_mode='html')
                else:
                    if not dice_value:
                        await message.reply(f"❎ | Введите сообщение в формате:\n<b>Куб (число от 1 до 6) (ставка)</b>", parse_mode='html')
                    else:
                        balance = (users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone())[0]
                        invited_users = (users.cursor.execute("SELECT invited_users from users where id = ?", (message.from_user.id,)).fetchone())[0]
                        if balance >= summ:
                            dice_value = int(dice_value)
                            bot_data = await bot.send_dice (message.chat.id)
                            bot_data = bot_data['dice']['value']
                            plus = bot_data + 1
                            minus = bot_data - 1
                            summ2 = summ * 10
                            data = {}
                            data["suma"] = summ
                            data['user_id'] = message.from_user.id
                            data1 = {}
                            data1["suma"] = summ2
                            data1['user_id'] = message.from_user.id
                            await sleep(5)

                            if bot_data > dice_value:
                                await message.reply(f'🎲❌ | Вы проиграли: <b>{summ}💰</b>', parse_mode='html')
                                users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", data)
                                users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                                users.cursor.execute(f'UPDATE users SET kosti = kosti + 1 WHERE id=?', (message.from_user.id,))
                            elif bot_data < dice_value:
                                await message.reply(f'🎲❌ | Вы проиграли: <b>{summ}💰</b>', parse_mode='html')
                                users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", data)
                                users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                                users.cursor.execute(f'UPDATE users SET kosti = kosti + 1 WHERE id=?', (message.from_user.id,))
                            else:
                                await message.reply(f'🎲✅ | Вы выиграли: <b>{summ * (2 + (0.35 * invited_users))}💰</b>', parse_mode='html')
                                users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""",
                                    {"suma": summ * (5 + (0.35 * invited_users)), "user_id": message.from_user.id}
                                )
                                users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                                users.cursor.execute(f'UPDATE users SET kosti = kosti + 1 WHERE id=?', (message.from_user.id,))
                                users.connect.commit()
                        elif balance < summ:
                            balanc = users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone()
                            balance = (balanc[0])
                            await message.reply(f'❎ | У вас нет столько монет!\n💳 | Ваш баланс: {balance}💰', parse_mode='html')
        else:
            await message.reply(f'❎ | Ваша максимальная ставка: {stavka}💰', parse_mode='html')
    else:
        game_rule = chats.cursor.execute("SELECT game_rule from chats where chat_id = ?", (msg.chat.id,)).fetchone()
        game_rule = (game_rule[0])
        if str(game_rule) == 'разрешено':
            if summ <= int(stavka):
                if dice_value > 6:
                    await message.reply(f"❎ | Введите сообщение в формате: \n<b>Куб (число от 1 до 6) (ставка)</b>", parse_mode='html')
                else:
                    if not summ:
                        await message.reply(f"❎ | Введите сообщение в формате: \n<b>Куб (число от 1 до 6) (ставка)</b>", parse_mode='html')
                    else:
                        if not dice_value:
                            await message.reply(f"❎ | Введите сообщение в формате:\n<b>Куб (число от 1 до 6) (ставка)</b>", parse_mode='html')
                        else:
                            balanc = (users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone())[0]
                            invited_users = (users.cursor.execute("SELECT invited_users from users where id = ?", (message.from_user.id,)).fetchone())[0]
                            if balance >= summ:
                                dice_value = int(dice_value)
                                bot_data = await bot.send_dice (message.chat.id)
                                bot_data = bot_data['dice']['value']
                                plus = bot_data + 1
                                minus = bot_data - 1
                                summ2 = summ * 10
                                data = {}
                                data["suma"] = summ
                                data['user_id'] = message.from_user.id
                                data1 = {}
                                data1["suma"] = summ2
                                data1['user_id'] = message.from_user.id
                                await sleep(5)

                                if bot_data > dice_value:
                                    await message.reply(f'🎲❌ | Вы проиграли: <b>{summ}💰</b>', parse_mode='html')
                                    users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", data)
                                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                                    users.cursor.execute(f'UPDATE users SET kosti = kosti + 1 WHERE id=?', (message.from_user.id,))
                                    chats.cursor.execute(f'UPDATE chats SET chat_games = chat_games + 1 WHERE chat_id=?', (message.chat.id,))
                                    users.connect.commit()
                                    chats.connect.commit()
                                elif bot_data < dice_value:
                                    await message.reply(f'🎲❌ | Вы проиграли: <b>{summ}💰</b>', parse_mode='html')
                                    users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", data)
                                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                                    users.cursor.execute(f'UPDATE users SET kosti = kosti + 1 WHERE id=?', (message.from_user.id,))
                                    chats.cursor.execute(f'UPDATE chats SET chat_games = chat_games + 1 WHERE chat_id=?', (message.chat.id,))
                                    users.connect.commit()
                                    chats.connect.commit()
                                else:
                                    await message.reply(f'🎲✅ | Вы выиграли: <b>{summ * (2 + (0.35 * invited_users))}💰</b>', parse_mode='html')
                                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""",
                                        {"suma": summ * (5 + (0.35 * invited_users)), "user_id": message.from_user.id}
                                    )
                                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                                    users.cursor.execute(f'UPDATE users SET kosti = kosti + 1 WHERE id=?', (message.from_user.id,))
                                    chats.cursor.execute(f'UPDATE chats SET chat_games = chat_games + 1 WHERE chat_id=?', (message.chat.id,))
                                    users.connect.commit()
                                    chats.connect.commit()
                            elif balance < summ:
                                balanc = users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone()
                                balance = (balanc[0])
                                await message.reply(f'❎ | У вас нет столько монет!\n💳 | Ваш баланс: {balance}💰', parse_mode='html')
            else:
                await message.reply(f'❎ | Ваша максимальная ставка: {stavka}💰', parse_mode='html')
        else:
            await message.reply(f'🚫 | В этом чате запрещено играть!')

#Дартс
@dp.message_handler(regexp=r"(^Дартс|дартс) ?(\d+)?")
async def darts(message: types.Message):
    msg = message
    command_parse = re.compile(r"(^Дартс|дартс) ?(\d+)?")
    parsed = command_parse.match(message.text)
    summ = parsed.group(2)
    name1 = message.from_user.get_mention(as_html=True)
    summ = int(summ)
    suma = int(summ) * 2
    name1 = message.from_user.get_mention(as_html=True)
    data = {}
    data["suma"] = suma
    data['user_id'] = message.from_user.id
    data1 = {}
    data1["suma"] = summ
    data1['user_id'] = message.from_user.id
    balance = (users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone())[0]
    stavka = (users.cursor.execute("SELECT stavka from users where id = ?", (message.from_user.id,)).fetchone())[0]
    invited_users = (users.cursor.execute("SELECT invited_users from users where id = ?", (message.from_user.id,)).fetchone())[0]

    if message.chat.type == 'private':
        if balance >= summ:
            if summ <= int(stavka):
                bot_data = await bot.send_dice(message.chat.id, emoji='🎯')
                bot_data = bot_data['dice']['value']
                await sleep(3)
                if bot_data == 6:
                    await message.reply(f'🎯✅ | Вы попали прямо в цель и выиграли: <b>{summ * (2 + (0.35 * invited_users))}</b>💰', parse_mode='html')
                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""",
                        {"suma": summ * (2 + (0.35 * invited_users)), "user_id": message.from_user.id}
                    )
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET darts = darts + 1 WHERE id=?', (message.from_user.id,))
                    users.connect.commit()
                elif bot_data == 1:
                    await message.reply(f'🎯❌ | Такой себе бросок, деньги остаются при вас')
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET darts = darts + 1 WHERE id=?', (message.from_user.id,))
                    users.connect.commit()
                else:
                    await message.reply(f'🎯❌ | Вы промазали и проиграли: <b>{summ}</b>💰', parse_mode='html')
                    users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", data1)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET darts = darts + 1 WHERE id=?', (message.from_user.id,))
                    users.connect.commit()
            else:
                await message.reply(f'❎ | Ваша максимальная ставка: {stavka}💰', parse_mode='html')
        else:
            await message.reply(f'❎ | У вас нет столько монет!\n💳 | Ваш баланс: {balance}💰', parse_mode='html')
    else:
        game_rule = chats.cursor.execute("SELECT game_rule from chats where chat_id = ?", (msg.chat.id,)).fetchone()
        game_rule = (game_rule[0])
        if str(game_rule) == 'разрешено':
            if balance >= summ:
                if summ <= (stavka):
                    bot_data = await bot.send_dice(message.chat.id, emoji='🎯')
                    bot_data = bot_data['dice']['value']
                    await sleep(3)
                    if bot_data == 6:
                        await message.reply(f'🎯✅ | Вы попали прямо в цель и выиграли: <b>{summ * (2 + (0.35 * invited_users))}</b>💰', parse_mode='html')
                        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""",
                            {"suma": summ * (2 + (0.35 * invited_users)), "user_id": message.from_user.id}
                        )
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET darts = darts + 1 WHERE id=?', (message.from_user.id,))
                        chats.cursor.execute(f'UPDATE chats SET chat_games = chat_games + 1 WHERE chat_id=?', (message.chat.id,))
                        chats.connect.commit()
                        users.connect.commit()
                    elif bot_data == 1:
                        await message.reply(f'🎯❌ | Такой себе бросок, деньги остаются при вас')
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET darts = darts + 1 WHERE id=?', (message.from_user.id,))
                        chats.cursor.execute(f'UPDATE chats SET chat_games = chat_games + 1 WHERE chat_id=?', (message.chat.id,))
                        chats.connect.commit()
                        users.connect.commit()
                    else:
                        await message.reply(f'🎯❌ | Вы промазали и проиграли: <b>{summ}</b>💰', parse_mode='html')
                        users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", data1)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET darts = darts + 1 WHERE id=?', (message.from_user.id,))
                        chats.cursor.execute(f'UPDATE chats SET chat_games = chat_games + 1 WHERE chat_id=?', (message.chat.id,))
                        chats.connect.commit()
                        users.connect.commit()
                else:
                    await message.reply(f'❎ | Ваша максимальная ставка: {stavka}💰', parse_mode='html')
            else:
                await message.reply(f'❎ | У вас нет столько монет!\n💳 | Ваш баланс: {balance}💰', parse_mode='html')
        else:
            await message.reply(f'🚫 | В этом чате запрещено играть!')

#Боул
@dp.message_handler(regexp=r"(^Боул|боул) ?(\d+)?")
async def boul(message: types.Message):
    msg = message
    command_parse = re.compile(r"(^Боул|боул) ?(\d+)?")
    parsed = command_parse.match(message.text)
    summ = parsed.group(2)
    summ = int(summ)
    suma = int(summ) * 2
    name1 = message.from_user.get_mention(as_html=True)
    data = {}
    data["suma"] = suma
    data['user_id'] = message.from_user.id
    data1 = {}
    data1["suma"] = summ
    data1['user_id'] = message.from_user.id
    balanc = users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone()
    balance = (balanc[0])
    stavka = users.cursor.execute("SELECT stavka from users where id = ?", (message.from_user.id,)).fetchone()
    stavka = (stavka[0])
    invited_users = users.cursor.execute("SELECT invited_users from users where id = ?", (message.from_user.id,)).fetchone()
    invited_users = (invited_users[0])
    if message.chat.type == 'private':
        if balance >= summ:
            if summ <= int(stavka):
                bot_data = await bot.send_dice(message.chat.id, emoji='🎳')
                bot_data = bot_data['dice']['value']
                await sleep(3)
                if bot_data == 6:
                    await message.reply(f'🎳💥 | Вы сбили все кегли и выиграли: <b>{summ * (2 + (0.35 * invited_users))}</b>💰', parse_mode='html')
                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""",
                        {"suma": summ * (2 + (0.35 * invited_users)), "user_id": message.from_user.id}
                    )
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET bouling = bouling + 1 WHERE id=?', (message.from_user.id,))
                    users.connect.commit()
                elif bot_data == 1:
                    await message.reply(f'🎳❌ | Такой себе бросок, деньги остаются при вас')
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET bouling = bouling + 1 WHERE id=?', (message.from_user.id,))
                    users.connect.commit()
                else:
                    await message.reply(f'🎳❌ | Вы промазали и проиграли: <b>{summ}</b>💰', parse_mode='html')
                    users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", data1)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET bouling = bouling + 1 WHERE id=?', (message.from_user.id,))
                    users.connect.commit()
            else:
                await message.reply(f'❎ | Ваша максимальная ставка: {stavka}💰', parse_mode='html')
        elif balance < summ:
            balanc = users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone()
            balance = (balanc[0])
            await message.reply(f'❎ | У вас нет столько монет!\n💳 | Ваш баланс: {balance}💰', parse_mode='html')
    else:
        game_rule = chats.cursor.execute("SELECT game_rule from chats where chat_id = ?", (msg.chat.id,)).fetchone()
        game_rule = (game_rule[0])
        if str(game_rule) == 'разрешено':
            if balance >= summ:
                if summ <= int(stavka):
                    bot_data = await bot.send_dice(message.chat.id, emoji='🎳')
                    bot_data = bot_data['dice']['value']
                    await sleep(3)
                    if bot_data == 6:
                        await message.reply(f'🎳💥 | Вы сбили все кегли и выиграли: <b>{summ * (2 + (0.35 * invited_users))}</b>💰', parse_mode='html')
                        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""",
                            {"suma": summ * (2 + (0.35 * invited_users)), "user_id": message.from_user.id}
                        )
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET bouling = bouling + 1 WHERE id=?', (message.from_user.id,))
                        chats.cursor.execute(f'UPDATE chats SET chat_games = chat_games + 1 WHERE chat_id=?', (message.chat.id,))
                        chats.connect.commit()
                        users.connect.commit()
                    elif bot_data == 1:
                        await message.reply(f'🎳❌ | Такой себе бросок, деньги остаются при вас')
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET bouling = bouling + 1 WHERE id=?', (message.from_user.id,))
                        chats.cursor.execute(f'UPDATE chats SET chat_games = chat_games + 1 WHERE chat_id=?', (message.chat.id,))
                        chats.connect.commit()
                        users.connect.commit()
                    else:
                        await message.reply(f'🎳❌ | Вы промазали и проиграли: <b>{summ}</b>💰', parse_mode='html')
                        users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", data1)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET bouling = bouling + 1 WHERE id=?', (message.from_user.id,))
                        chats.cursor.execute(f'UPDATE chats SET chat_games = chat_games + 1 WHERE chat_id=?', (message.chat.id,))
                        chats.connect.commit()
                        users.connect.commit()
                else:
                    await message.reply(f'❎ | Ваша максимальная ставка: {stavka}💰', parse_mode='html')
            elif balance < summ:
                            balanc = users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone()
                            balance = (balanc[0])
                            await message.reply(f'❎ | У вас нет столько монет!\n💳 | Ваш баланс: {balance}💰', parse_mode='html')
        else:
            await message.reply(f'🚫 | В этом чате запрещено играть!')

#Фут
@dp.message_handler(regexp=r"(^Фут|фут) ?(\d+)?")
async def football(message: types.Message):
    msg = message
    command_parse = re.compile(r"(^Фут|фут) ?(\d+)?")
    parsed = command_parse.match(message.text)
    summ = parsed.group(2)
    name1 = message.from_user.get_mention(as_html=True)
    data = {}
    summ = int(summ)
    data["suma"] = summ
    data['user_id'] = message.from_user.id
    balanc = users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone()
    balance = (balanc[0])
    stavka = users.cursor.execute("SELECT stavka from users where id = ?", (message.from_user.id,)).fetchone()
    stavka = (stavka[0])
    invited_users = int((users.cursor.execute("SELECT invited_users from users where id = ?", (message.from_user.id,)).fetchone())[0])
    if message.chat.type == 'private':
        if balance >= summ:
            if summ <= int(stavka):
                bot_data = await bot.send_dice(message.chat.id, emoji='⚽')
                bot_data = bot_data['dice']['value']
                await sleep(4)
                if bot_data >= 3:
                    await message.reply(f'⚽✅ | Вы попали прямо в ворота и выиграли: <b>{summ * (1 + (0.35 * invited_users))}</b>💰', parse_mode='html')
                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""",
                        {"suma": summ * (1 + (0.35 * invited_users)), "user_id": message.from_user.id}
                    )
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET footbal = footbal + 1 WHERE id=?', (message.from_user.id,))
                    users.connect.commit()
                else:
                    await message.reply(f'⚽❌ | Вы промазали и проиграли: <b>{summ}</b>💰', parse_mode='html')
                    users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", data)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET footbal = footbal + 1 WHERE id=?', (message.from_user.id,))
                    users.connect.commit()
            else:
                await message.reply(f'❎ | Ваша максимальная ставка: {stavka}💰', parse_mode='html')
        elif balance < summ:
            balanc = users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone()
            balance = (balanc[0])
            await message.reply(f'❎ | У вас нет столько монет!\n💳 | Ваш баланс: {balance}💰', parse_mode='html')
    else:
        game_rule = chats.cursor.execute("SELECT game_rule from chats where chat_id = ?", (msg.chat.id,)).fetchone()
        game_rule = (game_rule[0])
        if str(game_rule) == 'разрешено':
            if balance >= summ:
                if summ <= int(stavka):
                    bot_data = await bot.send_dice(message.chat.id, emoji='⚽')
                    bot_data = bot_data['dice']['value']
                    await sleep(4)
                    if bot_data >= 3:
                        await message.reply(f'⚽✅ | Вы попали прямо в ворота и выиграли: <b>{summ * (1 + (0.35 * invited_users))}</b>💰', parse_mode='html')
                        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""",
                            {"suma": summ * (1 + (0.35 * invited_users)), "user_id": message.from_user.id}
                        )
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET footbal = footbal + 1 WHERE id=?', (message.from_user.id,))
                        chats.cursor.execute(f'UPDATE chats SET chat_games = chat_games + 1 WHERE chat_id=?', (message.chat.id,))
                        users.connect.commit()
                        chats.connect.commit()
                    else:
                        await message.reply(f'⚽❌ | Вы промазали и проиграли: <b>{summ}</b>💰', parse_mode='html')
                        users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", data)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET footbal = footbal + 1 WHERE id=?', (message.from_user.id,))
                        chats.cursor.execute(f'UPDATE chats SET chat_games = chat_games + 1 WHERE chat_id=?', (message.chat.id,))
                        users.connect.commit()
                        chats.connect.commit()
                else:
                    await message.reply(f'❎ | Ваша максимальная ставка: {stavka}💰', parse_mode='html')
            elif balance < summ:
                            balanc = users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone()
                            balance = (balanc[0])
                            await message.reply(f'❎ | У вас нет столько монет!\n💳 | Ваш баланс: {balance}💰', parse_mode='html')
        else:
            await message.reply(f'🚫 | В этом чате запрещено играть!')

#Баскет
@dp.message_handler(regexp=r"(^Бас|бас|Баскет|баскет) ?(\d+)?")
async def basket(message: types.Message):
    msg = message
    command_parse = re.compile(r"(^Бас|бас|Баскет|баскет) ?(\d+)?")
    parsed = command_parse.match(message.text)
    summ = parsed.group(2)
    name1 = message.from_user.get_mention(as_html=True)
    data = {}
    data["suma"] = summ
    data['user_id'] = message.from_user.id
    balanc = users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone()
    balance = (balanc[0])
    stavka = users.cursor.execute("SELECT stavka from users where id = ?", (message.from_user.id,)).fetchone()
    stavka = (stavka[0])
    invited_users = int((users.cursor.execute("SELECT invited_users from users where id = ?", (message.from_user.id,)).fetchone())[0])
    summ = int(summ)
    if message.chat.type == 'private':
        if balance >= summ:
            if summ <= int(stavka):
                bot_data = await bot.send_dice(message.chat.id, emoji='🏀')
                bot_data = bot_data['dice']['value']
                await sleep(4)
                if bot_data >= 4:
                    await message.reply(f'🏀✅ | Вы попали прямо в кольцо и выиграли: <b>{summ * (1 + (0.35 * invited_users))}</b>💰', parse_mode='html')
                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""",
                        {"suma": summ * (1 + (0.35 * invited_users)), "user_id": message.from_user.id}
                    )
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET basket = basket + 1 WHERE id=?', (message.from_user.id,))
                elif bot_data == 3:
                    await message.reply(f'🏀❌ | Упс... мяч застрял в кольце, деньги остаются при вас.', parse_mode='html')
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET basket = basket + 1 WHERE id=?', (message.from_user.id,))
                    users.connect.commit()
                else:
                    await message.reply(f'🏀❌ | Вы промазали и проиграли: <b>{summ}</b>💰', parse_mode='html')
                    users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", data)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET basket = basket + 1 WHERE id=?', (message.from_user.id,))
                    users.connect.commit()
            else:
                await message.reply(f'❎ | Ваша максимальная ставка: {stavka} 💰', parse_mode='html')
        elif balance < summ:
            balanc = users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone()
            balance = (balanc[0])
            await message.reply(f'❎ | У вас нет столько монет!\n💳 | Ваш баланс: {balance}💰', parse_mode='html')
    else:
        game_rule = chats.cursor.execute("SELECT game_rule from chats where chat_id = ?", (msg.chat.id,)).fetchone()
        game_rule = (game_rule[0])
        if str(game_rule) == 'разрешено':
            if balance >= summ:
                if summ <= int(stavka):
                    bot_data = await bot.send_dice(message.chat.id, emoji='🏀')
                    bot_data = bot_data['dice']['value']
                    await sleep(4)
                    if bot_data >= 4:
                        await message.reply(f'🏀✅ | Вы попали прямо в кольцо и выиграли: <b>{summ * (1 + (0.35 * invited_users))}</b>💰', parse_mode='html')
                        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""",
                            {"suma": summ * (1 + (0.35 * invited_users)), "user_id": message.from_user.id}
                        )
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET basket = basket + 1 WHERE id=?', (message.from_user.id,))
                        chats.cursor.execute(f'UPDATE chats SET chat_games = chat_games + 1 WHERE chat_id=?', (message.chat.id,))
                        chats.connect.commit()
                        users.connect.commit()
                    elif bot_data == 3:
                        await message.reply(f'🏀❌ | Упс... мяч застрял в кольце, деньги остаются при вас.', parse_mode='html')
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET basket = basket + 1 WHERE id=?', (message.from_user.id,))
                        chats.cursor.execute(f'UPDATE chats SET chat_games = chat_games + 1 WHERE chat_id=?', (message.chat.id,))
                        chats.connect.commit()
                        users.connect.commit()
                    else:
                        await message.reply(f'🏀❌ | Вы промазали и проиграли: <b>{summ}</b>💰', parse_mode='html')
                        users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", data)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET basket = basket + 1 WHERE id=?', (message.from_user.id,))
                        chats.cursor.execute(f'UPDATE chats SET chat_games = chat_games + 1 WHERE chat_id=?', (message.chat.id,))
                        chats.connect.commit()
                        users.connect.commit()
                else:
                    await message.reply(f'❎ | Ваша максимальная ставка: {stavka}💰', parse_mode='html')
            elif balance < summ:
                balance = users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone()
                balance = (balance[0])
                await message.reply(f'❎ | У вас нет столько монет!\n💳 | Ваш баланс: {balance}💰', parse_mode='html')
        else:
            await message.reply(f'🚫 | В этом чате запрещено играть!')

#Охота
@rate_limit(limit=1.5)
@dp.message_handler(regexp=r"(^Охота|охота) ?(\d+)?")
async def nc(message: types.Message):
    name1 = message.from_user.get_mention(as_html=True)
    args = message.text.lower().split()

    if len(args) < 2:
        await message.reply("❎ | Вы не указали ставку!")
        return

    if int(args[1]) < 1:
        await message.reply("❎ | Ставка не может быть меньше нуля!")
        return

    summ2 = int(args[1])
    summ3 = int(args[1]) * 2
    summ4 = int(args[1]) * 3

    data = {}
    data["suma"] = int(args[1])
    data['user_id'] = message.from_user.id
    data1 = {}
    data1["suma"] = int(summ2)
    data1['user_id'] = message.from_user.id
    data2 = {}
    data2["suma"] = int(summ3)
    data2['user_id'] = message.from_user.id
    data3 = {}
    data3["suma"] = int(summ4)
    data3['user_id'] = message.from_user.id
    datas = {}
    datas["suma"] = int(args[1]) * 3
    datas['user_id'] = message.from_user.id
    datab = {}
    datab["suma"] = int(args[1]) * 1.5
    datab['user_id'] = message.from_user.id

    cnb = ['Заяц', 'Волк', 'Медведь', 'Мимо', 'Дядя Стёпа', 'Больница']
    game = random.choice(cnb)
    balance = users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone()
    balance = (balance[0])
    stavka = users.cursor.execute("SELECT stavka from users where id = ?", (message.from_user.id,)).fetchone()
    stavka = (stavka[0])
    if message.chat.type == 'private':
        if int(args[1]) <= int(stavka):
            if int(balance) >= int(args[1]):
                gg = await message.reply(f'💥 | Выстрел... посмотрим в кого вы попали')
                await sleep(3)
                if game == 'Заяц':
                    await gg.edit_text(f'💥🐰 | Отлично!\nВы попали в зайца, вот ваша награда: <b>{summ2}</b>💰', parse_mode='html')
                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data1)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET ohota = ohota + 1 WHERE id=?', (message.from_user.id,))
                elif game == 'Волк':
                    await gg.edit_text(f'💥🐺 | Отлично!\nВы попали в волка, вот ваша награда: <b>{summ3}</b>💰', parse_mode='html')
                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data2)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET ohota = ohota + 1 WHERE id=?', (message.from_user.id,))
                    users.connect.commit()
                elif game == 'Медведь':
                    await gg.edit_text(f'💥🐻 | Отлично!\nВы попали в медведя, вот ваша награда: <b>{summ4}</b>💰', parse_mode='html')
                    users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data3)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET ohota = ohota + 1 WHERE id=?', (message.from_user.id,))
                    users.connect.commit()
                elif game == 'Мимо':
                    await gg.edit_text(f'💥❎ | Вы промазали... Деньги остаются при вас', parse_mode='html')
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET ohota = ohota + 1 WHERE id=?', (message.from_user.id,))
                    users.connect.commit()
                elif game == 'Дядя Стёпа':
                    await gg.edit_text(f'💥😲 | Ёкараный бабай!\nВы попали в своего соседа дядю Стёпу, платите: <b>{int(args[1]) * 3}</b>💰, за его лечение', parse_mode='html')
                    users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", datas)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET ohota = ohota + 1 WHERE id=?', (message.from_user.id,))
                    users.connect.commit()
                elif game == 'Больница':
                    await gg.edit_text(f'🏥🐿 | Бешенная белка прогрызла вашу ногу!\nВы попали в больницу и оплатили: <b>{int(args[1]) * 1.5}</b>💰 за лечение!', parse_mode='html')
                    users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", datab)
                    users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                    users.cursor.execute(f'UPDATE users SET ohota = ohota + 1 WHERE id=?', (message.from_user.id,))
                    users.connect.commit()
            elif int(balance) < int(args[1]):
                await message.reply(f'❎ | У вас нет столько монет!\n💳 | Ваш баланс: {balance}💰 ', parse_mode='html')
        else:
            await message.reply(f'❎ | Ваша максимальная ставка: {stavka}💰', parse_mode='html')
    else:
        game_rule = chats.cursor.execute("SELECT game_rule from chats where chat_id = ?", (message.chat.id,)).fetchone()
        game_rule = (game_rule[0])
        if str(game_rule) == 'разрешено':
            if int(args[1]) <= int(stavka):
                if int(balance) >= int(args[1]):
                    gg = await message.reply(f'💥 | Выстрел... посмотрим в кого вы попали')
                    if game == 'Заяц':
                        await sleep(3)
                        await gg.edit_text(f'💥🐰 | Отлично!\nВы попали в зайца, вот ваша награда: <b>{summ2}</b>💰', parse_mode='html')
                        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data1)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET ohota = ohota + 1 WHERE id=?', (message.from_user.id,))
                        chats.cursor.execute(f'UPDATE chats SET chat_games = chat_games + 1 WHERE chat_id=?', (message.chat.id,))
                        chats.connect.commit()
                        users.connect.commit()
                    elif game == 'Волк':
                        await sleep(3)
                        await gg.edit_text(f'💥🐺 | Отлично!\nВы попали в волка, вот ваша награда: <b>{summ3}</b>💰', parse_mode='html')
                        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data2)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET ohota = ohota + 1 WHERE id=?', (message.from_user.id,))
                        chats.cursor.execute(f'UPDATE chats SET chat_games = chat_games + 1 WHERE chat_id=?', (message.chat.id,))
                        chats.connect.commit()
                        users.connect.commit()
                    elif game == 'Медведь':
                        await sleep(3)
                        await gg.edit_text(f'💥🐻 | Отлично!\nВы попали в медведя, вот ваша награда: <b>{summ4}</b>💰', parse_mode='html')
                        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data3)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET ohota = ohota + 1 WHERE id=?', (message.from_user.id,))
                        chats.cursor.execute(f'UPDATE chats SET chat_games = chat_games + 1 WHERE chat_id=?', (message.chat.id,))
                        chats.connect.commit()
                        users.connect.commit()
                    elif game == 'Мимо':
                        await sleep(3)
                        await gg.edit_text(f'💥❎ | Вы промазали... Деньги остаются при вас', parse_mode='html')
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET ohota = ohota + 1 WHERE id=?', (message.from_user.id,))
                        chats.cursor.execute(f'UPDATE chats SET chat_games = chat_games + 1 WHERE chat_id=?', (message.chat.id,))
                        chats.connect.commit()
                        users.connect.commit()
                    elif game == 'Дядя Стёпа':
                        await sleep(3)
                        await gg.edit_text(f'💥😲 | Ёкараный бабай!\nВы попали в своего соседа дядю Стёпу, платите: <b>{int(args[1]) * 3}</b>💰, за его лечение', parse_mode='html')
                        users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", datas)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET ohota = ohota + 1 WHERE id=?', (message.from_user.id,))
                        chats.cursor.execute(f'UPDATE chats SET chat_games = chat_games + 1 WHERE chat_id=?', (message.chat.id,))
                        chats.connect.commit()
                        users.connect.commit()
                    elif game == 'Больница':
                        await sleep(3)
                        await gg.edit_text(f'🏥🐿 | Бешенная белка прогрызла вашу ногу!\nВы попали в больницу и оплатили: <b>{int(args[1]) * 1.5}</b>💰 за лечение!', parse_mode='html')
                        users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", datab)
                        users.cursor.execute(f'UPDATE users SET games = games + 1 WHERE id=?', (message.from_user.id,))
                        users.cursor.execute(f'UPDATE users SET ohota = ohota + 1 WHERE id=?', (message.from_user.id,))
                        chats.cursor.execute(f'UPDATE chats SET chat_games = chat_games + 1 WHERE chat_id=?', (message.chat.id,))
                        chats.connect.commit()
                        users.connect.commit()
                elif int(balance) < int(args[1]):
                    await message.reply(f'❎ | У вас нет столько монет!\n💳 | Ваш баланс: {balance}💰 ', parse_mode='html')
            else:
                await message.reply(f'❎ | Ваша максимальная ставка: {stavka} 💰', parse_mode='html')
        else:
            await message.reply(f'🚫 | В этом чате запрещено играть!')

#Пополнить
@dp.message_handler(regexp=r"(^Пополнить счёт|пополнить счёт|^Пополнить счет|пополнить счет) ?(\d+)?")
async def bankplus(message: types.Message):
    balance = users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone()
    balance = (balance[0])
    bank = users.cursor.execute("SELECT bank from users where id = ?", (message.from_user.id,)).fetchone()
    bank = (bank[0])
    command_parse = re.compile(r"(^Пополнить счёт|пополнить счёт|^Пополнить счет|пополнить счет) ?(\d+)?")
    parsed = command_parse.match(message.text)
    suma = parsed.group(2)
    suma = int(suma)
    data1 = {}
    data1["suma"] = suma
    data1['user_id'] = message.from_user.id
    if int(balance) >= suma:
        users.cursor.execute("""UPDATE users SET bank = bank + :suma WHERE id = :user_id;""", data1)
        users.cursor.execute("""UPDATE users SET balance = balance - :suma WHERE id = :user_id;""", data1)
        await message.reply(f"Вы успешно пополнили свой счёт на <code>{suma}💰</code>", parse_mode='html')
    else:
        await message.reply(f"У вас недостаточно монет для пополнения счёта!", parse_mode='html')

#Снять
@dp.message_handler(regexp=r"(^Снять со счёта|снять со счёта|^Снять со счета|снять со счета) ?(\d+)?")
async def bankminus(message: types.Message):
    balance = users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone()
    balance = (balance[0])
    bank = users.cursor.execute("SELECT bank from users where id = ?", (message.from_user.id,)).fetchone()
    bank = (bank[0])
    command_parse = re.compile(r"(^Снять со счёта|снять со счёта|^Снять со счета|снять со счета) ?(\d+)?")
    parsed = command_parse.match(message.text)
    suma = parsed.group(2)
    suma = int(suma)
    data1 = {}
    data1["suma"] = suma
    data1['user_id'] = message.from_user.id
    if int(bank) >= suma:
        users.cursor.execute("""UPDATE users SET balance = balance + :suma WHERE id = :user_id;""", data1)
        users.cursor.execute("""UPDATE users SET bank = bank - :suma WHERE id = :user_id;""", data1)
        await message.reply(f"Вы успешно сняли <code>{suma}💰</code> со счёта!", parse_mode='html')
    else:
        await message.reply(f"У вас недостаточно средств на счету!", parse_mode='html')

#Текстовые команды:
@dp.message_handler()
async def echo_message(message: types.Message):
    #Регистрация чата
    msg = message
    chat_id = msg.chat.id
    chat_name = msg.chat.title
    chat_username = msg.chat.username
    now = datetime.now()
    reg_data = now.strftime("%d.%m.%Y")
    chat_status = "Обычный"
    game_rule = "разрешено"
    chat_rules = "Отсутствуют"
    mod_cmd = 'да'
    rules = "Не указаны!"
    welcome = "Добро пожаловать в чат!"
    chats.cursor.execute(f"SELECT chat_id FROM chats WHERE chat_id = '{chat_id}'")
    if message.chat.type == 'supergroup':
        if chats.cursor.fetchone() is None:
            chats.cursor.execute("INSERT INTO chats VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", (chat_id, chat_name, chat_username, game_rule, 0, reg_data, chat_status, chat_rules, mod_cmd, rules, welcome))
            await bot.send_message(config.owner, f'#НОВЫЙ_ЧАТ\n👥 Название: {chat_name}\n📎 Ссылка: @{chat_username}\n✅ ID: <code>{chat_id}</code>')
            chats.connect.commit()
        else:
            pass
    else:
        pass

    if message.text.lower() in ["Б", "б", "Баланс", "баланс", "💰", "Мои 💰", "мои 💰", "Мой 💰", "мой 💰"]:
        id = message.from_user.id
        users.cursor.execute(f"SELECT id from users WHERE id = '{id}'")
        if users.cursor.fetchone() is None:
            await message.reply(f'Вы не зарегистрированы!\nВведите /start')
        else:
            if message.reply_to_message:
                name2 = message.reply_to_message.from_user.get_mention(as_html=True)
                balance = users.cursor.execute("SELECT balance from users where id = ?", (message.reply_to_message.from_user.id,)).fetchone()
                balance = (balance[0])
                bank = users.cursor.execute("SELECT bank from users where id = ?", (message.reply_to_message.from_user.id,)).fetchone()
                bank = (bank[0])
                x1 = '{:,}'.format(balance)
                x2 = '{:,}'.format(bank)
                await message.answer(f'👤 | {name2}\n💰 | Баланс: <code>{x1}</code>\n🏦 | Банк: <code>{x2}</code>')
            else:
                name1 = message.from_user.get_mention(as_html=True)
                balance = users.cursor.execute("SELECT balance from users where id = ?", (message.from_user.id,)).fetchone()
                balance = (balance[0])
                bank = users.cursor.execute("SELECT bank from users where id = ?", (message.from_user.id,)).fetchone()
                bank = (bank[0])
                x1 = '{:,}'.format(balance)
                x2 = '{:,}'.format(bank)
                await message.answer(f'👤 | {name1}\n💰 | Баланс: <code>{x1}</code>\n🏦 | Банк: <code>{x2}</code>')

    #Топ богачей
    elif message.text.lower() in ["Топ б", "топ б", "Богачи", "богачи", "Топ 💰", "топ 💰"]:
        top15 = users.cursor.execute('SELECT name, balance FROM users WHERE balance IS NOT Null and status IS NOT "Администратор" and status IS NOT "Создатель бота" ORDER BY balance DESC LIMIT 15').fetchall()
        table = []
        for num, (fname, x) in enumerate(top15, 1):
            table.append(f'{num}. {fname} – {x}💰\n' )
        await message.answer('📊💰 | Топ 15 богачей бота:\n'+''.join(table), parse_mode='html', disable_web_page_preview=True)

    #Топ хуёв
    elif message.text.lower() in ["Топ х", "топ х", "Топ хуёв", "топ хуёв"]:
        top15 = users.cursor.execute('SELECT name, dick FROM users WHERE dick IS NOT Null and status IS NOT "Администратор" and status IS NOT "Создатель бота" ORDER BY dick DESC LIMIT 15').fetchall()
        table = []
        for num, (fname, x) in enumerate(top15, 1):
            table.append(f'{num}. {fname} – {x} см.\n' )
        await message.answer('📊🍆 | Топ 15 ялдаков бота:\n'+''.join(table), parse_mode='markdown', disable_web_page_preview=True)

    #Топ игроков
    elif message.text.lower() in ["Топ и", "топ и", "Топ игроков", "топ игроков", "Топ 🎮", "топ 🎮"]:
        top15 = users.cursor.execute('SELECT name, games FROM users WHERE games IS NOT Null and status IS NOT "Администратор" and status IS NOT "Создатель бота" ORDER BY games DESC LIMIT 15').fetchall()
        table = []
        for num, (fname, x) in enumerate(top15, 1):
            table.append(f'{num}. {fname} - {x}\n' )
        await message.answer('📊🎮 | Топ 15 игроков бота:\n'+''.join(table), parse_mode='html', disable_web_page_preview=True)


###ЗАПУСК###
if __name__ == "__main__":
    dp.middleware.setup(ThrottlingMiddleware())
    executor.start_polling(dp, skip_updates=True)
