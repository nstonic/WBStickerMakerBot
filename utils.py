import os
import shutil
from collections import Counter
from typing import Callable

from peewee import ModelSelect
from telebot.types import Message, CallbackQuery, InlineKeyboardButton
from telebot.util import quick_markup

from api.classes import Order, Supply, Product
from api.methods import get_product, get_stickers
from db_client import check_user_registration
from db_client import set_products_name_and_barcode
from db_client import select_orders_by_supply
from db_client import add_stickers_to_db
from models import OrderModel
from stickers import create_pdf


def get_supplies_markup(supplies: list[Supply]):
    """Подготавливает кнопки поставок
    @param supplies: список поставок, представленных как результаты парсинга
    запросов к API
    """
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
    @param orders: список заказов, представленных как результаты парсинга
    запросов к API
    @return: Строка из объединенных артикулов заказов
    """

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
     @param registration_func: Функция, которую следует вызвать, если пользователь
     не зарегистрирован. Она должна принимать в качестве аргумента Message"""

    def check_registration_decorator(func: Callable):
        """
        @param func: Проверяемая функция должна первым аргументом принимать
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


def fetch_products(orders: ModelSelect) -> list[Product]:
    """Собирает данные по продуктам из поставки
    @param orders: Заказы полученные из базы
    @return: список продуктов, представленных как результаты парсинга
    запросов к API
    @raise: HttpError, WBAPIError
    """
    articles = set([order.product.article for order in orders])
    products = [get_product(article) for article in articles]
    set_products_name_and_barcode(products)
    return products


def group_orders_by_article(orders: ModelSelect) -> dict[str:list[OrderModel]]:
    """
    Группирует заказы по артикулам
    @param orders: Выборка заказов из БД
    @return: словарь со сгруппированными заказами
    """
    grouped_orders = {
        order.product.article: []
        for order in orders}
    for order in orders:
        grouped_orders[order.product.article].append(order)
    return grouped_orders


def prepare_stickers(supply_id: str) -> tuple[str, dict]:
    """Собирает информацию по для стикеров.
    Подготавливает pdf, архивирует их и возвращает путь к zip архиву
    @param supply_id: ID поставки
    @return: адрес к файлу с архивом
    """
    orders = select_orders_by_supply(supply_id)
    fetch_products(orders)
    stickers = get_stickers(orders)
    add_stickers_to_db(stickers)

    orders = select_orders_by_supply(supply_id)
    grouped_orders = group_orders_by_article(orders)
    supply_path, stickers_report = create_pdf(grouped_orders, supply_id)
    shutil.make_archive(supply_path, 'zip', supply_path)
    return f'{supply_path}.zip', stickers_report


def delete_tempfiles():
    """
    Удаляет папки и zip архивы с pdf стикерами
    """
    dir_content = os.listdir()
    for path in dir_content:
        if not path.endswith('.py'):
            if path.startswith('Stickers'):
                shutil.rmtree(path, ignore_errors=True)
            if path.endswith('.zip'):
                os.remove(path)
