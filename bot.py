import os
import re

import telebot
from dotenv import load_dotenv
from requests import HTTPError
from telebot.types import Message, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup
from telebot.util import quick_markup

from api.errors import WBAPIError
from api.methods import get_new_orders
from api.methods import get_orders, add_order_to_supply, create_new_supply, delete_supply_by_id
from api.methods import get_supplies
from api.methods import get_supply_sticker
from api.methods import send_supply_to_deliver
from db_client import bulk_insert_orders, delete_supply_from_db
from db_client import bulk_insert_supplies
from db_client import get_order_by_id
from db_client import insert_user
from db_client import prepare_db
from stickers import save_image_from_str_to_png, rotate_image
from utils import add_stickers_and_products_to_orders, make_menu_from_list, convert_to_created_ago
from utils import check_registration, create_orders_markup
from utils import create_supplies_markup
from utils import delete_temp_sticker_files
from utils import join_orders
from utils import prepare_stickers

load_dotenv()
bot = telebot.TeleBot(os.environ['TG_BOT_TOKEN'], parse_mode=None)


def ask_for_registration(message: Message):
    """Отправляет администратору запрос на регистрацию пользователя"""
    user_id = message.chat.id
    register_markup = quick_markup(
        {
            'Одобрить': {'callback_data': f'register_{user_id}_{message.from_user.full_name}'},
            'Отказать': {'callback_data': f'deny_{user_id}'}
        }
    )
    bot.send_message(
        chat_id=os.environ['OWNER_ID'],
        text=f'Запрос на регистрацию пользователя\n{message.from_user.full_name}',
        reply_markup=register_markup)
    bot.send_message(
        chat_id=user_id,
        text='Бот находится в разработке')
    # text='Запрос на регистрацию отправлен администратору. Ожидайте ответа.')


def send_message_on_error(exception: Exception, message: Message):
    """Отправляет сообщение администратору и пользователю при ошибке запроса к API"""
    if isinstance(exception, WBAPIError):
        bot.send_message(
            chat_id=message.chat.id,
            text='Что-то пошло не так. Администратор уже разбирается')
    if isinstance(exception, HTTPError):
        bot.send_message(
            chat_id=message.chat.id,
            text='Ошибка сервера. Попробуйте позже')
    bot.send_message(
        chat_id=os.environ['OWNER_ID'],
        text=f'Ошибка у пользователя: {message.from_user.id}\n{exception}')


@bot.message_handler(regexp='Основное меню')
@bot.message_handler(commands=['start'])
@check_registration(ask_for_registration)
def start(message: Message):
    """
    Показывает основное меню
    @param message:
    """
    supplies_markup = make_menu_from_list(
        ['Показать поставки', 'Новые заказы']
    )
    bot.send_message(
        message.chat.id,
        text='Основное меню',
        reply_markup=supplies_markup
    )


@bot.message_handler(regexp='Показать поставки')
@check_registration(ask_for_registration)
def show_active_supplies(message: Message):
    """
    Обработчик поставок.
    Отображает текущие незакрытые поставки. Загружает их в базу
    """
    try:
        active_supplies = get_supplies()
    except (HTTPError, WBAPIError) as ex:
        send_message_on_error(ex, message)
        return

    bot.send_message(
        chat_id=message.chat.id,
        text='Текущие незакрытые поставки',
        reply_markup=create_supplies_markup(
            active_supplies,
            show_create_new=True
        )
    )
    bulk_insert_supplies(active_supplies)


@bot.message_handler(regexp='Новые заказы')
@check_registration(ask_for_registration)
def show_new_orders(message: Message):
    """
    Запрашивает новые заказы, отправляет клиенту в виде кнопок
    """
    try:
        new_orders = get_new_orders()
    except (HTTPError, WBAPIError) as ex:
        send_message_on_error(ex, message)
        return

    orders_markup = create_orders_markup(new_orders)
    bot.send_message(
        message.chat.id,
        'Новые заказы:\n(Артикул | Время с момента заказа)',
        reply_markup=orders_markup
    )
    bulk_insert_orders(new_orders)


@bot.callback_query_handler(func=lambda call: call.data.startswith('order_'))
@check_registration(ask_for_registration)
def show_order_details(call: CallbackQuery):
    """
    Показывает детали заказа и прелагает переместить его в поставку
    @param call:
    """
    order_id = call.data.lstrip('order_')
    order = get_order_by_id(int(order_id))
    bot.answer_callback_query(call.id, f'Информация по заказу {order.id}')
    order_markup = quick_markup(
        {
            'Перенести в поставку': {'callback_data': f'move_to_supply_{order.id}'}
        }
    )
    bot.send_message(
        call.message.chat.id,
        f'Номер заказа: {order.id}\n'
        f'Поставка: {order.supply}\n'
        f'Артикул: {order.product.article}\n'
        f'Время с момента заказа: {convert_to_created_ago(order.created_at)}',
        reply_markup=order_markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('move_to_supply_'))
@check_registration(ask_for_registration)
def move_order_to_supply(call: CallbackQuery):
    """
    Предлагает выбрать поставку, в которую добавится заказ
    @param call:
    """
    order_id = call.data.lstrip('move_to_supply_')

    try:
        active_supplies = get_supplies()
    except (HTTPError, WBAPIError) as ex:
        send_message_on_error(ex, call.message)
        return

    if active_supplies:
        bot.answer_callback_query(call.id, 'Поставки загружены')
    else:
        bot.answer_callback_query(call.id, 'Нет активных поставок')

    bot.send_message(
        chat_id=call.message.chat.id,
        text='Выберите поставку',
        reply_markup=create_supplies_markup(
            active_supplies,
            show_more_supplies=False,
            order_to_append=order_id
        )
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('append_o_to_s_'))
@check_registration(ask_for_registration)
def append_order_to_supply(call: CallbackQuery):
    """
    Добавляет заказ к поставке
    @param call:
    """
    order_id = re.search(r'_\d+_', call.data).group().strip('_')
    supply_id = call.data.lstrip(f'append_o_to_s_{order_id}_')

    try:
        add_order_to_supply(supply_id, order_id)
    except (HTTPError, WBAPIError) as ex:
        send_message_on_error(ex, call.message)
        return
    else:
        bot.answer_callback_query(call.id, 'Добавлено')
        bot.send_message(call.message.chat.id, 'Заказ добавлен в поставку')


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
        orders = get_orders(supply_id)
    except (HTTPError, WBAPIError) as ex:
        send_message_on_error(ex, call.message)
    else:
        if orders:
            order_markup = quick_markup({
                'Создать стикеры': {'callback_data': f'stickers_for_supply_{supply_id}'},
                'Отправить в доставку': {'callback_data': f'close_supply_{supply_id}'}
            }, row_width=1)
            bot.send_message(
                chat_id=call.message.chat.id,
                text=f'Заказы по поставке {supply_id}:\n\n{join_orders(orders)}',
                reply_markup=order_markup)
        else:
            order_markup = quick_markup({
                'Удалить поставку': {'callback_data': f'delete_supply_{supply_id}'}
            }, row_width=1)
            bot.send_message(
                chat_id=call.message.chat.id,
                text=f'В поставке нет заказов',
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
            limit=number_of_supplies)
    except (HTTPError, WBAPIError) as ex:
        send_message_on_error(ex, call.message)
    else:
        bot.send_message(
            chat_id=call.message.chat.id,
            text=f'Последние {number_of_supplies} поставок',
            reply_markup=create_supplies_markup(
                supplies,
                show_create_new=True
            )
        )
        bulk_insert_supplies(supplies)


@bot.callback_query_handler(func=lambda call: call.data.startswith('create_supply'))
@check_registration(ask_for_registration)
def delete_supply(call: CallbackQuery):
    """
    Запрашивает имя новой поставки
    """
    bot.clear_reply_handlers(call.message)
    bot.register_next_step_handler(
        call.message,
        create_supply)
    cancel_markup = ReplyKeyboardMarkup(resize_keyboard=True)
    cancel_markup.add(KeyboardButton('Отмена'))
    bot.send_message(
        chat_id=call.message.chat.id,
        text='Введите название новой поставки',
        reply_markup=cancel_markup
    )


@check_registration(ask_for_registration)
def create_supply(message: Message):
    """
    Создает новую поставку
    """
    message_text = message.text
    if message_text == 'Отмена':
        start(message)
        return
    try:
        new_supply_id = create_new_supply(message_text)
    except (HTTPError, WBAPIError) as ex:
        send_message_on_error(ex, message)
    else:
        bot.send_message(
            chat_id=message.chat.id,
            text=f'Новая поставка {new_supply_id} успешно создана')
        show_active_supplies(message)


@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_supply_'))
@check_registration(ask_for_registration)
def delete_supply(call: CallbackQuery):
    """
    Удаляет поставку
    """
    supply_id = call.data.lstrip('delete_supply_')
    try:
        delete_supply_by_id(supply_id)
    except (HTTPError, WBAPIError) as ex:
        send_message_on_error(ex, call.message)
    else:
        delete_supply_from_db(supply_id)
        bot.answer_callback_query(call.id, 'Поставка удалена')
        show_active_supplies(call.message)


@bot.callback_query_handler(func=lambda call: call.data.startswith('register_'))
@check_registration(ask_for_registration)
def register_user(call: CallbackQuery):
    """
    Регистрирует пользователя
    """
    user_id = re.search(r'_\d+_', call.data).group().strip('_')
    user_full_name = call.data.lstrip(f'register_{user_id}_')
    insert_user(
        user_id=user_id,
        user_full_name=user_full_name)
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
        sticker_file_name, stickers_report = prepare_stickers(supply_id=supply_id)
    except (HTTPError, WBAPIError) as ex:
        send_message_on_error(ex, call.message)
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
        delete_temp_sticker_files()


@bot.callback_query_handler(func=lambda call: call.data.startswith('close_supply_'))
@check_registration(ask_for_registration)
def close_supply(call: CallbackQuery):
    """
    Отправляет поставку в доставку и присылает пользователю QR код
    """
    supply_id = call.data.lstrip('close_supply_')
    try:
        status_code = send_supply_to_deliver(supply_id)
        if status_code != 204:
            raise WBAPIError(message=call.data, code=status_code)
    except (HTTPError, WBAPIError) as ex:
        send_message_on_error(ex, call.message)
        return
    else:
        bot.answer_callback_query(call.id, 'Отправлено в доставку')

        supply_sticker = get_supply_sticker(supply_id)

        os.makedirs('stickers', exist_ok=True)
        image_file_path = os.path.join('stickers', f'{supply_id}.png')

        save_image_from_str_to_png(supply_sticker.image_string, image_file_path)
        rotate_image(image_file_path)
        with open(image_file_path, 'rb') as image:
            bot.send_photo(call.message.chat.id, image)
    finally:
        delete_temp_sticker_files()


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
