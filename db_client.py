import os

import pytz
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


def insert_user(user_id: int | str, user_full_name: str) -> UserModel:
    """Регистрирует пользователя в базе
    @param user_id: Telegram ID пользователя
    @param user_full_name: Полное имя пользователя
    @return: Объект пользователя из БД
    """
    return UserModel.insert(id=user_id, full_name=user_full_name).on_conflict_replace().execute()


def get_user(user_id: int | str) -> UserModel:
    """Достает пользователя из базы
    @param user_id: Telegram ID пользователя
    @return: Объект пользователя из БД
    """
    return UserModel.get_or_none(UserModel.id == user_id)


def get_all_users() -> ModelSelect:
    """Достает всех пользователей из базы
    @return: Объект пользователя из БД
    """
    return UserModel.select()


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
        SupplyModel.created_at,
        SupplyModel.is_done]
    with db.atomic():
        SupplyModel.insert_many(
            rows=supplies_rows,
            fields=supplies_fields
        ).on_conflict_ignore().execute()


def bulk_insert_orders(orders: list[Order], supply_id: str = None):
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
             order.created_at.astimezone(pytz.timezone('Europe/Samara')).strftime('%Y-%m-%d %H:%M:%S'),
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


def select_orders_by_supply(supply_id: str) -> ModelSelect:
    """
    Выгружает из БД все заказы по данной поставке
    @param supply_id: ID поставки
    @return: Результат запроса к БД
    """
    return OrderModel.select().where(OrderModel.supply_id == supply_id)


def get_order_by_id(order_id: int) -> OrderModel | None:
    """
    Выгружает из БД все заказы по данной поставке
    @param order_id: ID заказа
    @return: Результат запроса к БД
    """
    return OrderModel.get_or_none(OrderModel.id == order_id)


def check_user_registration(user_id: int, is_admin: bool = False) -> UserModel | None:
    """Проверяет зарегистрирован ли пользователь в БД
    @param user_id: Telegram ID пользователя
    @param is_admin: Если True, то возвращается пользователь, только если он администратор
    @return: Объект пользователя из БД, если пользователь найден, в противном случае None
    """
    if is_admin:
        return UserModel.get_or_none(UserModel.id == user_id, UserModel.is_admin == True)
    return UserModel.get_or_none(UserModel.id == user_id)


def delete_supply_from_db(supply_id: str):
    supply = SupplyModel.get_or_none(SupplyModel.id == supply_id)
    if supply:
        supply.delete_instance()
