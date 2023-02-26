import datetime

from peewee import SqliteDatabase
from peewee import Model
from peewee import IntegerField
from peewee import CharField, TextField
from peewee import DateTimeField
from peewee import BooleanField
from peewee import ForeignKeyField

db = SqliteDatabase('bot.db')


class BaseSQLLiteModel(Model):
    class Meta:
        database = db


class User(BaseSQLLiteModel):
    id = IntegerField(primary_key=True)
    full_name = CharField(max_length=50)
    register_at = DateTimeField(default=datetime.datetime.now)
    is_admin = BooleanField(default=False)
    is_active = BooleanField(default=True)


class Supply(BaseSQLLiteModel):
    id = CharField(primary_key=True, max_length=128)
    name = CharField(max_length=128)
    closed_at = DateTimeField(null=True)
    create_at = DateTimeField()
    done = BooleanField()


class Product(BaseSQLLiteModel):
    article = CharField(max_length=128, primary_key=True)
    name = TextField()


class Order(BaseSQLLiteModel):
    id = IntegerField(primary_key=True)
    supply = ForeignKeyField(Supply, backref='orders', on_delete='CASCADE')
    article = ForeignKeyField(Product, backref='orders', on_delete='SET NULL', null=True)
    created_at = DateTimeField()


class SKU(BaseSQLLiteModel):
    text = CharField(primary_key=True, max_length=128)
    order = ForeignKeyField(Order, backref='skus', on_delete='CASCADE')
