# region imports
import asyncio
import csv
import json
import logging
import re
import traceback
from asyncio import AbstractEventLoop
from datetime import datetime, timedelta

import pytz
from aiogram import Bot, Dispatcher
from aiogram import types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InputFile, Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ContentType, \
    ReplyKeyboardMarkup, KeyboardButton, Chat, MessageEntity
import emoji
from aiogram.utils.callback_data import CallbackData
from apscheduler.triggers.date import DateTrigger

import config
import filters
import mails
import middlewares
import models.owners
import users
from config import ADMINS, BOT_TOKEN
from models.settings import Setting
from models.user import User
from scheduler_manager import scheduler
from users import count_users, delete_user, get_users

# endregion

logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] {%(filename)s:%(funcName)s:%(lineno)d} %(levelname)s - %(message)s',
                    datefmt='%H:%M:%S')

loop: AbstractEventLoop

# start_bot = Bot(token=BOT_TOKEN)
# dp = Dispatcher(start_bot, storage=MemoryStorage())

# Список токенов ботов
# TOKENS = [entry.token for entry in Setting.select(Setting.token)]
TOKENS = [BOT_TOKEN]

# config.ADMINS = [user.id for user in User.select().where(User.is_admin == True)]

# Создание экземпляров ботов и диспетчера для каждого токена
bots = [Bot(token) for token in TOKENS]
dispatchers = [Dispatcher(bot, storage=MemoryStorage()) for bot in bots]

bot_functions = []
# словарь чтобы запомнить юзеров которые нажали на запрос
users_verifying = dict()


# region Start Bot

# class AddBotState(StatesGroup):
#     add_token = State()
#
#
# @dp.message_handler(commands=["start"], state=None)
# async def start(message: Message, state: FSMContext):
#     await message.answer("Привет", reply_markup=start_markup())
#
#
# @dp.callback_query_handler(text=["start"], state=None)
# async def start(callback: CallbackQuery, state: FSMContext):
#     await callback.message.answer("Привет", reply_markup=start_markup())
#
#
# @dp.callback_query_handler(text="my_bots")
# async def my_bots(callback: CallbackQuery):
#     user_id = callback.from_user.id
#     owner_bots: [Setting] = Setting.select().where(Setting.owner_id == user_id)
#     if len(owner_bots) == 0:
#         await callback.message.answer("У вас нет ботов", reply_markup=no_bot_markup())
#         return
#     await callback.message.answer("Список ботов:", reply_markup=await bots_markup("my", owner_bots))
#
#
# @dp.callback_query_handler(lambda call: call.data.startswith("my_bot_"))
# async def my_bots(callback: CallbackQuery):
#     bot_id = int(callback.data.split("_")[2])
#
#     found_bot = None
#     for bot in bots:
#         if bot.id == bot_id:
#             found_bot = bot
#             break
#
#     if found_bot is not None:
#         bot_data = await found_bot.get_me()
#         await callback.message.answer(f"Bot Name: {bot_data.full_name} \n"
#                                       f"Id: {bot_data.id} \n"
#                                       f"Username: {bot_data.username}",
#                                       reply_markup=delete_bot_markup("delete", bot_id))
#
#
# @dp.callback_query_handler(lambda call: call.data.startswith("delete_bot_"))
# async def delete_bot(callback: CallbackQuery):
#     bot_id = int(callback.data.split("_")[2])
#
#     _dispatcher = None
#     for disp in dispatchers:
#         if disp.bot.id == bot_id:
#             _dispatcher = disp
#             break
#
#     for bot in bots:
#         if bot.id == bot_id:
#             bot = Setting.get(Setting.id == bot_id)
#             # Delete users associated with the bot
#             users_to_delete = User.select().where(User.bot == bot)
#             for user in users_to_delete:
#                 user.delete_instance()
#
#             Setting.delete_by_id(bot_id)
#             break
#     await callback.message.answer("Бот удален")
#
#     _dispatcher.stop_polling()
#
#
# def delete_bot_markup(action, bot_id):
#     markup = InlineKeyboardMarkup(row_width=1)
#     markup.add(InlineKeyboardButton("❌ Удалить", callback_data=action + "_bot_" + str(bot_id)))
#     markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="my_bots"))
#     return markup
#
#
# def no_bot_markup():
#     markup = InlineKeyboardMarkup(row_width=1)
#     markup.add(InlineKeyboardButton("➕ Создать бота", callback_data="add_bot"))
#     markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="start"))
#     return markup
#
#
# async def bots_markup(action: str, owner_bots: [Setting]):
#     markup = InlineKeyboardMarkup(row_width=1)
#     i = 0
#     j = 0
#     buttons = []
#     while i < len(owner_bots):
#         bot: Setting = owner_bots[i]
#
#         buttons.append(InlineKeyboardButton("@" + bot.username, callback_data=action + "_bot_" + str(bot.id)))
#         if j == 1 or i == len(owner_bots) - 1:
#             markup.row(*buttons)
#             buttons.clear()
#             j = 0
#         j += 1
#         i += 1
#     markup.row(InlineKeyboardButton("⬅️ Назад", callback_data="start"))
#     return markup
#
#
# @dp.callback_query_handler(text="add_bot")
# async def add_bot(callback: CallbackQuery):
#     await AddBotState.add_token.set()
#     await callback.message.answer("Пришлите токен бота")
#
#
# @dp.message_handler(state=AddBotState.add_token)
# async def add_bot(message: Message, state: FSMContext):
#     token = message.text
#
#     pattern = r'^[0-9]{9,11}:[a-zA-Z0-9_-]{35}$'
#     match = re.match(pattern, token)
#
#     if not bool(match):
#         await message.answer("Токен не правильный")
#
#     owner_id = message.chat.id
#
#     owner = models.owners.Owner.get_or_none(owner_id)
#
#     if owner is None:
#         owner = models.owners.Owner.create(id=owner_id)
#
#         # Короч добавляем админа, когда юзер вводит сообщение,
#         # то ему присваивается эта админка, фильтр чекает юзера и чекает бота,
#         # если юзер админ и принадлежит конкретному боту, то ему отправляется админка
#         # добавляем единожды, так как при добавлении юзер станет админом
#         ADMINS.append(owner_id)
#
#     bot = Bot(token)
#
#     bot_data = await bot.get_me()
#     try:
#         setting: Setting = Setting.create(id=bot.id, owner=owner, username=bot_data.username)
#         setting.token = token
#         setting.save()
#     except:
#         await message.answer("Бот уже запущен")
#         await state.finish()
#         return
#
#     bots.append(bot)
#
#     await message.answer(f"Бот @{bot_data.username}  успешно добавлен ✅")
#     await state.finish()
#
#
# async def set_bot(bot: Bot):
#     dispatcher_new = Dispatcher(bot, storage=MemoryStorage())
#     set_dispatcher(dispatcher_new)
#     await dispatcher_new.start_polling()
#
#
# def create_dispatcher(bot: Bot):
#     new_dispatcher = Dispatcher(bot, storage=MemoryStorage())
#     set_dispatcher(new_dispatcher)
#     dispatchers.append(new_dispatcher)
#
#
# def start_markup():
#     markup = InlineKeyboardMarkup(row_width=1)
#
#     markup.add(InlineKeyboardButton("🤖 Боты", callback_data="my_bots"))
#     markup.add(InlineKeyboardButton("➕ Создать бота", callback_data="add_bot"))
#     return markup
#
#
# endregion

# region decorators
def register_message_handler(*custom_filters, commands=None, state=None, content_types=None, **kwargs):
    def decorator(handler):
        bot_functions.append(
            lambda d:
            d.register_message_handler(handler, *custom_filters, commands=commands, content_types=content_types,
                                       state=state, **kwargs))
        return handler

    return decorator


def register_chat_join_request_handler(*custom_filters, **kwargs):
    def decorator(handler):
        bot_functions.append(
            lambda d:
            d.register_chat_join_request_handler(handler, *custom_filters, **kwargs))
        return handler

    return decorator


def register_callback_query_handler(*custom_filters, state=None, **kwargs):
    def decorator(handler):
        bot_functions.append(
            lambda d:
            d.register_callback_query_handler(handler, *custom_filters, state=state, **kwargs))
        return handler

    return decorator


# endregion


class UserMessage:
    def __init__(self):
        self.Id: int = -1
        self.Message_json: str = ""
        self.Delete_time = "0"
        self.Buttons: str = ""
        self.On_Off = True
        self.Schedule = "0"

    def to_dict(self):
        return {
            'Id': self.Id,
            'Message_json': self.Message_json,
            'Start_delete_time': self.Delete_time,
            'Buttons': self.Buttons,
            'On_Off': self.On_Off,
            'Schedule': self.Schedule
        }

    @classmethod
    def from_dict(cls, data):
        message = cls()
        message.Id = data.get('Id')
        message.Message_json = data.get('Message_json')
        message.Delete_time = data.get('Start_delete_time', "0")
        message.Buttons = data.get('Buttons')
        message.On_Off = data.get('On_Off', True)
        message.Schedule = data.get('Schedule', "0")
        return message


@register_message_handler(commands=["start"])
async def start(message: Message, state: FSMContext):
    await message.answer("Приветствие \n/adm")


@register_message_handler(commands=["id"], state="*")
async def get_id(message: types.Message):
    await message.answer(message.from_user.id)


@register_message_handler(lambda msg: msg.text == "/chat_id", state="*")
async def chat_id_get(message: Message, state: FSMContext):
    await state.set_state()
    await message.answer(message.chat.id)


@register_chat_join_request_handler()
async def join_request_handler(join_request: types.ChatJoinRequest, state: FSMContext):
    bot = join_request.bot

    user_id = join_request.from_user.id
    chat_id = join_request.chat.id
    title = join_request.chat.title

    # если юзер базе, то отправляем только приветствие
    if not users.get_user(user_id) is None:
        await send_all_messages(bot, user_id)
        return

    setting: Setting = Setting.get(id=bot.id)

    # добавление юзер в список для верификации
    users_verifying[user_id] = chat_id

    if not setting.captcha_is_on:
        await send_all_messages(bot, user_id, title)
        return

    user = join_request.from_user

    try:
        if not setting.captcha_after:
            await send_captcha(bot, user_id, user)
        else:
            await send_all_messages(bot, user_id, title, send_captcha, *[bot, user_id, user, state])

    except Exception as e:
        await notify_admins(bot, "Каптча не настроена")
        logging.exception(e)


# пока юзер не приймет капчу она будет приходить
async def send_captcha(bot: Bot, user_id, user: User, delay=True):
    setting: Setting = Setting.get(id=bot.id)

    data = json.loads(setting.captcha_text)
    message = types.Message(**data)

    title = (await message.bot.get_chat(users_verifying[user_id])).title

    text = format_text(message, user, title)

    if delay:
        delay_time = setting.captcha_first_delay
        if delay_time is not None or delay_time != 0:
            await asyncio.sleep(delay_time)
        delay = False
    try:
        message_data = await bot.send_message(
            user.id,
            text,
            parse_mode="HTML",
            reply_markup=get_captcha_markup(json.loads(setting.captcha_buttons)))
        # await state.update_data(captcha_msg=message_data)
    except Exception as e:
        logging.exception(e)
        return

    time = setting.captcha_time
    if time is None or time == 0:
        return
    await asyncio.sleep(time)
    try:
        await message_data.delete()
    except:
        return
    if user_id in users_verifying:
        await send_captcha(bot, user_id, user, delay)


# region Admin menu
@register_message_handler(commands=["adm", "admin"], is_admin=True, state=None)
async def admin_menu(message: Message, state: FSMContext):
    await message.answer("Админка открыта", reply_markup=get_admin_markup())


@register_callback_query_handler(text="get_db", is_admin=True)
async def export_users(call: CallbackQuery):
    count = count_users()

    with open("users.csv", "w", encoding="UTF8", newline="") as f:
        writer = csv.writer(f)

        writer.writerow(["id", "username", "created_at"])

        for user in get_users():
            writer.writerow(
                [user.id, user.username, user.created_at]
            )

    text_file = InputFile("users.csv", filename="users.csv")
    await call.answer()
    await call.message.answer_document(text_file)
    with open("database.sqlite3", "rb") as f:
        await call.message.answer_document(f)


@register_callback_query_handler(text="clear_users", is_admin=True)
async def users_count(call: CallbackQuery):
    msg = await call.message.answer(f"Удаляем неактивных..")
    users = get_users()
    active = 0
    non_active = 0
    count = 0
    for user in users:
        if count % 50 == 0:
            await msg.edit_text(f"Считаем.. {count} всего, {active} активных, {non_active} неактивных удалено")
        count += 1
        try:
            if await call.bot.send_chat_action(user.id, "typing"):
                active += 1
        except Exception as e:
            logging.exception(e)
            delete_user(user.id)
            non_active += 1

    await call.message.answer(
        f"Общее количество: {count}\nАктивных пользователей: {active}, удалено неактивных: {non_active}")


@register_callback_query_handler(text="get_users", is_admin=True)
async def users_count(call: CallbackQuery):
    msg = await call.message.answer(f"Считаем..")
    users = get_users()
    active = 0
    count = 0
    for user in users:
        if count % 10 == 0:
            await msg.edit_text(f"Считаем.. {count} всего, {active} активных")
        count += 1
        try:
            if await call.bot.send_chat_action(user.id, "typing"):
                active += 1
        except Exception as e:
            if "Retry" in e.__class__.__name__:
                print(e.__class__.__name__)

    await call.message.answer(f"Общее количество: {count}\nАктивных пользователей: {active}")


# endregion


# region Captcha settings menu
class VerificationSet(StatesGroup):
    captcha_buttons = State()
    captcha_msg = State()
    resend_time = State()
    delay_time = State()


@register_callback_query_handler(text="settings_captcha", is_admin=True)
async def _verification_set(callback: CallbackQuery, state: FSMContext):
    bot_id = callback.bot.id
    setting: Setting = Setting.get(id=bot_id)
    is_on = setting.captcha_is_on
    is_after = setting.captcha_after
    await callback.message.answer("Настройка капчи", reply_markup=get_captcha_set_markup(is_on, is_after))


# region Set captcha text
@register_callback_query_handler(text="captcha_text")
async def _verification_set(callback: CallbackQuery, state: FSMContext):
    await VerificationSet.captcha_msg.set()
    await callback.message.answer("Введите сообщение капчи")


@register_message_handler(state=VerificationSet.captcha_msg)
async def _verification_set(message: types.Message, state: FSMContext):
    bot_id = message.bot.id
    setting: Setting = Setting.get(id=bot_id)
    setting.captcha_text = message.as_json()
    setting.save()
    await state.finish()
    await message.answer("Готово")


# endregion


# region Set captcha button apply text
@register_callback_query_handler(text="captcha_buttons")
async def _verification_set(callback: CallbackQuery, state: FSMContext):
    await VerificationSet.captcha_buttons.set()
    await callback.message.answer("Введите что будет отображаться на кнопках каптчи в формате\n Кнопка1;Кнопка2")


@register_message_handler(state=VerificationSet.captcha_buttons)
async def _verification_set(message: types.Message, state: FSMContext):
    bot_id = message.bot.id
    setting: Setting = Setting.get(id=bot_id)
    buttons = message.text.split(';')

    setting.captcha_buttons = json.dumps(buttons)
    setting.save()
    await state.finish()
    await message.answer("Готово")


# endregion


# region Set captcha resend time
@register_callback_query_handler(text="captcha_time")
async def _verification_set(callback: CallbackQuery, state: FSMContext):
    await VerificationSet.resend_time.set()
    await callback.message.answer("Введите время повтора каптчи")


@register_message_handler(state=VerificationSet.resend_time, content_types=ContentType.ANY)
async def _verification_set(message: types.Message, state: FSMContext):
    bot_id = message.bot.id
    setting: Setting = Setting.get(id=bot_id)
    try:
        setting.captcha_time = int(message.text)
        setting.save()
    except Exception as e:
        logging.exception(e)
        await message.answer("Введите число")
        return
    await state.finish()
    await message.answer("Готово")


# endregion


# region Set captcha delay
@register_callback_query_handler(text="captcha_delay")
async def _verification_set(callback: CallbackQuery, state: FSMContext):
    await VerificationSet.delay_time.set()
    await callback.message.answer("Введите время задержки каптчи")


@register_message_handler(state=VerificationSet.delay_time, content_types=ContentType.ANY)
async def _verification_set(message: types.Message, state: FSMContext):
    bot_id = message.bot.id
    setting: Setting = Setting.get(id=bot_id)
    try:
        setting.captcha_first_delay = int(message.text)
        setting.save()
    except Exception as e:
        logging.exception(e)
        await message.answer("Введите число")
        return
    await state.finish()
    await message.answer("Готово")


# endregion


# region On off captcha
@register_callback_query_handler(text="captcha_on_off")
async def _verification_set(callback: CallbackQuery, state: FSMContext):
    bot_id = callback.bot.id
    setting: Setting = Setting.get(id=bot_id)
    setting.captcha_is_on = not setting.captcha_is_on
    setting.save()
    text = "Каптча включина 💡" if setting.captcha_is_on else "Каптча выключина 🔌"
    await callback.message.answer(text)


# endregion


# region Captcha place
@register_callback_query_handler(text="captcha_place")
async def _verification_set(callback: CallbackQuery, state: FSMContext):
    bot_id = callback.bot.id
    setting: Setting = Setting.get(id=bot_id)
    setting.captcha_after = not setting.captcha_after
    setting.save()
    text = "Каптча вконце ⬇" if setting.captcha_after else "Каптча вначале ⬆"
    await callback.message.answer(text)


# endregion

# endregion


# region markups
def get_captcha_markup(buttons: list):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    if len(buttons) == 1:
        markup.resize_keyboard = False

    buttons_kb = []

    for button in buttons:
        buttons_kb.append(KeyboardButton(button))

    markup.row(*buttons_kb)
    return markup


def get_admin_markup():
    markup = InlineKeyboardMarkup(row_width=1)

    markup.add(InlineKeyboardButton("Скачать БД 📁", callback_data="get_db"))
    markup.add(InlineKeyboardButton("Посчитать пользователей 👥", callback_data="get_users"))
    markup.add(InlineKeyboardButton("Почистить неактивных", callback_data="clear_users"))
    # markup.add(InlineKeyboardButton("Посчитать пользователей БЫСТРО 👥 (beta)", callback_data="get_users_fast"))
    markup.add(InlineKeyboardButton("Сделать рассылку 📬", callback_data="make_mail"))
    markup.add(InlineKeyboardButton("Настройка начальных сообщений ✉️", callback_data="settings_start"))
    markup.add(InlineKeyboardButton("Настройка капчи ♑", callback_data="settings_captcha"))
    return markup


def get_captcha_set_markup(is_on, is_after):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Изменить текст каптчи 📝", callback_data="captcha_text"))
    markup.add(InlineKeyboardButton("Изменить время каптчи 🕒", callback_data="captcha_time"))
    markup.add(InlineKeyboardButton("Изменить таймер каптчи ⏱", callback_data="captcha_delay"))
    markup.add(InlineKeyboardButton("Изменить кнопки каптчи ✅", callback_data="captcha_buttons"))
    # markup.add(InlineKeyboardButton("Изменить текст кнопки ❌", callback_data="captcha_btn_decline"))
    text = "Включить каптчу 🔌" if not is_on else "Выключить каптчу 💡"
    markup.add(InlineKeyboardButton(text, callback_data="captcha_on_off"))
    text = "Каптча вконце ⬇" if is_after else "Каптча вначале ⬆"
    markup.add(InlineKeyboardButton(text, callback_data="captcha_place"))
    return markup


def get_messages_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Добавить сообщение ➕", callback_data="add_message"))
    markup.add(InlineKeyboardButton("Изменить сообщение 📝", callback_data="edit_message"))
    markup.add(InlineKeyboardButton("Удалить сообщение ❌", callback_data="delete_message"))
    return markup


def get_choose_message_markup(action: str, number):
    markup = InlineKeyboardMarkup(row_width=1)
    i = 0
    j = 0
    buttons = []
    while i < number:
        buttons.append(InlineKeyboardButton(str(i + 1), callback_data=action + str(i + 1)))
        if j == 2 or i == number - 1:
            markup.row(*buttons)
            buttons.clear()
            j = 0
        j += 1
        i += 1
    return markup


def get_quit_btn(text="Отмена"):
    return InlineKeyboardButton(text, callback_data="quit")


# endregion


@register_callback_query_handler(text="quit", state="*")
async def _quit(call: CallbackQuery, state: FSMContext):
    await state.finish()
    await call.answer()
    await call.message.answer("Отменено")


# Настройка начальных сообщений
@register_callback_query_handler(text="settings_start", is_admin=True)
async def message_settings(call: CallbackQuery, state: FSMContext):
    bot_id = call.bot.id
    await state.update_data(setting_id=bot_id)
    await call.bot.send_message(call.from_user.id, "Выберите действие:", reply_markup=get_messages_markup())


# region Добавить начальное сообщение
class AddMessageStates(StatesGroup):
    msg = State()
    change_kb = State()
    delete_date = State()
    schedule = State()


@register_callback_query_handler(text="add_message", is_admin=True)
async def add_message(call: CallbackQuery, state: FSMContext):
    bot_id = call.bot.id
    await AddMessageStates.msg.set()
    await state.update_data(setting_id=bot_id, user_msg=UserMessage())
    await call.bot.send_message(call.from_user.id, "Введите текст сообщения:")


@register_message_handler(state=AddMessageStates.msg, is_admin=True, content_types=ContentType.ANY)
async def add_message(message: Message, state: FSMContext):
    bot_id = message.bot.id
    data = await state.get_data()
    user_msg: UserMessage = data.get("user_msg")
    user_msg.Message_json = message.as_json()

    # сохраняет созданное сообщение в базу
    await add_to_messages(bot_id, user_msg)
    await state.finish()
    await state.update_data(setting_id=bot_id, user_msg=user_msg)
    await menu_msg(message, state, message.chat.id, user_msg.Id)


# endregion

# region Изменить начальное сообщение
class EditMessageStates(StatesGroup):
    edit = State()
    change_kb = State()
    delete_date = State()
    schedule = State()


@register_callback_query_handler(text="edit_message", is_admin=True)
async def edit_message(call: CallbackQuery, state: FSMContext):
    bot_id = call.bot.id
    await state.update_data(setting_id=bot_id)
    number = await show_messages(call.bot, call.from_user.id)

    if number == 0:
        await call.message.answer("Сообщений нету")
        return

    await call.message.answer("Выберите сообщение для редактирования:",
                              reply_markup=get_choose_message_markup("edit_message_", number))


@register_callback_query_handler(lambda call: call.data.startswith("edit_message_"), is_admin=True)
async def edit_message(call: CallbackQuery, state: FSMContext):
    message_id = int(call.data.split("_")[2])
    bot_id = call.bot.id
    await state.update_data(setting_id=bot_id)

    messages = await get_messages(bot_id)

    if len(messages) == 0:
        await call.message.answer("Сообщений нету")
        return

    await menu_msg(call.message, state, call.from_user.id, message_id)


# endregion

# region Удалить начальное сообщение
@register_callback_query_handler(text="delete_message", is_admin=True)
async def delete_message(call: CallbackQuery, state: FSMContext):
    bot_id = call.bot.id
    await state.update_data(setting_id=bot_id)

    number = await show_messages(call.bot, call.from_user.id)

    if number == 0:
        await call.message.answer("Сообщений нету")
        return

    await call.message.answer("Выберите сообщение для удаления:",
                              reply_markup=get_choose_message_markup("delete_message_", number))


@register_callback_query_handler(lambda call: call.data.startswith("delete_message_"), is_admin=True)
async def delete_message(call: CallbackQuery, state: FSMContext):
    message_id = int(call.data.split("_")[2])
    bot_id = call.bot.id

    messages = await get_messages(bot_id)

    if len(messages) == 0:
        await call.message.answer("Сообщений нету")
        return

    await delete_user_message(bot_id, message_id)
    await call.message.answer("Сообщение удаленно")


# endregion

async def menu_msg(message, state, call_user_id, message_id: int):
    setting_id = await get_state_set_id(state)
    setting: Setting = Setting.get_or_none(id=setting_id)

    user_message = UserMessage()
    await MessageStates.menu.set()
    try:
        user_message_json = json.loads(setting.messages)
        user_message = UserMessage.from_dict(user_message_json[message_id - 1])

        start_kb = load_kb(user_message.Buttons)

        saved_message = json_to_tg_message(user_message.Message_json)

        await saved_message.copy_to(call_user_id, reply_markup=start_kb)

        await state.update_data(setting_id=setting_id, user_msg=user_message)
    except Exception as e:
        logging.exception(e)
        await message.answer("Сообщение не настроено")

    kb = InlineKeyboardMarkup(row_width=1)
    # kb.add(InlineKeyboardButton("Изменить ссылку 🔗", callback_data="change_link"))
    kb.add(InlineKeyboardButton("Изменить текст 📝️", callback_data="change_default"))
    kb.add(InlineKeyboardButton("Настроить отложенную отправку 🕑️", callback_data="change_message_schedule"))
    kb.add(InlineKeyboardButton("Изменить клавиатуру ⌨️", callback_data="change_start_kb"))
    kb.add(InlineKeyboardButton("Настроить время удаления ⏱️", callback_data="change_message_delete"))
    if user_message.On_Off:
        change_start_text = "Выключить сообщение 🔌"
    else:
        change_start_text = "Включить сообщение 💡"
    kb.add(InlineKeyboardButton(change_start_text, callback_data="change_start"))
    kb.add(get_quit_btn("Выход"))

    await message.answer(f"Меню для начального сообщения {message_id}", reply_markup=kb)


class MessageStates(StatesGroup):
    menu = State()
    msg = State()
    change_kb = State()
    delete_date = State()
    schedule = State()


# region Message text
# Изменить текст сообщения
@register_callback_query_handler(text="change_default", state=MessageStates.menu, is_admin=True)
async def change_message_text(call: CallbackQuery):
    await MessageStates.msg.set()
    await call.answer()
    await call.message.answer("Отправьте сообщение для начального сообщения")


# Изменить текст сообщения
@register_message_handler(is_admin=True, state=MessageStates.msg, content_types=ContentType.ANY)
async def change_message_text(message: Message, state: FSMContext):
    set_id = await get_state_set_id(state)
    user_message = await get_state_user_msg(state)

    user_message.Message_json = message.as_json()
    await state.update_data(user_msg=user_message)
    await save_message(set_id, user_message)
    await MessageStates.menu.set()
    await message.answer("Успешно изменено!")


# endregion

# region Message schedule
# Настроить отложить сообщение
@register_callback_query_handler(text="change_message_schedule", state=MessageStates.menu, is_admin=True)
async def change_message_schedule(call: CallbackQuery):
    await MessageStates.schedule.set()
    await call.answer()
    await call.message.answer("Введите время, через которое отправить рассылку, в формате гг:мм:сс")


# Настроить время отложенного сообщения
@register_message_handler(is_admin=True, state=MessageStates.schedule)
async def change_schedule_time(message: Message, state: FSMContext):
    set_id = await get_state_set_id(state)
    user_message = await get_state_user_msg(state)

    try:
        if message.text != "0":
            datetime.strptime(message.text, "%H:%M:%S")
    except:
        await message.answer("Неправильный формат")
        return
    await MessageStates.menu.set()

    user_message.Schedule = message.text
    await state.update_data(user_msg=user_message)
    await save_message(set_id, user_message)
    await message.answer("Успешно!")


# endregion

# region Message buttons
# Изменить клавиатуру
@register_callback_query_handler(text="change_start_kb", state=MessageStates.menu)
async def _process_change_kb(call: CallbackQuery, state: FSMContext):
    await MessageStates.change_kb.set()
    await call.answer()
    await call.message.answer("Отправьте клавиатуру в формате \n"
                              "текст;ссылка\n"
                              "где каждая строчка это отдельная кнопка\n"
                              "Пример:\n"
                              "Google;google.com\n"
                              "Facebook;facebook.com")


@register_message_handler(state=MessageStates.change_kb)
async def _process_change_kb_end(message: Message, state: FSMContext):
    set_id = await get_state_set_id(state)
    user_message = await get_state_user_msg(state)

    text = message.text
    kb = InlineKeyboardMarkup(row_width=1)
    try:
        btns = text.split("\n")
        for btn in btns:
            name, link = btn.split(";")
            kb.add(InlineKeyboardButton(name, url=link))

        user_message.Buttons = kb.as_json()

        send_to = message.chat.id

        data = json.loads(user_message.Message_json)
        saved_message = types.Message(**data)

        await state.update_data(user_msg=user_message)
        await MessageStates.menu.set()
        await saved_message.copy_to(send_to, reply_markup=kb)
        await save_message(set_id, user_message)

    except:
        await message.answer("Неправильный формат")
        return

    await message.answer("Успешно изменено!")


def load_kb(kb):
    if kb == "":
        return None
    start_kb = json.loads(kb)["inline_keyboard"]
    start_kb = InlineKeyboardMarkup(inline_keyboard=start_kb) if start_kb else None
    return start_kb


# endregion

# region Message delete
# Настроить удаление
@register_callback_query_handler(text="change_message_delete", state=MessageStates.menu, is_admin=True)
async def change_message_delete(call: CallbackQuery):
    await MessageStates.delete_date.set()
    await call.answer()
    await call.message.answer(
        "Введите время, через которое удалить сообщение, в формате гг:мм:сс. Чтобы сообщение не удалялось, напишите 0")


# Настроить время удаления сообщения
@register_message_handler(is_admin=True, state=MessageStates.delete_date)
async def change_delete_time(message: Message, state: FSMContext):
    set_id = await get_state_set_id(state)
    user_message = await get_state_user_msg(state)

    try:
        if message.text != "0":
            datetime.strptime(message.text, "%H:%M:%S")
    except:
        await message.answer("Неправильный формат")
        return

    await MessageStates.menu.set()

    user_message.Delete_time = message.text
    await state.update_data(user_msg=user_message)
    await save_message(set_id, user_message)
    await message.answer("Успешно!")


# endregion

# region Message on off
# Включение выключение начального сообщения
@register_callback_query_handler(text="change_start", state=MessageStates.menu, is_admin=True)
async def _change_start(call: CallbackQuery, state: FSMContext):
    set_id = await get_state_set_id(state)
    user_message = await get_state_user_msg(state)

    user_message.On_Off = not user_message.On_Off
    await save_message(set_id, user_message)
    await state.update_data(user_msg=user_message)
    text = "Начальное сообщение включино 💡" if user_message.On_Off else "Начальное сообщение выключино 🔌"
    await call.message.answer(text)


# endregion


class MailingStates(StatesGroup):
    msg = State()
    idle = State()
    change_kb = State()
    delete_time = State()
    schedule_time = State()
    amount = State()
    step = State()
    fast = State()


@register_callback_query_handler(text="make_mail", is_admin=True)
async def set_mail(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Выберите действие", reply_markup=mails.get_mail_menu())


# region Get users fast Beta
fast_user_count = {"count": 0, "active": 0}


@register_callback_query_handler(text="get_users_fast", is_admin=True)
async def users_count(call: CallbackQuery):
    await call.answer()
    msg = await call.message.answer(f"Считаем..")
    all_users = get_users()

    for users in mails.chunks(all_users, 25):
        for user in users:
            asyncio.create_task(check_is_active(call.bot, user.id))
        await asyncio.sleep(1)
        await msg.edit_text(f"Считаем... Всего {fast_user_count['count']}, активных: {fast_user_count['active']}")
    await call.message.answer(
        f"Общее количество: {fast_user_count['count']}\nАктивных пользователей: {fast_user_count['active']}")


async def check_is_active(bot: Bot, user_id):
    try:
        if await bot.send_chat_action(user_id, "typing"):
            fast_user_count["active"] += 1
    except Exception as e:
        logging.exception(e)
        pass
    finally:
        fast_user_count["count"] += 1


# endregion


# region Add Mail
@register_callback_query_handler(text="add_mail", is_admin=True)
async def set_mail(call: CallbackQuery, state: FSMContext):
    await MailingStates.msg.set()
    await call.answer()
    await call.message.answer("Отправьте сообщение для рассылки")


# region Mail text
@register_message_handler(is_admin=True, state=MailingStates.msg, content_types=ContentType.ANY)
async def _confirm_make_mail(message: Message, state: FSMContext):
    await MailingStates.idle.set()
    await state.update_data(msg=message)
    kb = mails.get_mail_kb()
    await message.answer("Меню действий", reply_markup=kb)


# endregion

# region Mail date
@register_callback_query_handler(text="add_send_date", state=MailingStates.idle)
async def _process_change_kb(call: CallbackQuery, state: FSMContext):
    await MailingStates.schedule_time.set()
    await call.message.answer("Введите время, когда отправить сообщение, в формате дд:гг:мм:сс")


@register_message_handler(is_admin=True, state=MailingStates.schedule_time)
async def _confirm_make_mail(message: Message, state: FSMContext):
    try:
        time = datetime.strptime(message.text, "%d:%H:%M:%S")
    except:
        await message.answer("Неправильный формат")
        return
    await state.update_data(send_date=time)
    await MailingStates.idle.set()
    kb = mails.get_mail_kb()
    await message.answer("Меню действий", reply_markup=kb)


# endregion

# region Mail delete time
@register_callback_query_handler(text="add_delete_time", state=MailingStates.idle)
async def _process_change_kb(call: CallbackQuery, state: FSMContext):
    await MailingStates.delete_time.set()
    await call.message.answer("Введите время, через которое удалить сообщение, в формате гг:мм:сс")


@register_message_handler(is_admin=True, state=MailingStates.delete_time)
async def _confirm_make_mail(message: Message, state: FSMContext):
    try:
        time = datetime.strptime(message.text, "%H:%M:%S")
    except:
        await message.answer("Неправильный формат")
        return
    await state.update_data(time=time)
    await MailingStates.idle.set()
    kb = mails.get_mail_kb()
    await message.answer("Меню действий", reply_markup=kb)


# endregion

# region Mail buttons
@register_callback_query_handler(text="change_kb", state=MailingStates.idle)
async def _process_change_kb(call: CallbackQuery, state: FSMContext):
    await MailingStates.change_kb.set()
    await call.answer()
    await call.message.answer("Отправьте клавиатуру в формате \n"
                              "текст;ссылка\n"
                              "где каждая строчка это отдельная кнопка\n"
                              "Пример:\n"
                              "Google;google.com\n"
                              "Facebook;facebook.com")


@register_message_handler(state=MailingStates.change_kb)
async def _process_change_kb_end(message: Message, state: FSMContext):
    text = message.text
    bot = message.bot
    kb = InlineKeyboardMarkup(row_width=1)

    try:
        btns = text.split("\n")
        for btn in btns:
            name, link = btn.split(";")
            kb.add(InlineKeyboardButton(name, url=link))
        async with state.proxy() as data:
            new_msg_id = await bot.copy_message(message.from_user.id, message.from_user.id, data["msg"].message_id,
                                                reply_markup=kb)
            await MailingStates.idle.set()
            data["msg_id"] = new_msg_id.message_id
            data["kb"] = kb

    except Exception as e:
        logging.exception(e)
        await message.answer("Неправильный формат")
        return

    kb = mails.get_mail_kb()
    await message.answer("Меню действий", reply_markup=kb)


# endregion

# region Mail cancel
@register_callback_query_handler(text="cancel_mail", state=MailingStates.idle)
async def _process_cancel_mail(call: CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.edit_text("Отменено", reply_markup=None)


# endregion

# region Mail Amount
@register_callback_query_handler(text="confirm_mail", state=MailingStates.idle, is_admin=True)
async def _make_mail(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await MailingStates.amount.set()
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Отправить всем", callback_data="send_all")
    )
    await call.message.answer("Укажите количество пользователей или нажмите кнопку чтобы отправить всем",
                              reply_markup=kb)


# отправить всем
@register_callback_query_handler(text="send_all", state=MailingStates.amount, is_admin=True)
async def _send_all_mail(call: CallbackQuery):
    await call.answer()
    await choose_fast_or_not(call.message)


# отправить количеству
@register_message_handler(state=MailingStates.amount, is_admin=True)
async def _make_mail(message: Message, state: FSMContext):
    max_amount = message.text

    if not max_amount.isdigit():
        await message.answer("Это не число!")
        return

    max_amount = int(max_amount)
    if max_amount < 0:
        await message.answer("Введите число больше 0")
        return

    await MailingStates.fast.set()
    await state.update_data(max_amount=max_amount)
    await choose_fast_or_not(message)


# endregion

# region Fast or not
fast_cb = CallbackData("fast_mail", "is_fast")


async def choose_fast_or_not(message: Message):
    await MailingStates.fast.set()
    kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("Обычная", callback_data=fast_cb.new("no")),
        InlineKeyboardButton("Быстрая (бета)", callback_data=fast_cb.new("yes")),
    )
    await message.answer(
        "Выберите режим отправки рассылки\nОбратите внимание, "
        "что быстрая может работать некорректно и её надо протестировать",
        reply_markup=kb)


# endregion


fast_count = {
    "count": 0,
    "good": 0,
    "bad": 0
}


# mail_thread_on = False


# WTF?
# @register_message_handler(commands=["stop"], is_admin=True)
# async def _stop_mail():
# global mail_thread_on
# mail_thread_on = False


@register_callback_query_handler(fast_cb.filter(), state=MailingStates.fast)
async def _process_mail(call: CallbackQuery, state: FSMContext, callback_data: dict):
    # global mail_thread_on
    msg = await call.message.answer(f"Делаем рассылку..")
    data = await state.get_data()
    await state.finish()
    message: Message = data["msg"]
    kb: InlineKeyboardMarkup = data.get("kb")
    max_amount = data.get("max_amount")
    has_limit = max_amount is not None
    from_user = call.from_user.id
    time: datetime = data.get("time")
    send_date: datetime = data.get("send_date")
    fast = True if callback_data.get("is_fast") == "yes" else False

    user_ids = users.get_user_ids()
    all_amount = max_amount if has_limit else len(user_ids)
    fast_count["count"] = 0
    fast_count["good"] = 0
    fast_count["bad"] = 0

    # mail_thread_on = True
    if send_date is not None:
        mail: mails.MailMessage = mails.MailMessage()
        mail.Message_json = message.as_json()
        mail.Buttons = kb.as_json() if kb is not None else ""
        # mail.Schedule =
        # mail.Delete_time =
        timezone = pytz.timezone('Europe/Kiev')
        now = datetime.now(timezone).date()

        date = datetime(now.year, now.month, send_date.day, send_date.hour, send_date.minute, send_date.second)
        job = scheduler.add_job(mails.make_mail, trigger=DateTrigger(date, 'Europe/Kiev'), args=(
            user_ids, fast, from_user, message, kb, time, has_limit, max_amount, msg, call, all_amount,
            f"make_mail_{call.from_user.id}_{message.message_id}"),
                                id=f"make_mail_{call.from_user.id}_{message.message_id}")

        mail.ShId = job.id
        await mails.add_to_mails(call.bot.id, mail)

    else:
        await mails.make_mail(user_ids, fast, from_user, message, kb, time, has_limit, max_amount, msg, call,
                              all_amount)
        await call.message.answer("Рассылка закончена!")
    # mail_thread_on = False
    # ====


# endregion


# region Удалить рассылку
@register_callback_query_handler(text="delete_mail", is_admin=True)
async def delete_mail(call: CallbackQuery, state: FSMContext):
    bot_id = call.bot.id
    await state.update_data(setting_id=bot_id)

    number = await mails.show_mails(call.bot, call.from_user.id)

    if number == 0:
        await call.message.answer("Сообщений нету")
        return

    await call.message.answer("Выберите сообщение для удаления:",
                              reply_markup=get_choose_message_markup("delete_mail_", number))


@register_callback_query_handler(lambda call: call.data.startswith("delete_mail_"), is_admin=True)
async def delete_mail(call: CallbackQuery, state: FSMContext):
    mail_id = int(call.data.split("_")[2])
    bot_id = call.bot.id

    messages = await mails.get_mails(bot_id)

    if len(messages) == 0:
        await call.message.answer("Сообщений нету")
        return

    await mails.delete_user_mail(bot_id, mail_id)
    await call.message.answer("Сообщение удаленно")


# endregion

# =======

@register_message_handler(is_admin=True, commands=["test"])
async def _confirm_make_mail(message: Message, state: FSMContext):
    msg = await message.answer(f"Считаем..")
    users = get_users()
    active = 0
    count = 0
    for user in users:
        if count % 10 == 0:
            await msg.edit_text(f"Считаем.. {count}, {active}")
        count += 1
        try:
            if await message.bot.send_chat_action(user.id, "typing"):
                active += 1
            # await asyncio.sleep(0.2)
        except Exception as e:
            print(e)
            if "Retry" in e.__class__.__name__:
                print(e)

    await message.answer(f"Общее количество: {count}\nАктивных пользователей: {active}")


# =======


# region Help functions
async def delete_msg(bot, chat_id, msg_id):
    try:
        await bot.delete_message(chat_id, msg_id)
    except Exception as e:
        logging.exception(e)
        pass


async def notify_admins(bot: Bot, text):
    for user_id in config.ADMINS:
        await bot.send_message(user_id, text)


def format_text(message: Message, user: Chat | User, title=None) -> str:
    if message is None:
        return ""

    html = ""

    user_id = user.id

    title = title if title is not None else ""

    def wrap_with_tag(tag, text, link=None):
        if link is not None:
            return f'<{tag} href="{link}">{text}</{tag}>'
        return f"<{tag}>{text}</{tag}>"

    def has_emojis(text):
        # Define a regular expression pattern to match emojis
        emoji_pattern = re.compile(
            "["
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F700-\U0001F77F"  # alchemical symbols
            "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
            "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
            "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
            "\U0001FA00-\U0001FA6F"  # Chess Symbols
            "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
            "\U00002702-\U000027B0"  # Dingbats
            "\U000024C2-\U0001F251"
            "]+"
        )

        # Use the findall method to search for all occurrences of the emoji pattern in the text
        emojis_found = re.findall(emoji_pattern, text)

        # Check if any emojis were found
        if emojis_found:
            return True, emojis_found
        else:
            return False, None

    current_offset = 0
    add_to_text = 0

    entities: [MessageEntity] = message.entities if message.entities else message.caption_entities
    message_text = message.text if message.text else message.caption

    for entity in entities:
        start = entity.offset - add_to_text
        length = entity.length
        has_emoji, emojis = has_emojis(message_text[:start])

        if has_emoji:
            add_to_text = len(emojis)
            start -= add_to_text
            print("")

        text = message_text[current_offset:start]

        html += text

        if entity.type == "bold":
            html += wrap_with_tag("b", message_text[start: start + length])
        elif entity.type == "italic":
            html += wrap_with_tag("i", message_text[start: start + length])
        elif entity.type == "underline":
            html += wrap_with_tag("u", message_text[start: start + length])
        elif entity.type == "strikethrough":
            html += wrap_with_tag("s", message_text[start: start + length])
        elif entity.type == "spoiler":
            html += wrap_with_tag("tg-spoiler", message_text[start: start + length])
        elif entity.type == "pre":
            html += wrap_with_tag("pre", message_text[start: start + length])
        elif entity.type == "url":
            html += message_text[start: start + length]
        elif entity.type == "text_link":
            link = entity.url
            if link is not None:
                html += wrap_with_tag("a", message_text[start: start + length], link)

        current_offset = start + length

    html += message_text[current_offset:]

    html_result = emoji.emojize(html)

    result = html_result.format(
        id=user_id, username=user.username, fname=user.first_name, lname=user.last_name,
        fullname=user.full_name, anyname=user.username if not (user.username == None) else user.full_name,
        ctitle=title)

    return result


async def get_state_set_id(state: FSMContext):
    data = await state.get_data()
    return data["setting_id"]


async def get_state_user_msg(state: FSMContext) -> UserMessage:
    data = await state.get_data()
    return data["user_msg"]


async def send_message(bot: Bot, send_to, message: UserMessage, title=None, next=None, *next_args):
    # if chat_id != 0:
    #     c = UserChannel.get_or_none(user_id=send_to, channel_id=chat_id)
    #     if c is not None:
    #         return

    async def send():
        sent_msg = await bot.send_message(
            send_to,
            result,
            reply_markup=start_kb,
            parse_mode="HTML",
            disable_web_page_preview=True
        ) if message_to_send.text is not None else await message_to_send.copy_to(
            send_to,
            result,
            reply_markup=start_kb,
            parse_mode="HTML"
        )

        if delete_time != '0':
            date = datetime.now() + timedelta(
                seconds=delete_time.second,
                minutes=delete_time.minute,
                hours=delete_time.hour
            )

            scheduler.add_job(
                delete_msg,
                trigger=DateTrigger(date),
                # trigger=DateTrigger(date, 'Europe/Kiev'),
                args=(bot, send_to, sent_msg.message_id),
                id=f"delete_msg_{send_to}_{sent_msg.message_id}"
            )

        if next is not None:
            await next(*next_args)

    try:
        if message.Message_json is None:
            await notify_admins(bot, "Стартовое сообщение не настроено" + str(message.Id))
            return

        if not message.On_Off:
            return

        schedule = "0"
        if message.Schedule != "0":
            try:
                schedule = datetime.strptime(message.Schedule, "%H:%M:%S")
            except ValueError:
                await notify_admins(
                    bot,
                    f"ID: {message.Id}. Неправильный формат даты рассылки сообщения: {message.Schedule}"
                )

        delete_time = "0"
        if message.Delete_time != "0":
            try:
                delete_time = datetime.strptime(message.Delete_time, "%H:%M:%S")
            except ValueError:
                await notify_admins(
                    bot,
                    f"ID: {message.Id}. Неправильный формат удаления сообщения: {message.Delete_time}"
                )

        start_kb = load_kb(message.Buttons) if message.Buttons else None

        user = await bot.get_chat(send_to)

        data = json.loads(message.Message_json)
        message_to_send = types.Message(**data)

        result = format_text(message_to_send, user, title)

        # User.update(step=User.step + 1).where(User.id == true_user_id).execute()
        # UserChannel.insert(user_id=true_user_id, channel_id=chat_id).execute()

        if schedule != "0":
            date = datetime.now() + timedelta(
                seconds=schedule.second,
                minutes=schedule.minute,
                hours=schedule.hour
            )
            scheduler.add_job(send, trigger=DateTrigger(date))

        else:
            await send()
    except Exception as e:
        logging.error(traceback.format_exc())


async def send_all_messages(bot: Bot, send_to, title=None, captcha=None, *captcha_args):
    settings_id = bot.id
    messages = await get_messages(settings_id)
    next = captcha
    args = captcha_args
    is_captcha_set = False
    for i in range(len(messages)).__reversed__():
        args = [bot, send_to, messages[i], title, next, *args]
        if not is_captcha_set:
            next = send_message
            is_captcha_set = True
        i += 1
    if next is not None:
        await next(*args)


async def add_to_messages(setting_id, message: UserMessage):
    setting: Setting = Setting.get_or_none(setting_id)
    messages = []
    user_messages = json.loads(setting.messages)

    if len(user_messages) == 0:
        message.Id = 1
        messages = [message]
    else:
        for user_message in user_messages:
            messages.append(UserMessage.from_dict(user_message))

        messages.append(message)
        message.Id = len(messages)

    message_dicts = [message.to_dict() for message in messages]
    setting.messages = json.dumps(message_dicts)
    setting.save()


async def save_message(setting_id, message: UserMessage):
    setting: Setting = Setting.get_or_none(setting_id)
    messages = []
    user_messages = json.loads(setting.messages)

    id = message.Id

    for user_message in user_messages:
        messages.append(UserMessage.from_dict(user_message))

    messages[id - 1] = message

    message_dicts = [message.to_dict() for message in messages]
    setting.messages = json.dumps(message_dicts)
    setting.save()


async def get_messages(setting_id):
    setting: Setting = Setting.get_or_none(setting_id)
    messages = []
    user_messages = json.loads(setting.messages)

    for user_message_dict in user_messages:
        user_message = UserMessage.from_dict(user_message_dict)
        messages.append(user_message)

    return messages


async def delete_user_message(setting_id, message_id):
    setting: Setting = Setting.get_or_none(setting_id)
    messages = []
    user_messages = json.loads(setting.messages)

    i = 1
    for user_message in user_messages:
        messages.append(UserMessage.from_dict(user_message))

    if message_id - 1 < len(messages):
        messages.pop(message_id - 1)

    for message in messages:
        message.Id = i
        i += 1

    message_dicts = [message.to_dict() for message in messages]
    setting.messages = json.dumps(message_dicts)
    setting.save()


async def show_messages(bot: Bot, send_to) -> int:
    user_messages: [UserMessage] = await get_messages(bot.id)

    for user_message in user_messages:
        message_id = user_message.Id
        message = json_to_tg_message(user_message.Message_json)
        kb = load_kb(user_message.Buttons)
        await bot.send_message(
            send_to,
            message.text + "\nID: " + str(message_id),
            reply_markup=kb,
            entities=message.entities
        ) if message.text is not None else await message.copy_to(
            send_to,
            caption=message.caption + "\nID: " + str(message_id),
            reply_markup=kb
        )
    return len(user_messages)


def json_to_tg_message(json_message) -> Message:
    data = json.loads(json_message)
    return types.Message(**data)


async def add_bot_to_db(bot: Bot):
    owner_id = ADMINS[0]
    owner = models.owners.Owner.get_or_none(owner_id)
    if owner is None:
        owner = models.owners.Owner.create(id=owner_id)

    bot_data = await bot.get_me()
    try:
        setting: Setting = Setting.create(id=bot.id, owner=owner, username=bot_data.username)
        setting.token = BOT_TOKEN
        setting.save()
    except:
        return


# endregion

# need to be rewritten
@register_message_handler()
async def apply_or_decline(message: Message):
    bot = message.bot
    user_id = message.from_user.id
    setting: Setting = Setting.get_or_none(id=bot.id)
    if not (user_id in users_verifying):
        return

    user_username = message.from_user.username

    current_loop = asyncio.get_running_loop()
    if message.text in json.loads(setting.captcha_buttons):
        try:
            current_loop.create_task(message.delete())
            current_loop.create_task(bot.delete_message(user_id, message.message_id - 1))  # state
        except Exception as e:
            print(e)

        users.get_or_create_user(user_id, user_username)
        if not setting.captcha_after:
            title = (await message.bot.get_chat(users_verifying[user_id])).title
            await send_all_messages(bot, user_id, title)
        try:
            del users_verifying[user_id]
        except:
            pass


def set_dispatcher(dispatcher_r: Dispatcher):
    dispatcher_r.middleware.setup(middlewares.UsersMiddleware())
    dispatcher_r.filters_factory.bind(filters.Admin)
    for item in bot_functions:
        item(dispatcher_r)


async def start_scheduler():
    scheduler.start()


async def start_polling():
    # dispatchers.append(dp)
    await add_bot_to_db(bots[0])
    tasks = [dispatcher_.start_polling() for dispatcher_ in dispatchers]
    # tasks.append(check_list(bots))
    tasks.append(start_scheduler())
    await asyncio.gather(*tasks)


# async def check_list(list: list):
#     count = len(list)
#     while True:
#         if len(list) > count:
#             count = len(list)
#             asyncio.ensure_future(set_bot(list[len(list) - 1]), loop=loop)
#         await asyncio.sleep(0.1)


# endregion

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    for dispatcher in dispatchers:
        set_dispatcher(dispatcher)
    loop.run_until_complete(start_polling())

# UserMessage Id must be static
