import time

from requests import HTTPError, Response
from requests.exceptions import ChunkedEncodingError


class WBAPIError(HTTPError):
    """Исключения для обработки ошибок запроса к API"""

    def __init__(self, code: str, message: str):
        self.message = message
        self.code = code

    def __str__(self):
        return f'{self.code}: {self.message}'


def check_response(response: Response):
    """Функция для обработки ошибок запросов к API"""
    response.raise_for_status()
    response_json = response.json()  # может возникнуть requests.exceptions.JSONDecodeError
    if response_json.keys() == ('code', 'message'):
        raise WBAPIError(
            code=response_json['code'],
            message=response_json['message']
        )


def retry_on_network_error(func):
    """Декоратор повторяет запрос, если произошел разрыв соединения"""

    def wrapper(url):
        delay = 0
        while True:
            delay = min(delay, 30)
            try:
                return func(url)
            except (ChunkedEncodingError, ConnectionError):
                time.sleep(delay)
                delay += 5
                continue

    return wrapper
