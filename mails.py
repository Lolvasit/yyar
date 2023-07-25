import asyncio
import json
import logging
from datetime import datetime, timedelta

import aiogram
from aiogram import Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.triggers.date import DateTrigger

from main import format_text, delete_msg, load_kb, \
    json_to_tg_message, fast_count
from models.settings import Setting
from scheduler_manager import scheduler


class MailMessage:
    def __init__(self):
        self.Id: int = -1
        self.ShId: str = ""
        self.Message_json: str = ""
        self.Delete_time = "0"
        self.Buttons: str = ""
        self.Schedule = "0"

    def to_dict(self):
        return {
            'Id': self.Id,
            "ShId": self.ShId,
            'Message_json': self.Message_json,
            'Start_delete_time': self.Delete_time,
            'Buttons': self.Buttons,
            'Schedule': self.Schedule
        }

    @classmethod
    def from_dict(cls, data):
        message = cls()
        message.Id = data.get('Id')
        message.ShId = data.get('ShId')
        message.Message_json = data.get('Message_json')
        message.Buttons = data.get('Buttons')
        message.On_Off = data.get('On_Off', True)
        message.Schedule = data.get('Schedule', "0")
        return message


def get_mail_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("Добавить рассылку ", callback_data="add_mail"))
    kb.add(InlineKeyboardButton("Удалить рассылку", callback_data="delete_mail"))
    return kb


def get_mail_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("Изменить клавиатуру ⌨️", callback_data="change_kb"))
    kb.add(InlineKeyboardButton("Добавить дату отправки 📅", callback_data="add_send_date"))
    kb.add(InlineKeyboardButton("Добавить время удаления ⏱", callback_data="add_delete_time"))
    kb.add(InlineKeyboardButton("Отменить рассылку ❌", callback_data="cancel_mail"))
    kb.add(InlineKeyboardButton("Подтвердить рассылку ✅", callback_data="confirm_mail"))
    return kb


def chunks(lst, n):
    """
# Yield successive n-sized chunks from lst.
"""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


async def send_mail(bot, user_id: int, from_chat: int, message: Message, kb, time) -> bool:
    try:

        user = await bot.get_chat(user_id)
        result = format_text(message, user)

        sent_msg = await bot.send_message(
            user_id,
            result,
            reply_markup=kb,
            parse_mode="HTML",
            disable_web_page_preview=True
        ) if message.text is not None else await message.copy_to(
            user_id,
            caption=result,
            reply_markup=kb,
            parse_mode="HTML"
        )
    except aiogram.exceptions.RetryAfter as e:
        await asyncio.sleep(e.timeout)
        return await send_mail(bot, user_id, from_chat, message, kb, time)
    except Exception as e:
        logging.exception(e)
        fast_count["bad"] += 1
    else:
        if time is not None:
            date = datetime.now() + timedelta(seconds=time.second, minutes=time.minute,
                                              hours=time.hour)
            scheduler.add_job(delete_msg, trigger=DateTrigger(date), args=(bot, user_id, sent_msg.message_id),
                              id=f"delete_msg_{user_id}_{message.message_id}")
        fast_count["good"] += 1
    fast_count["count"] += 1


async def make_mail(user_ids, fast, from_user, message: Message, kb, time, has_limit, max_amount, msg, call,
                    all_amount, sh_id=None):
    bot = call.bot

    count = 0
    good = 0
    bad = 0
    mail_thread_on = True
    if fast:
        for users in chunks(user_ids, 25):
            if not mail_thread_on:
                break
            for user in users:
                asyncio.create_task(send_mail(bot, user.id, from_user, message, kb, time))
            await asyncio.sleep(1)
            try:
                await msg.edit_text(
                    f"Отправлено: {fast_count['count']}, успешно: {fast_count['good']}, неудачно: {fast_count['bad']}")
            except:
                pass
            if has_limit and fast_count["good"] >= max_amount:
                break

        if sh_id is not None:
            await delete__mail(bot.id, sh_id)
        await call.message.answer(
            f"Результаты рассылки\nОтправлено: {fast_count['count']}, успешно: {fast_count['good']}, "
            f"неудачно: {fast_count['bad']}")
        fast_count["count"] = 0
        fast_count['good'] = 0
        fast_count['bad'] = 0
    # ====
    else:
        for user_id in user_ids:
            if not mail_thread_on:
                break
            if count % 50 == 0:
                await msg.edit_text(f"Отправлено: {count}, удачно {good}, всего надо {all_amount}")
            try:
                user = await bot.get_chat(user_id)

                result = format_text(message, user)

                sent_msg = await bot.send_message(
                    user_id,
                    result,
                    reply_markup=kb,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                ) if message.text is not None else await message.copy_to(
                    user_id,
                    caption=result,
                    reply_markup=kb,
                    parse_mode="HTML"
                )
                if time is not None:
                    date = datetime.now() + timedelta(seconds=time.second, minutes=time.minute,
                                                      hours=time.hour)
                    scheduler.add_job(delete_msg, trigger=DateTrigger(date, 'Europe/Kiev'), args=(bot, user_id, sent_msg.message_id),
                                      id=f"delete_msg_{user_id}_{message.message_id}")
                good += 1
            except Exception as e:
                logging.error(f"Error: {str(e)}")
                bad += 1
            count += 1
            if has_limit and good >= max_amount:
                break
            await asyncio.sleep(0.05)

        if sh_id is not None:
            await delete__mail(bot.id, sh_id)
        await msg.edit_text(f"Всего: {count}\nУдачно: {good}\nНе пришло: {bad}")


async def add_to_mails(setting_id, message: MailMessage):
    setting: Setting = Setting.get_or_none(setting_id)
    messages = []
    user_messages = json.loads(setting.mails)

    if len(user_messages) == 0:
        message.Id = 1
        messages = [message]
    else:
        for user_message in user_messages:
            messages.append(MailMessage.from_dict(user_message))

        messages.append(message)
        message.Id = len(messages)

    message_dicts = [message.to_dict() for message in messages]
    setting.mails = json.dumps(message_dicts)
    setting.save()


async def save_mail(setting_id, message: MailMessage):
    setting: Setting = Setting.get_or_none(setting_id)
    messages = []
    user_messages = json.loads(setting.mails)

    id = message.Id

    for user_message in user_messages:
        messages.append(MailMessage.from_dict(user_message))

    messages[id - 1] = message

    message_dicts = [message.to_dict() for message in messages]
    setting.mails = json.dumps(message_dicts)
    setting.save()


async def get_mails(setting_id):
    setting: Setting = Setting.get_or_none(setting_id)
    messages = []
    user_messages = json.loads(setting.mails)

    for user_message_dict in user_messages:
        user_message = MailMessage.from_dict(user_message_dict)
        messages.append(user_message)

    return messages


async def delete__mail(setting_id, sh_id):
    mails = await get_mails(setting_id)
    message_id = -1

    for mail in mails:
        if sh_id == mail.ShId:
            message_id = mail.Id

    setting: Setting = Setting.get_or_none(setting_id)
    messages = await get_mails(setting_id)

    i = 1

    if message_id - 1 < len(messages):
        messages.pop(message_id - 1)

    for message in messages:
        message.Id = i
        i += 1

    message_dicts = [message.to_dict() for message in messages]
    setting.mails = json.dumps(message_dicts)

    setting.save()


async def delete_user_mail(setting_id, message_id):
    setting: Setting = Setting.get_or_none(setting_id)
    messages = []
    user_messages = json.loads(setting.mails)

    i = 1
    for user_message in user_messages:
        messages.append(MailMessage.from_dict(user_message))

    if message_id - 1 < len(messages):
        item = messages.pop(message_id - 1)
        try:
            job = scheduler.get_job(item.ShId, "default")
            job.remove()
        except Exception as e:
            logging.exception(e)

    for message in messages:
        message.Id = i
        i += 1

    message_dicts = [message.to_dict() for message in messages]
    setting.mails = json.dumps(message_dicts)

    setting.save()


async def show_mails(bot: Bot, send_to) -> int:
    user_messages: [MailMessage] = await get_mails(bot.id)

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
