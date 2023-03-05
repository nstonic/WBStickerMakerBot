from peewee import ModelSelect

from .classes import Supply, Order, Product, Sticker
from .requests import get_product_response, get_orders_response, get_sticker_response, get_supplies_response


def get_orders(supply_id: str) -> list[Order]:
    """
    Получает и парсит информацию о заказах из данной поставке с Wildberries
    @param supply_id: id запрашиваемой поставки
    @return: список заказов, представленных как результаты парсинга
    запросов к API
    @raise: HTTPError, WBAPIError
    """
    response = get_orders_response(
        supply_id=supply_id)
    return [Order.parse_obj(order) for order in response.json()['orders']]


def get_product(article: str) -> Product:
    """
    Получает и парсит информацию о товаре с Wildberries
    @param article: артикул товара
    @return: результат парсинга запроса к API
    @raise: HTTPError, WBAPIError
    """
    response = get_product_response(article)
    for product_card in response.json()["data"]:
        if product_card["vendorCode"] == article:
            return Product.parse_from_card(product_card)
    return Product(article=article)


def get_supplies(
        only_active: bool = True,
        number_of_supplies: int = 50) -> list[Supply]:
    """
    Получает и парсит информацию о поставках с Wildberries
    @param only_active: Если True то возвращает только незакрытые поставки,
    в противном случае - все
    @param number_of_supplies: Максимальное число возвращаемых поставок
    @return: список поставок, представленных как результаты парсинга
    запросов к API
    @raise: HTTPError, WBAPIError
    """
    response = get_supplies_response()
    supplies = []
    for supply in response.json()["supplies"][::-1]:
        if not supply['done'] or only_active is False:
            supply = Supply.parse_obj(supply)
            supplies.append(supply)
        if len(supplies) == number_of_supplies:
            break
    return supplies


def get_stickers(orders: ModelSelect) -> list[Sticker]:
    """
    Получает и парсит информацию о стикерах с Wildberries
    @param orders: Заказы полученные из БД
    @return: список стикеров, представленных как результаты парсинга
    запросов к API
    @raise: HTTPError, WBAPIError
    """
    stickers_response = get_sticker_response(list(orders))
    return [Sticker.parse_obj(sticker) for sticker in stickers_response.json()['stickers']]
