from peewee import CharField, Model, SqliteDatabase, IntegrityError, IntegerField, AutoField, TextField, BooleanField, \
    ForeignKeyField
from peewee_migrate import Router

from models.owners import Owner

database = SqliteDatabase("database.sqlite3")

router = Router(database)
router.run()


class BaseModel(Model):
    class Meta:
        database = database


class Setting(BaseModel):
    # Id is bot id
    id = AutoField(primary_key=True)
    token = TextField(default=None, null=True)
    owner = ForeignKeyField(Owner, backref="owners", null=True)
    username = TextField(default=None, null=True)

    # json формат листа с сообщениями для рассылки
    messages = TextField(default="[]", null=True)
    mails = TextField(default="[]", null=True)

    captcha_text = TextField(default="Are you human", null=True)
    captcha_buttons = TextField(default="[]", null=True)
    captcha_time = IntegerField(default=30, null=True)
    captcha_first_delay = IntegerField(default=30, null=True)
    captcha_is_on = BooleanField(default=False, null=True)
    captcha_after = BooleanField(default=False, null=True)

    # link = TextField(default="", null=True)
    def __repr__(self) -> str:
        return f"<Setting {self.id} {self.link}>"

    class Meta:
        table_name = "settings"

    # @classmethod
    # def get_many(cls, names, step=0):
    #     lst = cls.select(cls.value)
    #     lst = [cls.get_or_none(name=name,step=step) for name in names]
    #     return [item.value if item else None for item in lst]

    @classmethod
    def set_many(cls, kwargs, step=0):
        for name, value in kwargs.items():
            cls.update({cls.value: value}).where((cls.name == name) & (cls.step == step)).execute()
