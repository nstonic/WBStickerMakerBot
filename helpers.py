from collections import Counter
from typing import Callable

from telebot.types import Message, CallbackQuery

from api.classes import Order
from db_client import check_user_registration



def join_orders(orders: list[Order]) -> str:
    """Собирает все артикулы из заказов и объединяет их в одно сообщение
    @type orders: список заказов, представленных как результаты парсинга
    запросов к API"""
    if orders:
        articles = [order.article for order in orders]
        joined_orders = '\n'.join(
            [f'{article} - {count}шт.'
             for article, count in Counter(sorted(articles)).items()])
    else:
        joined_orders = 'В данной поставе нет заказов'
    return joined_orders


def check_registration(registration_func: Callable):
    """Декоратор проверяет регистрацию пользователя, отправившего сообщение.
     Если пользователь не зарегистрирован, то запускает процесс регистрации.
     @type registration_func: Функция, которую следует вызвать, если пользователь
     не зарегистрирован. Она должна принимать в качестве аргумента Message"""

    def check_registration_decorator(func):
        def wrapper(*args, **kwargs):
            first_arg, *_ = args
            if isinstance(first_arg, Message):
                message = first_arg
            elif isinstance(first_arg, CallbackQuery):
                message = first_arg.message
            else:
                return

            if not check_user_registration(message.chat.id):
                registration_func(message)
            else:
                return func(*args, **kwargs)

        return wrapper

    return check_registration_decorator
