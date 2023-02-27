from collections import Counter

from requests import Response

import api
import db_client


def join_orders(orders: list[api.Order]) -> str:
    """Собирает все артикулы из заказов и объединяет их в одно сообщение"""
    if orders:
        articles = [order.article for order in orders]
        joined_orders = '\n'.join(
            [
                f'{article} - {count}шт.'
                for article, count in Counter(sorted(articles)).items()
            ]
        )
    else:
        joined_orders = 'В данной поставе нет заказов'
    return joined_orders


def fetch_supplies(
        response: Response,
        only_active: bool = True,
        number_of_supplies: int = 50) -> list[api.Supply]:
    """Собирает поставки в список и записывает их в БД"""

    supplies = []
    for supply in response.json()["supplies"][::-1]:
        if not supply['done'] or only_active is False:
            supply = api.Supply.parse_obj(supply)
            supplies.append(supply)
            db_client.insert_supply(supply)
        if len(supplies) == number_of_supplies:
            break
    return supplies

