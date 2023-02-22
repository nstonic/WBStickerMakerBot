import os
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
def show_supplies(call: CallbackQuery):
    """
    Отображает текущие незакрытые поставки
    :param call:
    :return: None
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
            text='Показать предыдущие закрытые',
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
    :param call:
    :return: None
    """
    response = get_orders_response(
        api_key=os.environ['WB_API_KEY'],
        supply_id=call.data.lstrip('supply_')
    )
    bot.answer_callback_query(call.id, 'Заказы')

    orders = [
        Order.parse_obj(order)
        for order in response.json()['orders']
    ]
    bot.send_message(
        chat_id=call.message.chat.id,
        text=compile_orders_to_one_message(orders),
    )


def compile_orders_to_one_message(orders: list[Order]) -> str:
    if orders:
        message_text = '\n'.join(
            sorted(
                [
                    order.article
                    for order in orders
                ]
            )
        )
    else:
        message_text = 'В данной поставе нет заказов'
    return message_text


if __name__ == '__main__':
    bot.infinity_polling()
