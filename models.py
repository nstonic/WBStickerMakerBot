import datetime

from peewee import (SqliteDatabase,
                    Model,
                    IntegerField,
                    CharField,
                    DateTimeField,
                    BooleanField)

db = SqliteDatabase('bot.db')


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    id = IntegerField(primary_key=True)
    full_name = CharField(max_length=50)
    register_at = DateTimeField(default=datetime.datetime.now)
    is_admin = BooleanField(default=False)
    is_active = BooleanField(default=True)
