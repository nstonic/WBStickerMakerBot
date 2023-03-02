import requests
from requests import Response

from .errors import retry_on_network_error, check_response
from models import OrderModel


@retry_on_network_error
def get_supplies_response(api_key: str) -> Response:
    """
    Отправляет запрос к API. Получает список поставок.
    @param api_key: api ключ wildberries
    @return: Response от API
    @raise: HttpError, WBAPIError
    """
    headers = {"Authorization": api_key}
    params = {
        "limit": 1000,
        "next": 0}
    # Находим последнюю страницу с поставками
    while True:
        response = requests.get(
            "https://suppliers-api.wildberries.ru/api/v3/supplies",
            headers=headers,
            params=params)
        check_response(response)
        if response.json()["supplies"] == params["limit"]:
            params["next"] = response.json()["next"]
            continue
        else:
            return response


@retry_on_network_error
def get_orders_response(api_key: str, supply_id: str) -> Response | None:
    """
    Отправляет запрос к API. Получает список заказов по данной поставке.
    @param api_key: api ключ wildberries
    @param supply_id: id поставки, по которой требуется получить заказы
    @return: Response от API
    @raise: HttpError, WBAPIError
    """
    headers = {"Authorization": api_key}
    response = requests.get(
        f"https://suppliers-api.wildberries.ru/api/v3/supplies/{supply_id}/orders",
        headers=headers)
    check_response(response)
    return response


@retry_on_network_error
def get_product_response(api_key: str, article: str) -> Response | None:
    """
    Отправляет запрос к API. Получает описание товара по артикулу.
    @param api_key: api ключ wildberries
    @param article: артикул товара
    @return: Response от API
    @raise: HttpError, WBAPIError
    """
    headers = {"Authorization": api_key}
    request_json = {"vendorCodes": [article]}
    response = requests.post(
        "https://suppliers-api.wildberries.ru/content/v1/cards/filter",
        json=request_json,
        headers=headers)
    check_response(response)
    return response


@retry_on_network_error
def get_sticker_response(api_key: str, orders: list[OrderModel]) -> Response | None:
    """
    Отправляет запрос к API. Получает стикеры по списку заказов
    @param api_key: api ключ wildberries
    @param orders: Список заказов полученных из БД
    @return: Response от API
    @raise: HttpError, WBAPIError
    """
    headers = {"Authorization": api_key}
    json_ = {"orders": [order.id for order in orders]}
    params = {
        "type": "png",
        "width": 58,
        "height": 40}
    response = requests.post(
        "https://suppliers-api.wildberries.ru/api/v3/orders/stickers",
        headers=headers,
        json=json_,
        params=params)
    check_response(response)
    return response
