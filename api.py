import requests


def get_supplies_response(api_key: str):
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
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            break
        if response.json()["supplies"] == params["limit"]:
            params["next"] = response.json()["next"]
            continue
        else:
            return response
