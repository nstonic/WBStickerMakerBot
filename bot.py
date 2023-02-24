import json
import os

import telebot
from dotenv import load_dotenv
from telebot.types import (Message,
                           InlineKeyboardMarkup,
                           InlineKeyboardButton,
                           CallbackQuery)

from api import get_supplies_response, get_orders_response
from classes import Supply, Order
from helpers import join_orders, get_admin_id, get_user_role

load_dotenv()
bot = telebot.TeleBot(os.environ['TG_BOT_TOKEN'], parse_mode=None)


def check_registration(func):
    """Декоратор проверяет регистрацию пользователя, отправившего сообщение.
     Если пользователь не зарегистрирован, то запускает процесс регистрации"""

    def wrapper(*args, **kwargs):
        if isinstance(args[0], Message):
            message = args[0]
        elif isinstance(args[0], CallbackQuery):
            message = args[0].message
        else:
            return

        if not get_user_role(message.chat.id):
            ask_for_registration(message)
        else:
            return func(*args, **kwargs)

    return wrapper


def ask_for_registration(message):
    """Отправляет запрос на регистрацию администратору"""
    user_id = message.chat.id
    register_markup = InlineKeyboardMarkup(row_width=2)
    register_markup.add(
        InlineKeyboardButton(
            text='Одобрить',
            callback_data=f'register_{user_id}'
        ),
        InlineKeyboardButton(
            text='Отказать',
            callback_data=f'deny_{user_id}'
        )
    )
    bot.send_message(
        chat_id=get_admin_id(),
        text=f'Запрос на регистрацию пользователя\n{message.from_user.full_name}',
        reply_markup=register_markup
    )
    bot.send_message(
        chat_id=user_id,
        text='Запрос на регистрацию отправлен администратору. Ожидайте ответа.'
    )


@bot.message_handler(commands=['start'])
@check_registration
def start(message: Message):
    supplies_markup = InlineKeyboardMarkup()
    supplies_markup.add(
        InlineKeyboardButton(
            text='Показать поставки',
            callback_data='show_supplies'
        )
    )
    bot.send_message(
        message.chat.id,
        text='Привет',
        reply_markup=supplies_markup
    )


@bot.callback_query_handler(func=lambda call: call.data == 'show_supplies')
@check_registration
def show_active_supplies(call: CallbackQuery):
    """
    Отображает текущие незакрытые поставки
    """
    if response := get_supplies_response(os.environ['WB_API_KEY']):
        supplies = [
            Supply.parse_obj(supply)
            for supply in response.json()["supplies"]
        ]
        bot.answer_callback_query(call.id, 'Поставки загружены')
    else:
        bot.answer_callback_query(call.id, 'Сервер недоступен. Попробуйте позже')
        return

    supplies_markup = InlineKeyboardMarkup()
    for supply in supplies:
        if not supply.done:
            supplies_markup.add(
                InlineKeyboardButton(
                    text=f'{supply.name} | {supply.sup_id})',
                    callback_data=f'supply_{supply.sup_id}'
                )
            )
    supplies_markup.add(
        InlineKeyboardButton(
            text='Показать больше поставок',
            callback_data=f'more_supplies'
        )
    )

    bot.send_message(
        chat_id=call.message.chat.id,
        text='Текущие незакрытые поставки',
        reply_markup=supplies_markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('supply_'))
@check_registration
def show_orders(call: CallbackQuery):
    """
    Отображает заказы из текущей поставки
    """

    supply_id = call.data.lstrip('supply_')
    response = get_orders_response(
        api_key=os.environ['WB_API_KEY'],
        supply_id=supply_id
    )
    bot.answer_callback_query(call.id, 'Заказы')

    orders = [
        Order.parse_obj(order)
        for order in response.json()['orders']
    ]
    order_markup = InlineKeyboardMarkup()
    order_markup.add(
        InlineKeyboardButton(
            text='Создать стикеры',
            callback_data=f'stickers_for_supply_{supply_id}'
        )
    )
    bot.send_message(
        chat_id=call.message.chat.id,
        text=f'Заказы по поставке {supply_id}:\n\n{join_orders(orders)}',
        reply_markup=order_markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('more_supplies'))
@check_registration
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


@check_registration
def show_number_of_supplies(message: Message, call: CallbackQuery):
    """
    Отображает требуемое число последних поставок
    """
    if response := get_supplies_response(os.environ['WB_API_KEY']):
        supplies = sorted(
            [
                Supply.parse_obj(supply)
                for supply in response.json()["supplies"]
            ],
            key=lambda supply: supply.create_at
        )[::-1]
    else:
        try:
            bot.answer_callback_query(call.id, 'Сервер недоступен. Попробуйте позже')
        except telebot.apihelper.ApiTelegramException:
            pass
        return

    try:
        supplies_subset = supplies[:int(message.text)][::-1]
    except ValueError:
        bot.clear_reply_handlers(call.message)
        bot.register_next_step_handler(
            call.message,
            show_number_of_supplies,
            call=call
        )
        bot.send_message(
            chat_id=call.message.chat.id,
            text='Не понял Вас. Введите ещё раз'
        )
        return

    is_active = {0: 'Открыта', 1: 'Закрыта'}
    supplies_markup = InlineKeyboardMarkup()
    for supply in supplies_subset[:50]:
        supplies_markup.add(
            InlineKeyboardButton(
                text=f'{supply.name} | {supply.sup_id} | {is_active[supply.done]}',
                callback_data=f'supply_{supply.sup_id}'
            )
        )

    try:
        bot.answer_callback_query(call.id, f'Загружено {len(supplies_markup.keyboard)} поставок')
    except telebot.apihelper.ApiTelegramException:
        pass

    supplies_markup.add(
        InlineKeyboardButton(
            text='Показать больше поставок',
            callback_data=f'more_supplies'
        )
    )
    bot.send_message(
        chat_id=call.message.chat.id,
        text='Текущие незакрытые поставки',
        reply_markup=supplies_markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('register_'))
@check_registration
def register_user(call: CallbackQuery):
    """
    Регистрирует пользователя
    """
    user_id = call.data.lstrip('register_')
    with open('users.json') as file:
        users = json.load(file)
    users[user_id] = "manager"
    with open('users.json', 'w') as file:
        json.dump(users, file, ensure_ascii=False, indent=4)

    bot.answer_callback_query(
        call.id,
        text='Пользователь зарегистрирован'
    )
    bot.send_message(
        int(user_id),
        text='Ваша регистрация одобрена. Можно начать работать.\n/start'
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('deny_'))
@check_registration
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
        text='Ваша регистрация отклонена'
    )


if __name__ == '__main__':
    bot.infinity_polling()
