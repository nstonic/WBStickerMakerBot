import datetime
from dataclasses import dataclass

from pydantic import BaseModel, Field


class Supply(BaseModel):
    """Класс для парсинга информации о поставке полученной от API"""
    supply_id: str = Field(alias='id')
    name: str
    closed_at: datetime.datetime = Field(alias='closedAt', default=None)
    created_at: datetime.datetime = Field(alias='createdAt')
    is_done: bool = Field(alias='done')

    def to_tuple(self):
        return self.supply_id, self.name, self.closed_at, self.created_at, self.is_done


class Order(BaseModel):
    """Класс для парсинга информации о заказе полученной от API"""
    order_id: int = Field(alias='id')
    article: str
    created_at: datetime.datetime = Field(alias='createdAt')


class Sticker(BaseModel):
    """Класс для парсинга информации о стикере полученной от API"""
    order_id: int = Field(alias='orderId')
    file: str
    partA: str
    partB: str


class SupplySticker(BaseModel):
    """Класс для парсинга информации о стикере отгруженной поставки"""
    barcode: str
    image_string: str = Field(alias='file')


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
        for characteristic in product_card.get('characteristics'):
            if name := characteristic.get('Наименование'):
                break
        else:
            name = 'Наименование продукции'
        barcode = product_card['sizes'][0]['skus'][0]
        article = product_card.get('vendorCode', '0000000000')
        return Product(
            name=name,
            barcode=barcode,
            article=article)
