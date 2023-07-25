from datetime import datetime

from peewee import BooleanField, CharField, DateTimeField, IntegerField, Model, SqliteDatabase

database = SqliteDatabase("database.sqlite3")


class BaseModel(Model):
    class Meta:
        database = database


class Owner(BaseModel):
    id = IntegerField(primary_key=True)

    def __repr__(self) -> str:
        return f"<User {self.id}>"

    class Meta:
        table_name = "owners"

# class UserChannel(BaseModel):
#     user_id = IntegerField()
#     channel_id = IntegerField()

#     def __repr__(self) -> str:
#         return f"<UserChannel {self.user_id} {self.channel_id}>"

#     class Meta:
#         table_name = "users_channels"
