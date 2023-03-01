import requests
from requests import Response

from .errors import retry_on_network_error, check_response
from models import OrderModel


@retry_on_network_error
def get_supplies_response(api_key: str) -> Response | None:
    """
    Получает список поставок
    """
    headers = {"Authorization": api_key}
    params = {
        "limit": 1000,
        "next": 0
    }
    # Находим последнюю страницу с поставками
    while True:
        response = requests.get(
            "https://suppliers-api.wildberries.ru/api/v3/supplies",
            headers=headers,
            params=params
        )
        check_response(response)
        if response.json()["supplies"] == params["limit"]:
            params["next"] = response.json()["next"]
            continue
        else:
            return response


@retry_on_network_error
def get_orders_response(api_key: str, supply_id: str) -> Response | None:
    """
    Получает список заказов по данной поставке
    :param api_key:
    :param supply_id:
    :return:
    """
    headers = {"Authorization": api_key}
    response = requests.get(
        f"https://suppliers-api.wildberries.ru/api/v3/supplies/{supply_id}/orders",
        headers=headers
    )

    check_response(response)
    return response


@retry_on_network_error
def get_product_response(api_key: str, article: str) -> Response | None:
    """
    Получает описание товара по артикулу
    """
    headers = {"Authorization": api_key}
    request_json = {"vendorCodes": [article]}
    response = requests.post("https://suppliers-api.wildberries.ru/content/v1/cards/filter",
                             json=request_json,
                             headers=headers)

    check_response(response)
    return response


@retry_on_network_error
def get_sticker_response(api_key: str, orders: list[OrderModel]) -> Response | None:
    headers = {"Authorization": api_key}
    json_ = {"orders": [order.id for order in orders]}
    params = {
        "type": "png",
        "width": 58,
        "height": 40
    }

    response = requests.post(
        "https://suppliers-api.wildberries.ru/api/v3/orders/stickers",
        headers=headers,
        json=json_,
        params=params
    )
    check_response(response)
    return response
