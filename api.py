import requests
from requests.exceptions import HTTPError, JSONDecodeError
from requests import Response
from errors import check_response, retry_on_network_error, WBAPIError


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
        if response.json()["supplies"] == params["limit"]:
            params["next"] = response.json()["next"]
            continue
        else:
            return response


@retry_on_network_error
def get_orders_response(api_key: str, supply_id: str) -> Response | None:
    """
    Получает список заказов по данной поставке
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
    else:
        return response


@retry_on_network_error
def get_product_response(api_key: str, articles: str) -> Response | None:
    headers = {"Authorization": api_key}
    for article in sorted(articles):
        request_json = {"vendorCodes": [article]}
        response = requests.post("https://suppliers-api.wildberries.ru/content/v1/cards/filter",
                                 json=request_json,
                                 headers=headers)
        try:
            check_response(response)
        except (HTTPError, JSONDecodeError, WBAPIError) as ex:
            print(ex)
        else:
            return response
