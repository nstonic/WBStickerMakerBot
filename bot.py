import os
from collections import Counter
from pprint import pprint

import telebot
from dotenv import load_dotenv
from telebot.types import (Message,
                           InlineKeyboardMarkup,
                           InlineKeyboardButton,
                           CallbackQuery)

from api import get_supplies_response, get_orders_response
from classes import Supply, Order

load_dotenv()
bot = telebot.TeleBot(os.environ['TG_BOT_TOKEN'], parse_mode=None)


@bot.message_handler(commands=['start'])
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
                    text=f'{supply.name} | (создана: {supply.create_at.strftime("%d.%m.%Y")})',
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
        text=compile_orders_to_one_message(orders),
        reply_markup=order_markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('more_supplies'))
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
                text=f'{supply.name} | (создана: {supply.create_at.strftime("%d.%m.%Y")}) | {is_active[supply.done]}',
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


def compile_orders_to_one_message(orders: list[Order]) -> str:
    """Собирает все артикулы из заказов и компилирует их в одно сообщение"""
    if orders:
        articles = [order.article for order in orders]
        message_text = '\n'.join(
            [
                f'{article} - {count}шт.'
                for article, count in Counter(articles.sort()).items()
            ]
        )
    else:
        message_text = 'В данной поставе нет заказов'
    return message_text


if __name__ == '__main__':
    bot.infinity_polling()
