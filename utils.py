import os
import shutil
from collections import Counter
from typing import Callable

from peewee import ModelSelect
from telebot.types import Message, CallbackQuery, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telebot.util import quick_markup

from api.classes import Order, Supply
from api.methods import get_product, get_stickers
from db_client import check_user_registration
from db_client import select_orders_by_supply
from db_client import add_stickers_to_db
from db_client import set_products_name_and_barcode
from models import OrderModel
from stickers import create_stickers


def make_menu_from_list(buttons_title: list, row_width: int = 2) -> ReplyKeyboardMarkup:
    """Создаёт нижнее меню из списка кнопок
    @param buttons_title: Тексты кнопок
    @param row_width: Максимальное количество кнопок в строке
    @return:
    """
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [KeyboardButton(button)
               for button in buttons_title]
    markup.add(*buttons, row_width=row_width)
    return markup


def create_supplies_markup(
        supplies: list[Supply],
        show_more_supplies: bool = True,
        show_create_new: bool = False,
        order_to_append: int | str = None
):
    """Подготавливает кнопки поставок
    @param supplies: список поставок, представленных как результаты парсинга
    @param order_to_append: если указано, то callback_data меняется
     на добавление заказа к поставке - 'append_o_to_s_{order_to_append}_{supply.supply_id}'.
     В противном случае в callback_data будет отправлен только id поставки - 'supply_{supply.supply_id}'
    @param show_create_new: добавляет кнопку "Показать больше поставок" в конце списка
    @param show_more_supplies: добавляет кнопку "Создать новую" в конце списка
    запросов к API
    """
    is_done = {0: 'Открыта', 1: 'Закрыта'}
    buttons = {}
    for supply in supplies:
        callback_data = f'append_o_to_s_{order_to_append}_{supply.supply_id}' \
            if order_to_append else f'supply_{supply.supply_id}'
        button_name = f'{supply.name} | {supply.supply_id} | {is_done[supply.is_done]}'
        buttons[button_name] = {'callback_data': callback_data}

    supplies_markup = quick_markup(buttons, row_width=1)
    if show_more_supplies:
        supplies_markup.add(
            InlineKeyboardButton(
                text='Показать больше поставок',
                callback_data=f'more_supplies'
            )
        )
    if show_create_new:
        supplies_markup.add(
            InlineKeyboardButton(
                text='Создать новую',
                callback_data=f'create_supply'
            )
        )
    return supplies_markup


def create_orders_markup(orders: list[Order]):
    """Подготавливает кнопки заказов
    @param orders: список заказов, представленных как результаты парсинга
    запросов к API
    """
    orders_markup = quick_markup({
        f'{order.article} | {order.created_at}': {
            'callback_data': f'order_{order.order_id}'
        }
        for order in orders
    }, row_width=1)
    return orders_markup


def join_orders(orders: list[Order]) -> str:
    """Собирает все артикулы из заказов и объединяет их в одно сообщение
    @param orders: список заказов, представленных как результаты парсинга
    запросов к API
    @return: Строка из объединенных артикулов заказов
    """

    articles = [order.article for order in orders]
    joined_orders = '\n'.join(
        [f'{article} - {count}шт.'
         for article, count in Counter(sorted(articles)).items()]
    )
    return joined_orders


def check_registration(registration_func: Callable):
    """Декоратор проверяет регистрацию пользователя, отправившего сообщение.
     Если пользователь не зарегистрирован, то запускает процесс регистрации.
     @param registration_func: Функция, которую следует вызвать, если пользователь
     не зарегистрирован. Она должна принимать в качестве аргумента Message"""

    def check_registration_decorator(func: Callable):

        def wrapper(*args, **kwargs):
            first_arg, *_ = args
            if isinstance(first_arg, Message):
                message = first_arg
            elif isinstance(first_arg, CallbackQuery):
                message = first_arg.message
            else:
                class CheckRegistrationError(Exception):
                    pass

                raise CheckRegistrationError(
                    f'Проверяемая функция {func.__name__}'
                    f' должна первым аргументом принимать либо CallbackQuery, либо Message.'
                    f' А не {type(first_arg)} = {first_arg}'
                )

            if check_user_registration(message.chat.id):
                return func(*args, **kwargs)
            else:
                registration_func(message)

        return wrapper

    return check_registration_decorator


def group_orders_by_article(orders: ModelSelect) -> dict[str:list[OrderModel]]:
    """
    Группирует заказы по артикулам
    @param orders: Выборка заказов из БД
    @return: словарь со сгруппированными заказами
            {
              Артикул1 : [Заказ1, Заказ2]
              и т.д.
            }
    """
    grouped_orders = {
        order.product.article: []
        for order in orders}
    for order in orders:
        grouped_orders[order.product.article].append(order)
    return grouped_orders


def add_stickers_and_products_to_orders(supply_id: str):
    """Добавляет в заказы данные по товарам и стикерам
    @param supply_id: ID поставки
    """
    orders = select_orders_by_supply(supply_id)
    articles = set([order.product.article for order in orders])
    products = [get_product(article) for article in articles]
    set_products_name_and_barcode(products)
    stickers = get_stickers([order.id for order in orders])
    add_stickers_to_db(stickers)


def prepare_stickers(supply_id: str) -> tuple[str, dict]:
    """Собирает информацию для стикеров.
    Подготавливает pdf, архивирует их и возвращает путь к zip архиву
    @param supply_id: ID поставки
    @return: адрес к файлу с архивом
    """
    orders = select_orders_by_supply(supply_id)
    grouped_orders = group_orders_by_article(orders)
    supply_path, stickers_report = create_stickers(grouped_orders, supply_id)
    shutil.make_archive(supply_path, 'zip', supply_path)
    return f'{supply_path}.zip', stickers_report


def delete_temp_sticker_files():
    """
    Удаляет папки и zip архивы с pdf стикерами
    """
    dir_content = os.listdir()
    for path in dir_content:
        if not path.endswith('.py'):
            if path.startswith('stickers'):
                shutil.rmtree(path, ignore_errors=True)
            if path.endswith('.zip'):
                os.remove(path)
