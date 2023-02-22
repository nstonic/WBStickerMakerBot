import os

import telebot
from dotenv import load_dotenv
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from api import get_supplies_response
from classes import Supply

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
def get_supplies(call: CallbackQuery):
    """
    Отображает текущие незакрытые поставки
    :param call:
    :return: None
    """
    response = get_supplies_response(os.environ['WB_API_KEY'])

    supplies = [
        Supply.parse_obj(supply)
        for supply in response.json()["supplies"]
    ]

    supplies_markup = InlineKeyboardMarkup()
    for supply in supplies:
        if not supply.done:
            supplies_markup.add(
                InlineKeyboardButton(
                    text=supply.name,
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


if __name__ == '__main__':
    bot.infinity_polling()
