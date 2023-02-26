import json
from collections import Counter

from classes import Order


def join_orders(orders: list[Order]) -> str:
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



def get_admin_id() -> int:
    """Получает id администратора"""
    with open('users.json') as file:
        users = json.load(file)
    return int(next(filter(lambda user: user[1] == 'admin', users.items()))[0])



