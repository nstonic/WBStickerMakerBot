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
    """Базовая модель для БД"""
    class Meta:
        database = db


class UserModel(BaseDbModel):
    """Модель пользователя"""
    id = IntegerField(primary_key=True)
    full_name = CharField(max_length=200)
    register_at = DateTimeField(default=datetime.datetime.now)
    is_admin = BooleanField(default=False)
    is_active = BooleanField(default=True)


class SupplyModel(BaseDbModel):
    """Модель поставки"""
    id = CharField(primary_key=True, max_length=128)
    name = CharField(max_length=128)
    closed_at = DateTimeField(null=True)
    create_at = DateTimeField()
    done = BooleanField()


class ProductModel(BaseDbModel):
    """Модель товара"""
    article = CharField(max_length=128, primary_key=True)
    barcode = CharField(max_length=32, null=True)
    name = TextField(null=True)


class OrderModel(BaseDbModel):
    """Модель заказа"""
    id = IntegerField(primary_key=True)
    supply = ForeignKeyField(SupplyModel, backref='orders', on_delete='CASCADE')
    product = ForeignKeyField(ProductModel, backref='orders', on_delete='CASCADE')
    sticker = TextField(null=True)
    created_at = DateTimeField()
