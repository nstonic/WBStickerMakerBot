from collections import Counter

from barcode import Code128
from barcode.writer import ImageWriter
from fpdf import FPDF
from requests import Response

import api
import db_client
from models import Product


def join_orders(orders: list[api.Order]) -> str:
    """Собирает все артикулы из заказов и объединяет их в одно сообщение"""
    if orders:
        articles = [order.article for order in orders]
        joined_orders = '\n'.join(
            [
                f'{article} - {count}шт.'
                for article, count in Counter(sorted(articles)).items()
            ]
        )
    else:
        joined_orders = 'В данной поставе нет заказов'
    return joined_orders


def fetch_supplies(
        response: Response,
        only_active: bool = True,
        number_of_supplies: int = 50) -> list[api.Supply]:
    """Собирает поставки в список и записывает их в БД"""

    supplies = []
    for supply in response.json()["supplies"][::-1]:
        if not supply['done'] or only_active is False:
            supply = api.Supply.parse_obj(supply)
            supplies.append(supply)
            db_client.insert_supply(supply)
        if len(supplies) == number_of_supplies:
            break
    return supplies


def build_barcode_pdf(product: Product):
    with open("barcode.png", "wb") as file:
        Code128(product.barcode, writer=ImageWriter()).write(file)
    pdf = FPDF(format=(120, 75))
    pdf.set_auto_page_break(auto=False, margin=0)
    pdf.add_page()
    pdf.image("barcode.png", y=3, x=33, w=55, h=33, type="png")
    try:
        pdf.add_font("Arial", fname='arial.ttf', uni=True)
        pdf.set_font("Arial", size=10)
    except:
        input("Скопируйте arial.ttf в папку с программой.\nДля закрытия нажмите Enter")
    pdf.ln(30)
    pdf.multi_cell(w=0, h=5,
                   txt=f"{product.name}\nАртикул: {product.article}\nСтрана: Россия\nБренд: CVT",
                   align="L")

    pdf.output(rf"barcodes\{product.article}.pdf")
