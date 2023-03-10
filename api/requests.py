import os

import requests
from dotenv import load_dotenv
from requests import Response

from .errors import retry_on_network_error, check_response

load_dotenv()
_headers = {"Authorization": os.environ['WB_API_KEY']}


@retry_on_network_error
def get_supplies_response() -> Response:
    """
    Отправляет запрос к API. Получает список поставок.
    @return: Response от API
    @raise: HTTPError, WBAPIError
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
def get_orders_response(supply_id: str) -> Response:
    """
    Отправляет запрос к API. Получает список заказов по данной поставке.
    @param supply_id: id поставки, по которой требуется получить заказы
    @return: Response от API
    @raise: HTTPError, WBAPIError
    """
    response = requests.get(
        f"https://suppliers-api.wildberries.ru/api/v3/supplies/{supply_id}/orders",
        headers=_headers)
    check_response(response)
    return response


@retry_on_network_error
def get_product_response(article: str) -> Response:
    """
    Отправляет запрос к API. Получает описание товара по артикулу.
    @param article: артикул товара
    @return: Response от API
    @raise: HTTPError, WBAPIError
    """
    request_json = {"vendorCodes": [article]}
    response = requests.post(
        "https://suppliers-api.wildberries.ru/content/v1/cards/filter",
        json=request_json,
        headers=_headers)
    check_response(response)
    return response


@retry_on_network_error
def get_sticker_response(order_ids: list[int]) -> Response:
    """
    Отправляет запрос к API. Получает стикеры по списку заказов
    @param order_ids: Список id заказов
    @return: Response от API
    @raise: HTTPError, WBAPIError
    """
    json_ = {"orders": order_ids}
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


@retry_on_network_error
def send_deliver_request(supply_id: str) -> int:
    """
    Отправляет поставку в доставку.
    @param supply_id: id поставки
    @return: статус код запроса
    @raise: HTTPError, WBAPIError
    """
    response = requests.patch(
        f"https://suppliers-api.wildberries.ru/api/v3/supplies/{supply_id}/deliver",
        headers=_headers)
    response.raise_for_status()
    return response.status_code


@retry_on_network_error
def get_supply_sticker_response(supply_id: str) -> Response:
    """
    Получает QR-code поставки, которая уже находится в доставке
    @param supply_id: id поставки
    @return: Response от API
    @raise: HTTPError, WBAPIError
    """
    params = {
        "type": "png",
        "width": 58,
        "height": 40}
    response = requests.get(
        f"https://suppliers-api.wildberries.ru/api/v3/supplies/{supply_id}/barcode",
        headers=_headers,
        params=params)
    check_response(response)
    return response
