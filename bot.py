import os

import telebot
from dotenv import load_dotenv
from requests import HTTPError
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import Message, CallbackQuery
from telebot.util import quick_markup

from api.errors import WBAPIError
from api.methods import get_orders, get_supplies
from db_client import bulk_insert_orders
from db_client import bulk_insert_supplies
from db_client import insert_user
from db_client import prepare_db
from utils import join_orders, add_stickers_and_products_to_orders
from utils import check_registration
from utils import get_supplies_markup
from utils import prepare_stickers
from utils import delete_tempfiles

load_dotenv()
bot = telebot.TeleBot(os.environ['TG_BOT_TOKEN'], parse_mode=None)


def ask_for_registration(message: Message):
    """Отправляет администратору запрос на регистрацию пользователя"""
    user_id = message.chat.id
    register_markup = quick_markup(
        {'Одобрить': {'callback_data': f'register_{user_id}'},
         'Отказать': {'callback_data': f'deny_{user_id}'}})
    bot.send_message(
        chat_id=os.environ['OWNER_ID'],
        text=f'Запрос на регистрацию пользователя\n{message.from_user.full_name}',
        reply_markup=register_markup)
    bot.send_message(
        chat_id=user_id,
        text='Бот находится в разработке.')
        # text='Запрос на регистрацию отправлен администратору. Ожидайте ответа.')


@bot.message_handler(commands=['start'])
@check_registration(ask_for_registration)
def start(message: Message):
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
    Обработчик поставок.
    Отображает текущие незакрытые поставки. Загружает их в базу
    """
    try:
        active_supplies = get_supplies()
    except WBAPIError as ex:
        bot.answer_callback_query(call.id, 'Что-то пошло не так. Администратор уже разбирается')
        bot.send_message(
            chat_id=os.environ['OWNER_ID'],
            text=ex.__str__())
        return
    except HTTPError:
        bot.answer_callback_query(call.id, 'Ошибка сервера. Попробуйте позже')
        return

    if active_supplies:
        bot.answer_callback_query(call.id, 'Поставки загружены')
    else:
        bot.answer_callback_query(call.id, 'Нет активных поставок')

    bot.send_message(
        chat_id=call.message.chat.id,
        text='Текущие незакрытые поставки',
        reply_markup=get_supplies_markup(active_supplies))

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
    try:
        orders = get_orders(supply_id=supply_id)
    except WBAPIError as ex:
        bot.answer_callback_query(call.id, 'Что-то пошло не так. Администратор уже разбирается')
        bot.send_message(
            chat_id=os.environ['OWNER_ID'],
            text=ex.__str__())
        return
    except HTTPError:
        bot.answer_callback_query(call.id, 'Ошибка сервера. Попробуйте позже')
        return

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
    (если пользователю нужно посмотреть не только текущие открытые поставки, но и более ранние)
    """
    bot.clear_reply_handlers(call.message)
    bot.register_next_step_handler(
        call.message,
        show_number_of_supplies,
        call=call)
    bot.send_message(
        chat_id=call.message.chat.id,
        text='Сколько последних поставок вы хотите посмотреть? (максимум 50)')


@check_registration(ask_for_registration)
def show_number_of_supplies(message: Message, call: CallbackQuery):
    """
    Отображает требуемое число поставок, начиная с самых поздних
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

    try:
        supplies = get_supplies(
            only_active=False,
            number_of_supplies=number_of_supplies)
    except WBAPIError as ex:
        bot.answer_callback_query(call.id, 'Что-то пошло не так. Администратор уже разбирается')
        bot.send_message(
            chat_id=os.environ['OWNER_ID'],
            text=ex.__str__())
        return
    except HTTPError:
        bot.answer_callback_query(call.id, 'Ошибка сервера. Попробуйте позже')
        return

    bot.send_message(
        chat_id=call.message.chat.id,
        text=f'Последние {number_of_supplies} поставок',
        reply_markup=get_supplies_markup(supplies))

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
        user_full_name=call.from_user.full_name)
    bot.answer_callback_query(
        call.id,
        text='Пользователь зарегистрирован')
    bot.send_message(
        user_id,
        text='Ваша регистрация одобрена. Можно начать работать.\n/start')


@bot.callback_query_handler(func=lambda call: call.data.startswith('deny_'))
@check_registration(ask_for_registration)
def deny_registration(call: CallbackQuery):
    """
    Отклоняет запрос регистрации
    """
    user_id = call.data.lstrip('deny_')
    bot.answer_callback_query(
        call.id,
        text='Регистрация отклонена')
    bot.send_message(
        int(user_id),
        text='Ваш запрос на регистрацию отклонен')


@bot.callback_query_handler(func=lambda call: call.data.startswith('stickers_for_supply_'))
@check_registration(ask_for_registration)
def send_stickers(call: CallbackQuery):
    """
    Подготавливает и отправляет пользователю стикеры по данной поставке
    """
    supply_id = call.data.lstrip('stickers_for_supply_')
    bot.answer_callback_query(call.id, 'Запущена подготовка стикеров. Подождите')

    try:
        add_stickers_and_products_to_orders(supply_id)
        sticker_file_name, stickers_report = prepare_stickers(supply_id)
    except WBAPIError as ex:
        bot.answer_callback_query(call.id, 'Что-то пошло не так. Администратор уже разбирается')
        bot.send_message(
            chat_id=os.environ['OWNER_ID'],
            text=ex.__str__())
        return
    except HTTPError:
        bot.answer_callback_query(call.id, 'Ошибка сервера. Попробуйте позже')
        return
    else:
        with open(sticker_file_name, 'rb') as file:
            bot.send_document(call.message.chat.id, file)
        if failed_stickers := stickers_report['failed']:
            missing_articles = "\n".join(failed_stickers)
            message_text = f'Стикеры по поставке {supply_id}.\n' \
                           f'Не удалось создать стикеры для товаров:\n{missing_articles}'
        else:
            message_text = f'Стикеры по поставке {supply_id}'
        bot.send_message(call.message.chat.id, message_text)
    finally:
        delete_tempfiles()


def main():
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
