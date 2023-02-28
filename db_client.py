from pprint import pprint

# from barcode import Code128
# from barcode.writer import ImageWriter
# from fpdf import FPDF
from peewee import ModelSelect

from api import Supply, Order, get_supplies_response, get_product, get_sticker_response, Sticker
from models import db, UserDbModel, SupplyDbModel, OrderDbModel, SKUDbModel, ProductDbModel


def prepare_db(owner_id: int, owner_full_name: str):
    """Создает базу данных. Регистрирует владельца как единственного администратора"""
    db.create_tables(
        [UserDbModel, SupplyDbModel, OrderDbModel, SKUDbModel, ProductDbModel]
    )

    UserDbModel.update({'is_admin': False}). \
        where(UserDbModel.is_admin, UserDbModel.id != owner_id). \
        execute()

    UserDbModel.insert(
        id=owner_id,
        full_name=owner_full_name,
        is_admin=True
    ).on_conflict_ignore().execute()


def check_user_registration(user_id: int) -> bool:
    """Проверяет зарегистрирован ли пользователь"""
    return UserDbModel.get_or_none(UserDbModel.id == user_id)


def insert_user(user_id: int, user_full_name: str) -> UserDbModel:
    """Регистрирует пользователя в базе"""
    return UserDbModel.insert(id=user_id, full_name=user_full_name).on_conflict_replace().execute()


def insert_supply(supply: Supply):
    """Добавляет поставку в базу"""
    SupplyDbModel.insert(
        id=supply.sup_id,
        name=supply.name,
        closed_at=supply.closed_at,
        create_at=supply.create_at,
        done=supply.done
    ).on_conflict_replace().execute()


def bulk_insert_orders(orders: list[Order], supply_id: str):
    """Загружает в базу все заказы и продукты по данной поставке"""
    OrderDbModel.delete().where(OrderDbModel.supply == supply_id)
    articles = [[order.article] for order in orders]
    with db.atomic():
        ProductDbModel.insert_many(
            rows=articles,
            fields=[ProductDbModel.article]
        ).on_conflict_ignore().execute()

    orders_data = []
    for order in orders:
        product = ProductDbModel.get(ProductDbModel.article == order.article)
        orders_data.append([order.order_id, product, order.created_at, supply_id])
    order_fields = [OrderDbModel.id, OrderDbModel.product, OrderDbModel.created_at, OrderDbModel.supply]
    with db.atomic():
        OrderDbModel.insert_many(rows=orders_data, fields=order_fields).on_conflict_replace().execute()


def fetch_supplies(
        api_key: str,
        only_active: bool = True,
        number_of_supplies: int = 50) -> list[Supply]:
    """Собирает поставки в список и записывает их в БД"""
    response = get_supplies_response(api_key)
    supplies = []
    for supply in response.json()["supplies"][::-1]:
        if not supply['done'] or only_active is False:
            supply = Supply.parse_obj(supply)
            supplies.append(supply)
            insert_supply(supply)
        if len(supplies) == number_of_supplies:
            break
    return supplies


def get_orders(supply_id: str) -> ModelSelect:
    return OrderDbModel.select().where(OrderDbModel.supply_id == supply_id)


def fetch_products(api_key: str, orders: ModelSelect):
    """Собирает данные по продуктам из поставки"""
    articles = set([order.product.article for order in orders])
    products = {article: get_product(api_key, article) for article in articles}
    for article, product_name in products.items():
        ProductDbModel.update({ProductDbModel.name: product_name}). \
            where(ProductDbModel.article == article).execute()


def fetch_stickers(api_key: str, orders: ModelSelect):
    stickers_response = get_sticker_response(api_key, list(orders))
    stickers = [Sticker.parse_obj(sticker) for sticker in stickers_response.json()['stickers']]
    for sticker in stickers:
        OrderDbModel.update({OrderDbModel.sticker: sticker.file}). \
            where(OrderDbModel.id == sticker.order_id).execute()

# def build_barcode_pdf(product: ProductDbModel):
#     with open("barcode.png", "wb") as file:
#         Code128(product.barcode, writer=ImageWriter()).write(file)
#     pdf = FPDF(format=(120, 75))
#     pdf.set_auto_page_break(auto=False, margin=0)
#     pdf.add_page()
#     pdf.image("barcode.png", y=3, x=33, w=55, h=33, type="png")
#     try:
#         pdf.add_font("Arial", fname='arial.ttf', uni=True)
#         pdf.set_font("Arial", size=10)
#     except:
#         input("Скопируйте arial.ttf в папку с программой.\nДля закрытия нажмите Enter")
#     pdf.ln(30)
#     pdf.multi_cell(w=0, h=5,
#                    txt=f"{product.name}\nАртикул: {product.article}\nСтрана: Россия\nБренд: CVT",
#                    align="L")
#
#     pdf.output(rf"barcodes\{product.article}.pdf")
