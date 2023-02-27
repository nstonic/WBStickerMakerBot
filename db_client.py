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


def insert_user(user_id: int, user_full_name: str) -> models.BaseSQLLiteModel:
    """Регистрирует пользователя в базе"""
    return models.User.insert(id=user_id, full_name=user_full_name).on_conflict_replace().execute()


def insert_supply(supply: api.Supply):
    """Добавляет поставку в базу"""
    models.Supply.insert(
        id=supply.sup_id,
        name=supply.name,
        closed_at=supply.closed_at,
        create_at=supply.create_at,
        done=supply.done
    ).on_conflict_replace().execute()


def bulk_insert_orders(orders: list[api.Order], supply_id: str):
    """Загружает в базу все заказы и продукты по данной поставке"""
    models.Order.delete().where(models.Order.supply == supply_id)

    # products = (
    #     api.get_product(
    #         os.environ['WB_API_KEY'],
    #         article=order.article
    #     )
    #     for order in orders
    # )
    # product_fields = [models.Product.name, models.Product.article]
    # with models.db.atomic():
    #     models.Product.insert_many(rows=products, fields=product_fields).on_conflict_replace().execute()

    orders = [
        (order.order_id, supply_id, order.article, order.created_at)
        for order in orders
    ]
    order_fields = [models.Order.id, models.Order.supply, models.Order.article, models.Order.created_at]
    with models.db.atomic():
        models.Order.insert_many(rows=orders, fields=order_fields).on_conflict_replace().execute()
