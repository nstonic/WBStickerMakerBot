import os

import api
import models


def prepare_db(owner_id: int, owner_full_name: str):
    """Создает базу данных. Регистрирует владельца как единственного администратора"""
    models.db.create_tables(
        [models.User, models.Supply, models.Order, models.SKU, models.Product]
    )

    models.User.update({'is_admin': False}). \
        where(models.User.is_admin, models.User.id != owner_id). \
        execute()

    models.User.insert(
        id=owner_id,
        full_name=owner_full_name,
        is_admin=True
    ).on_conflict_ignore().execute()


def check_user_registration(user_id: int) -> bool:
    """Проверяет зарегистрирован ли пользователь"""
    return models.User.get_or_none(models.User.id == user_id)


def create_user(user_id: int, user_full_name: str) -> models.BaseSQLLiteModel:
    """Регистрирует пользователя в базе"""
    return models.User.create(id=user_id, full_name=user_full_name)


def create_supply(supply: api.Supply):
    """Добавляет поставку в базу"""
    models.Supply.insert(
        id=supply.sup_id,
        name=supply.name,
        closed_at=supply.closed_at,
        create_at=supply.create_at,
        done=supply.done
    ).on_conflict_replace().execute()


def create_order(order: api.Order, supply_id: str):
    """Загружает в базу все заказы по данной поставке"""
    product = api.get_product(
        os.environ['WB_API_KEY'],
        article=order.article)
    models.Product.insert(
        article=order.article,
        name=product.name
    ).on_conflict_ignore().execute()

    models.Order.delete().where(models.Order.supply == supply_id)
    models.Order.insert(
        id=order.order_id,
        supply=supply_id,
        article=order.article,
        created_at=order.created_at
    ).on_conflict_replace().execute()

    for sku in order.skus:
        models.SKU.insert(
            text=sku,
            order=order.order_id
        ).on_conflict_ignore().execute()
