import os

import requests
from requests import Response

from .errors import retry_on_network_error, check_response
from models import OrderModel

_headers = {"Authorization": os.environ['WB_API_KEY']}

@retry_on_network_error
def get_supplies_response() -> Response:
    """
    Отправляет запрос к API. Получает список поставок.
    @return: Response от API
    @raise: HttpError, WBAPIError
    """
    params = {
        "limit": 1000,
        "next": 0}
    # Находим последнюю страницу с поставками
    while True:
        response = requests.get(
            "https://suppliers-api.wildberries.ru/api/v3/supplies",
            headers=_headers,
            params=params)
        check_response(response)
        if response.json()["supplies"] == params["limit"]:
            params["next"] = response.json()["next"]
            continue
        else:
            return response


@retry_on_network_error
def get_orders_response(supply_id: str) -> Response | None:
    """
    Отправляет запрос к API. Получает список заказов по данной поставке.
    @param supply_id: id поставки, по которой требуется получить заказы
    @return: Response от API
    @raise: HttpError, WBAPIError
    """
    response = requests.get(
        f"https://suppliers-api.wildberries.ru/api/v3/supplies/{supply_id}/orders",
        headers=_headers)
    check_response(response)
    return response


@retry_on_network_error
def get_product_response(article: str) -> Response | None:
    """
    Отправляет запрос к API. Получает описание товара по артикулу.
    @param article: артикул товара
    @return: Response от API
    @raise: HttpError, WBAPIError
    """
    request_json = {"vendorCodes": [article]}
    response = requests.post(
        "https://suppliers-api.wildberries.ru/content/v1/cards/filter",
        json=request_json,
        headers=_headers)
    check_response(response)
    return response


@retry_on_network_error
def get_sticker_response(orders: list[OrderModel]) -> Response | None:
    """
    Отправляет запрос к API. Получает стикеры по списку заказов
    @param orders: Список заказов полученных из БД
    @return: Response от API
    @raise: HttpError, WBAPIError
    """
    json_ = {"orders": [order.id for order in orders]}
    params = {
        "type": "png",
        "width": 58,
        "height": 40}
    response = requests.post(
        "https://suppliers-api.wildberries.ru/api/v3/orders/stickers",
        headers=_headers,
        json=json_,
        params=params)
    check_response(response)
    return response
