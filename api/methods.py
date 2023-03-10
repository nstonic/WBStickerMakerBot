from .classes import Supply, Order, Product, Sticker, SupplySticker
from .requests import get_product_response, get_new_orders_response
from .requests import get_supply_sticker_response
from .requests import get_orders_response
from .requests import get_sticker_response
from .requests import get_supplies_response
from .requests import send_deliver_request


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


def get_stickers(order_ids: list[int]) -> list[Sticker]:
    """
    Получает и парсит информацию о стикерах с Wildberries
    @param order_ids: Список id заказов
    @return: список стикеров, представленных как результаты парсинга
    запросов к API
    @raise: HTTPError, WBAPIError
    """
    stickers_response = get_sticker_response(order_ids)
    return [Sticker.parse_obj(sticker) for sticker in stickers_response.json()['stickers']]


def send_supply_to_deliver(supply_id: str) -> int:
    """
    Отправляет поставку в доставку.
    @param supply_id: id поставки
    @return: код запроса
    @raise: HTTPError, WBAPIError
    """
    return send_deliver_request(supply_id)


def get_supply_sticker(supply_id: str) -> SupplySticker:
    """
    Отправляет поставку в доставку.
    @param supply_id: id поставки
    @return: результат парсинга запроса к API
    @raise: HTTPError, WBAPIError
    """
    response = get_supply_sticker_response(supply_id)
    return SupplySticker.parse_obj(response.json())


def get_new_orders() -> list[Order]:
    """
    Получает и парсит информацию о новых заказах
    @return: список заказов, представленных как результаты парсинга
    запросов к API
    @raise: HTTPError, WBAPIError
    """
    response = get_new_orders_response()
    return [Order.parse_obj(order) for order in response.json()['orders']]
