import datetime

from pydantic import BaseModel, Field


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


class Sticker(BaseModel):
    file: str
    order_id: int = Field(alias='orderId')
    partA: str
    partB: str


class Product:

    def __init__(self, product_card: dict):
        name = 'Наименование продукции'
        for characteristic in product_card.get('characteristics'):
            if name := characteristic.get('Наименование'):
                break
        self.name = name
        self.barcode = product_card['sizes'][0]['skus'][0]
        self.article = product_card.get('vendorCode', '0000000000')
