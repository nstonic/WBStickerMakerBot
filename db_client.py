from peewee import ModelSelect

from api.classes import Supply, Order, Product, Sticker
from api.methods import get_product, get_stickers
from models import db, UserModel, SupplyModel, OrderModel, ProductModel


def prepare_db(owner_id: int, owner_full_name: str):
    """Создает базу данных. Регистрирует владельца как единственного администратора"""
    db.create_tables(
        [UserModel, SupplyModel, OrderModel, ProductModel]
    )

    UserModel.update({'is_admin': False}). \
        where(UserModel.is_admin, UserModel.id != owner_id). \
        execute()

    UserModel.insert(
        id=owner_id,
        full_name=owner_full_name,
        is_admin=True
    ).on_conflict_ignore().execute()


def check_user_registration(user_id: int) -> bool:
    """Проверяет зарегистрирован ли пользователь"""
    return UserModel.get_or_none(UserModel.id == user_id)


def insert_user(user_id: int, user_full_name: str) -> UserModel:
    """Регистрирует пользователя в базе"""
    return UserModel.insert(id=user_id, full_name=user_full_name).on_conflict_replace().execute()


def bulk_insert_supplies(supplies: list[Supply]):
    """Добавляет поставки в базу"""
    supplies_rows = [supply.to_tuple() for supply in supplies]
    supplies_fields = [SupplyModel.id, SupplyModel.name, SupplyModel.closed_at, SupplyModel.create_at, SupplyModel.done]
    with db.atomic():
        SupplyModel.insert_many(
            rows=supplies_rows,
            fields=supplies_fields
        ).on_conflict_ignore().execute()


def bulk_insert_orders(orders: list[Order], supply_id: str):
    """Загружает в базу все заказы и продукты по данной поставке"""
    OrderModel.delete().where(OrderModel.supply == supply_id)
    articles = [[order.article] for order in orders]
    with db.atomic():
        ProductModel.insert_many(
            rows=articles,
            fields=[ProductModel.article]
        ).on_conflict_ignore().execute()

    orders_data = []
    for order in orders:
        product = ProductModel.get(ProductModel.article == order.article)
        orders_data.append([order.order_id, product, order.created_at, supply_id])
    order_fields = [OrderModel.id, OrderModel.product, OrderModel.created_at, OrderModel.supply]
    with db.atomic():
        OrderModel.insert_many(rows=orders_data, fields=order_fields).on_conflict_replace().execute()


def select_orders_by_supply(supply_id: str) -> ModelSelect:
    return OrderModel.select().where(OrderModel.supply_id == supply_id)


def fetch_products(api_key: str, orders: ModelSelect) -> list[Product]:
    """Собирает данные по продуктам из поставки"""
    articles = set([order.product.article for order in orders])
    products = [get_product(api_key, article) for article in articles]
    for product in products:
        ProductModel.update(
            {ProductModel.name: product.name,
             ProductModel.barcode: product.barcode}
        ).where(ProductModel.article == product.article).execute()
    return products


def add_stickers_to_db(stickers: list[Sticker]):
    """Собирает стикеры заказов"""
    for sticker in stickers:
        OrderModel.update({OrderModel.sticker: sticker.file}). \
            where(OrderModel.id == sticker.order_id).execute()
