import datetime

from peewee import SqliteDatabase
from peewee import Model
from peewee import IntegerField
from peewee import CharField, TextField
from peewee import DateTimeField
from peewee import BooleanField
from peewee import ForeignKeyField

db = SqliteDatabase('bot.db')


class BaseDbModel(Model):
    class Meta:
        database = db


class UserDbModel(BaseDbModel):
    id = IntegerField(primary_key=True)
    full_name = CharField(max_length=50)
    register_at = DateTimeField(default=datetime.datetime.now)
    is_admin = BooleanField(default=False)
    is_active = BooleanField(default=True)


class SupplyDbModel(BaseDbModel):
    id = CharField(primary_key=True, max_length=128)
    name = CharField(max_length=128)
    closed_at = DateTimeField(null=True)
    create_at = DateTimeField()
    done = BooleanField()


class ProductDbModel(BaseDbModel):
    article = CharField(max_length=128, primary_key=True)
    name = TextField(null=True)


class OrderDbModel(BaseDbModel):
    id = IntegerField(primary_key=True)
    supply = ForeignKeyField(SupplyDbModel, backref='orders', on_delete='CASCADE')
    product = ForeignKeyField(ProductDbModel, backref='orders', on_delete='CASCADE')
    sticker = TextField(null=True)
    created_at = DateTimeField()


class SKUDbModel(BaseDbModel):
    text = CharField(primary_key=True, max_length=128)
    order = ForeignKeyField(OrderDbModel, backref='skus', on_delete='CASCADE')
