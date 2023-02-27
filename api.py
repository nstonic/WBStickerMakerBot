import datetime

import requests
from pydantic import BaseModel, Field
from dataclasses import dataclass
from requests.exceptions import HTTPError
from requests import Response, JSONDecodeError
from errors import check_response, retry_on_network_error, WBAPIError


class Supply(BaseModel):
    name: str
    closed_at: datetime.datetime = Field(alias='closedAt', default=None)
    create_at: datetime.datetime = Field(alias='createdAt')
    done: bool
    sup_id: str = Field(alias='id')

    def to_tuple(self):
        return self.sup_id, self.name, self.closed_at, self.create_at, self.done


class Order(BaseModel):
    order_id: int = Field(alias='id')
    article: str
    created_at: datetime.datetime = Field(alias='createdAt')

    def to_tuple(self) -> tuple:
        return self.order_id, self.article, self.created_at


@dataclass
class Product:
    name: str
    article: str


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
        except (HTTPError, JSONDecodeError, WBAPIError) as ex:
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
def get_product(api_key: str, article: str) -> tuple | None:
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

    wanted_product_card = next(
        filter(
            lambda product: product["vendorCode"] == article,
            response.json()["data"]
        )
    )
    name = next(
        filter(
            lambda characteristic: characteristic.get('Наименование'),
            wanted_product_card["characteristics"]
        )
    )['Наименование']

    return name, article


@retry_on_network_error
def get_sticker_response(api_key: str, orders: list[Order]):
    headers = {"Authorization": api_key}
    json_ = {"orders": [order.order_id for order in orders]}
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
    # print(
    #     [
    #         {sticker['orderId']:sticker['file']}
    #         for sticker in response.json()['stickers']
    #     ]
    # )

    # for order in orders:
    #     for sticker in response.json()["stickers"]:
    #         if sticker["orderId"] == order.order_id:
    #             order.sticker = sticker
    #             break
