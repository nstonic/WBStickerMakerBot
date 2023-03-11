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
    registered_at = DateTimeField(default=datetime.datetime.now)
    is_admin = BooleanField(default=False)
    is_active = BooleanField(default=True)

    class Meta:
        db_table = 'Users'


class SupplyModel(BaseDbModel):
    """Модель поставки"""
    id = CharField(primary_key=True, max_length=128)
    name = CharField(max_length=128)
    closed_at = DateTimeField(null=True)
    created_at = DateTimeField()
    is_done = BooleanField()

    class Meta:
        db_table = 'Supply'


class ProductModel(BaseDbModel):
    """Модель товара"""
    article = CharField(max_length=128, primary_key=True)
    barcode = CharField(max_length=32, null=True)
    name = TextField(null=True)

    class Meta:
        db_table = 'Products'


class OrderModel(BaseDbModel):
    """Модель заказа"""
    id = IntegerField(primary_key=True)
    supply = ForeignKeyField(SupplyModel, backref='orders', default=None, null=True)
    product = ForeignKeyField(ProductModel, backref='orders', on_delete='CASCADE')
    sticker = TextField(null=True)
    sticker_path = CharField(max_length=128)
    created_at = DateTimeField()

    class Meta:
        db_table = 'Orders'
