from collections import Counter

from api import Order
from db_client import get_orders, fetch_products, fetch_stickers


def join_orders(orders: list[Order]) -> str:
    """Собирает все артикулы из заказов и объединяет их в одно сообщение"""
    if orders:
        articles = [order.article for order in orders]
        joined_orders = '\n'.join(
            [f'{article} - {count}шт.'
             for article, count in Counter(sorted(articles)).items()])
    else:
        joined_orders = 'В данной поставе нет заказов'
    return joined_orders


def fetch_data_for_stickers(supply_id: str, wb_api_key: str):
    orders = get_orders(supply_id)
    fetch_products(wb_api_key, orders)
    fetch_stickers(wb_api_key, orders)
