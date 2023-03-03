import datetime
from dataclasses import dataclass

from pydantic import BaseModel, Field


class Supply(BaseModel):
    """Класс для парсинга информации о поставке полученной от API"""
    name: str
    closed_at: datetime.datetime = Field(alias='closedAt', default=None)
    create_at: datetime.datetime = Field(alias='createdAt')
    done: bool
    sup_id: str = Field(alias='id')

    def to_tuple(self):
        return self.sup_id, self.name, self.closed_at, self.create_at, self.done


class Order(BaseModel):
    """Класс для парсинга информации о заказе полученной от API"""
    order_id: int = Field(alias='id')
    article: str
    created_at: datetime.datetime = Field(alias='createdAt')


class Sticker(BaseModel):
    """Класс для парсинга информации о стикере полученной от API"""
    file: str
    order_id: int = Field(alias='orderId')
    partA: str
    partB: str


@dataclass
class Product:
    """Класс для парсинга информации о товаре полученной от API"""
    article: str
    name: str = None
    barcode: str = None

    @staticmethod
    def parse_from_card(product_card: dict):
        """Парсит товар из карты товара, полученной из json
        @param product_card: Карта товара в виде словаря из json
        @return: Объект парсинга товара
        """
        name = 'Наименование продукции'
        for characteristic in product_card.get('characteristics'):
            if name := characteristic.get('Наименование'):
                break
        barcode = product_card['sizes'][0]['skus'][0]
        article = product_card.get('vendorCode', '0000000000')
        return Product(
            name=name,
            barcode=barcode,
            article=article)
