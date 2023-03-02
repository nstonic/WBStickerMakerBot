import time

from requests import HTTPError, Response
from requests.exceptions import ChunkedEncodingError


class WBAPIError(HTTPError):
    """Исключения для обработки ошибок запроса к API"""

    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code

    def __str__(self):
        return f'{self.code}: {self.message}' if self.code else self.message


def check_response(response: Response):
    """Функция для обработки ошибок запросов к API"""
    response.raise_for_status()
    response_json = response.json()
    if response_json.keys() == ('code', 'message'):
        raise WBAPIError(
            code=response_json['code'],
            message=response_json['message'])
    if response_json.get('error'):
        raise WBAPIError(
            message=f'{response_json["errorText"]}: {response_json["additionalErrors"]}')


def retry_on_network_error(func):
    """Декоратор повторяет запрос, если произошел разрыв соединения"""

    def wrapper(*args, **kwargs):
        delay = 0
        while True:
            delay = min(delay, 30)
            try:
                return func(*args, **kwargs)
            except (ChunkedEncodingError, ConnectionError):
                time.sleep(delay)
                delay += 5
                continue

    return wrapper
