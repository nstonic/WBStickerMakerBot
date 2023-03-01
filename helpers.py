from collections import Counter
from typing import Callable

from telebot.types import Message, CallbackQuery, InlineKeyboardButton
from telebot.util import quick_markup

from api.classes import Order, Supply
from db_client import check_user_registration


def get_supplies_markup(supplies: list[Supply]):
    """Подготавливает кнопки поставок"""
    is_active = {0: 'Открыта', 1: 'Закрыта'}
    supplies_markup = quick_markup({
        f'{supply.name} | {supply.sup_id} | {is_active[supply.done]}': {'callback_data': f'supply_{supply.sup_id}'}
        for supply in supplies
    }, row_width=1)
    supplies_markup.add(
        InlineKeyboardButton(
            text='Показать больше поставок',
            callback_data=f'more_supplies'))
    return supplies_markup


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
        """
        @type func: Проверяемая функция должна первым аргументом принимать
        либо CallbackQuery, либо Message
        """
        def wrapper(*args, **kwargs):
            first_arg, *_ = args
            if isinstance(first_arg, Message):
                message = first_arg
            elif isinstance(first_arg, CallbackQuery):
                message = first_arg.message
            else:
                return

            if check_user_registration(message.chat.id):
                return func(*args, **kwargs)
            else:
                registration_func(message)

        return wrapper

    return check_registration_decorator
