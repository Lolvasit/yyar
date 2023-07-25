from aiogram.dispatcher.filters import BoundFilter
from aiogram.types import Message

from models.owners import Owner
from models.settings import Setting
from users import get_user


# Наверное нужно переписать, чтобы просто чекать является ли юзер овнером бота
class Admin(BoundFilter):
    key = "is_admin"

    def __init__(self, is_admin: bool):
        self.is_admin = is_admin

    async def check(self, message: Message):
        user = get_user(message.from_user.id)

        if not user:
            return False

        return user.is_admin == self.is_admin

    # async def check(self, message: Message):
    #     user = get_user(message.from_user.id)
    #
    #     bots: [Setting] = []
    #     if user.is_admin:
    #         owner = Owner.get_or_none(user.id)
    #
    #         if owner is not None:
    #             bots: [Setting] = Setting.select().where(Setting.owner_id == owner)
    #
    #     def check_bot():
    #         for bot in bots:
    #             if bot.id == message.bot.id:
    #                 return True
    #         return False
    #
    #     if not user or not check_bot():
    #         return False
    #
    #     return user.is_admin == self.is_admin
