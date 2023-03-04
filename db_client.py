import os

from peewee import ModelSelect

from api.classes import Supply, Order, Product, Sticker
from models import db, UserModel, SupplyModel, OrderModel, ProductModel


def prepare_db(owner_id: int, owner_full_name: str):
    """Создает БД. Регистрирует владельца как единственного администратора
    @param owner_id: Telegram ID владельца бота
    @param owner_full_name: Полное имя владельца бота
    """
    db.create_tables([UserModel, SupplyModel, OrderModel, ProductModel])
    UserModel.update({'is_admin': False}) \
        .where(UserModel.is_admin, UserModel.id != owner_id) \
        .execute()
    UserModel.insert(
        id=owner_id,
        full_name=owner_full_name,
        is_admin=True
    ).on_conflict_ignore().execute()


def insert_user(user_id: int, user_full_name: str) -> UserModel:
    """Регистрирует пользователя в базе
    @param user_id: Telegram ID пользователя
    @param user_full_name: Полное имя пользователя
    @return: Объект пользователя из БД
    """
    return UserModel.insert(id=user_id, full_name=user_full_name).on_conflict_replace().execute()


def bulk_insert_supplies(supplies: list[Supply]):
    """Добавляет поставки в базу
    @param supplies: список поставок, представленных как результаты парсинга
    запросов к API
    """
    supplies_rows = [supply.to_tuple() for supply in supplies]
    supplies_fields = [
        SupplyModel.id,
        SupplyModel.name,
        SupplyModel.closed_at,
        SupplyModel.create_at,
        SupplyModel.done]
    with db.atomic():
        SupplyModel.insert_many(
            rows=supplies_rows,
            fields=supplies_fields
        ).on_conflict_ignore().execute()


def bulk_insert_orders(orders: list[Order], supply_id: str):
    """Загружает в базу все заказы и продукты по данной поставке
    @param orders: список заказов, представленных как результаты парсинга
    запросов к API
    @param supply_id: ID поставки
    """
    OrderModel.delete().where(OrderModel.supply == supply_id)
    products_rows = [[order.article] for order in orders]
    with db.atomic():
        ProductModel.insert_many(
            rows=products_rows,
            fields=[ProductModel.article]
        ).on_conflict_ignore().execute()

    orders_data = []
    for order in orders:
        product = ProductModel.get(ProductModel.article == order.article)
        orders_data.append(
            [order.order_id,
             product,
             order.created_at,
             supply_id,
             os.path.join('stickers', f'{order.order_id}.png')])
    order_fields = [
        OrderModel.id,
        OrderModel.product,
        OrderModel.created_at,
        OrderModel.supply,
        OrderModel.sticker_path]
    with db.atomic():
        OrderModel.insert_many(rows=orders_data, fields=order_fields).on_conflict_replace().execute()


def set_products_name_and_barcode(products: list[Product]):
    """
    Добавляет к товарам в БД данные: наименование и штрихкод.
    Все товары должны быть уже созданы в БД
    @param products: список товаров, представленных как результаты парсинга
    запросов к API
    """
    for product in products:
        ProductModel.update(
            {ProductModel.name: product.name,
             ProductModel.barcode: product.barcode}
        ).where(ProductModel.article == product.article).execute()


def add_stickers_to_db(stickers: list[Sticker]):
    """Заполняет у заказов в БД поле со стикером
    @param stickers: список стикеров, представленных как результаты парсинга
    запросов к API
    """
    for sticker in stickers:
        OrderModel.update({OrderModel.sticker: sticker.file}). \
            where(OrderModel.id == sticker.order_id).execute()
