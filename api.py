import datetime

import requests
from pydantic import BaseModel, Field
from requests.exceptions import HTTPError, JSONDecodeError
from requests import Response
from errors import check_response, retry_on_network_error, WBAPIError
from models import OrderDbModel


class Supply(BaseModel):
    name: str
    closed_at: datetime.datetime = Field(alias='closedAt', default=None)
    create_at: datetime.datetime = Field(alias='createdAt')
    done: bool
    sup_id: str = Field(alias='id')


class Order(BaseModel):
    order_id: int = Field(alias='id')
    article: str
    created_at: datetime.datetime = Field(alias='createdAt')


class Sticker(BaseModel):
    file: str
    order_id: int = Field(alias='orderId')
    partA: str
    partB: str


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
        try:
            check_response(response)
        except (HTTPError, WBAPIError) as ex:
            print(ex)
            return
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
    try:
        check_response(response)
    except (HTTPError, JSONDecodeError, WBAPIError) as ex:
        print(ex)
        return
    else:
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

    try:
        check_response(response)
    except (HTTPError, JSONDecodeError, WBAPIError) as ex:
        print(ex)
        return
    return response


def get_product(api_key: str, article: str) -> tuple | None:
    response = get_product_response(api_key, article)
    wanted_product_card = next(filter(
        lambda product: product["vendorCode"] == article,
        response.json()["data"]))

    return next(filter(
        lambda characteristic: characteristic.get('Наименование'),
        wanted_product_card["characteristics"])
    )['Наименование']


@retry_on_network_error
def get_sticker_response(api_key: str, orders: list[OrderDbModel]) -> Response | None:
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
    try:
        check_response(response)
    except (HTTPError, JSONDecodeError, WBAPIError) as ex:
        print(ex)
        return
    return response
