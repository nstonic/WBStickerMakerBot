import os

import telebot
from dotenv import load_dotenv
from telebot.types import Message, CallbackQuery
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from api.methods import get_orders, get_supplies, get_stickers
from helpers import join_orders, check_registration
from db_client import bulk_insert_orders, insert_user, prepare_db, select_orders_by_supply, \
    bulk_insert_supplies, fetch_products, add_stickers_to_db
from stickers import create_barcode_pdf, create_stickers

load_dotenv()
bot = telebot.TeleBot(os.environ['TG_BOT_TOKEN'], parse_mode=None)
WB_API_KEY = os.environ['WB_API_KEY']


def ask_for_registration(message):
    """Отправляет запрос на регистрацию пользователя администратору"""
    user_id = message.chat.id
    register_markup = InlineKeyboardMarkup(row_width=2)

    register_markup.add(
        InlineKeyboardButton(
            text='Одобрить',
            callback_data=f'register_{user_id}'),
        InlineKeyboardButton(
            text='Отказать',
            callback_data=f'deny_{user_id}'))
    bot.send_message(
        chat_id=os.environ['OWNER_ID'],
        text=f'Запрос на регистрацию пользователя\n{message.from_user.full_name}',
        reply_markup=register_markup)
    bot.send_message(
        chat_id=user_id,
        text='Запрос на регистрацию отправлен администратору. Ожидайте ответа.')


@bot.message_handler(commands=['start'])
@check_registration(ask_for_registration)
def start(message: Message):
    bot.delete_message(message.chat.id, message.id)
    supplies_markup = InlineKeyboardMarkup()
    supplies_markup.add(
        InlineKeyboardButton(
            text='Показать поставки',
            callback_data='show_supplies'))
    bot.send_message(
        message.chat.id,
        text='Привет',
        reply_markup=supplies_markup)


@bot.callback_query_handler(func=lambda call: call.data == 'show_supplies')
@check_registration(ask_for_registration)
def show_active_supplies(call: CallbackQuery):
    """
    Отображает текущие незакрытые поставки
    """
    if active_supplies := get_supplies(WB_API_KEY):
        bot.answer_callback_query(call.id, 'Поставки загружены')
    else:
        bot.answer_callback_query(call.id, 'Нет активных поставок')
        return

    supplies_markup = InlineKeyboardMarkup()
    for supply in active_supplies:
        if not supply.done:
            supplies_markup.add(
                InlineKeyboardButton(
                    text=f'{supply.name} | {supply.sup_id})',
                    callback_data=f'supply_{supply.sup_id}'))
    supplies_markup.add(
        InlineKeyboardButton(
            text='Показать больше поставок',
            callback_data=f'more_supplies'))
    bot.send_message(
        chat_id=call.message.chat.id,
        text='Текущие незакрытые поставки',
        reply_markup=supplies_markup)

    bulk_insert_supplies(active_supplies)


@bot.callback_query_handler(func=lambda call: call.data.startswith('supply_'))
@check_registration(ask_for_registration)
def handle_orders(call: CallbackQuery):
    """
    Обработчик заказов.
    Запрашивает заказы по данной поставке, отправляет их одним сообщением клиенту,
    после чего загружает в базу данных
    """

    supply_id = call.data.lstrip('supply_')
    orders = get_orders(
        api_key=WB_API_KEY,
        supply_id=supply_id)

    order_markup = InlineKeyboardMarkup()
    order_markup.add(
        InlineKeyboardButton(
            text='Создать стикеры',
            callback_data=f'stickers_for_supply_{supply_id}'))
    bot.send_message(
        chat_id=call.message.chat.id,
        text=f'Заказы по поставке {supply_id}:\n\n{join_orders(orders)}',
        reply_markup=order_markup)

    bulk_insert_orders(orders, supply_id)
    bot.answer_callback_query(call.id, 'Заказы загружены')


@bot.callback_query_handler(func=lambda call: call.data.startswith('more_supplies'))
@check_registration(ask_for_registration)
def get_supplies_number(call: CallbackQuery):
    """
    Запрашивает количество требуемых поставок
    """

    bot.clear_reply_handlers(call.message)
    bot.register_next_step_handler(
        call.message,
        show_number_of_supplies,
        call=call
    )
    bot.send_message(
        chat_id=call.message.chat.id,
        text='Сколько последних поставок вы хотите посмотреть? (максимум 50)'
    )


@check_registration(ask_for_registration)
def show_number_of_supplies(message: Message, call: CallbackQuery):
    """
    Отображает требуемое число последних поставок
    """
    try:
        number_of_supplies = int(message.text)
    except ValueError:
        bot.clear_reply_handlers(call.message)
        bot.register_next_step_handler(
            call.message,
            show_number_of_supplies,
            call=call)
        bot.send_message(
            chat_id=call.message.chat.id,
            text='Не понял Вас. Введите ещё раз')
        return

    bot.answer_callback_query(call.id, 'Идёт загрузка. Подождите')
    supplies = get_supplies(
        api_key=WB_API_KEY,
        only_active=False,
        number_of_supplies=number_of_supplies)
    is_active = {0: 'Открыта', 1: 'Закрыта'}
    supplies_markup = InlineKeyboardMarkup()
    for supply in sorted(supplies, key=lambda supply: supply.create_at):
        supplies_markup.add(
            InlineKeyboardButton(
                text=f'{supply.name} | {supply.sup_id} | {is_active[supply.done]}',
                callback_data=f'supply_{supply.sup_id}'))

    supplies_markup.add(
        InlineKeyboardButton(
            text='Показать больше поставок',
            callback_data=f'more_supplies'))
    bot.send_message(
        chat_id=call.message.chat.id,
        text='Текущие незакрытые поставки',
        reply_markup=supplies_markup)

    bulk_insert_supplies(supplies)


@bot.callback_query_handler(func=lambda call: call.data.startswith('register_'))
@check_registration(ask_for_registration)
def register_user(call: CallbackQuery):
    """
    Регистрирует пользователя
    """
    user_id = int(call.data.lstrip('register_'))
    insert_user(
        user_id=user_id,
        user_full_name=call.from_user.full_name
    )
    bot.answer_callback_query(
        call.id,
        text='Пользователь зарегистрирован'
    )
    bot.send_message(
        user_id,
        text='Ваша регистрация одобрена. Можно начать работать.\n/start'
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('deny_'))
@check_registration(ask_for_registration)
def deny_registration(call: CallbackQuery):
    """
    Отклоняет запрос регистрации
    """
    user_id = call.data.lstrip('deny_')
    bot.answer_callback_query(
        call.id,
        text='Регистрация отклонена'
    )
    bot.send_message(
        int(user_id),
        text='Ваш запрос на регистрацию отклонен'
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('stickers_for_supply_'))
@check_registration(ask_for_registration)
def send_stickers(call: CallbackQuery):
    supply_id = call.data.lstrip('stickers_for_supply_')
    bot.answer_callback_query(call.id, 'Запущена подготовка стикеров. Подождите')

    orders = select_orders_by_supply(supply_id)
    products = fetch_products(WB_API_KEY, orders)
    stickers = get_stickers(WB_API_KEY, orders)
    add_stickers_to_db(stickers)

    bot.send_message(call.message.chat.id, f'Данные успешно загружены. Ваши стикеры скоро будут готовы. Ожидайте')

    create_barcode_pdf(products)
    sticker_file_name = create_stickers(orders, supply_id)
    with open(sticker_file_name, 'rb') as file:
        bot.send_message(call.message.chat.id, f'Стикеры по поставке {supply_id}')
        bot.send_document(call.message.chat.id, file)


def main():
    os.makedirs("barcodes", exist_ok=True)
    try:
        owner_id = int(os.environ['OWNER_ID'])
    except ValueError:
        print('OWNER_ID должен быть целым числом')
        return
    prepare_db(
        owner_id=owner_id,
        owner_full_name=os.environ['OWNER_FULL_NAME'])
    bot.infinity_polling()


if __name__ == '__main__':
    main()
