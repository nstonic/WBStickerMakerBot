from peewee import ModelSelect

from .classes import Product, Order, Supply, Sticker
from .requests import get_supplies_response, get_orders_response, get_product_response, get_sticker_response


def get_orders(supply_id: str, api_key: str) -> list[Order]:
    response = get_orders_response(
        api_key=api_key,
        supply_id=supply_id)
    return [Order.parse_obj(order) for order in response.json()['orders']]


def get_product(api_key: str, article: str) -> Product:
    response = get_product_response(api_key, article)
    wanted_product_card = {}
    for product_card in response.json()["data"]:
        if product_card["vendorCode"] == article:
            wanted_product_card = product_card
            break
    return Product(wanted_product_card)


def get_supplies(api_key: str,
                 only_active: bool = True,
                 number_of_supplies: int = 50) -> list[Supply]:
    response = get_supplies_response(api_key)
    supplies = []
    for supply in response.json()["supplies"][::-1]:
        if not supply['done'] or only_active is False:
            supply = Supply.parse_obj(supply)
            supplies.append(supply)
        if len(supplies) == number_of_supplies:
            break
    return supplies


def get_stickers(api_key: str, orders: ModelSelect):
    stickers_response = get_sticker_response(api_key, list(orders))
    return [Sticker.parse_obj(sticker) for sticker in stickers_response.json()['stickers']]
