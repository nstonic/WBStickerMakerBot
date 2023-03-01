import os
import shutil
from base64 import b64decode

from barcode import Code128
from barcode.writer import ImageWriter
from fpdf import FPDF
from peewee import ModelSelect
from pypdf import PdfWriter, PdfReader

from api import Product
from models import OrderDbModel


def create_barcode_pdf(products: list[Product]):
    for product in products:
        with open("barcode.png", "wb") as file:
            Code128(product.barcode, writer=ImageWriter()).write(file)
        pdf = FPDF(format=(120, 75))
        pdf.set_auto_page_break(auto=False, margin=0)
        pdf.add_page()
        pdf.image("barcode.png", y=3, x=33, w=55, h=33, type="png")
        pdf.add_font("Arial", fname='arial.ttf', uni=True)
        pdf.set_font("Arial", size=10)
        pdf.ln(30)
        pdf.multi_cell(
            w=0, h=5,
            txt=f"{product.name}\nАртикул: {product.article}\nСтрана: Россия\nБренд: CVT",
            align="L"
        )
        pdf.output(rf"barcodes\{product.article}.pdf")


def create_stickers(orders: ModelSelect, supply_id: str) -> str:
    path_name = f'Stickers for {supply_id}'
    grouped_orders = group_orders_by_article(orders)
    os.makedirs(path_name, exist_ok=True)
    for article, orders in grouped_orders.items():
        save_stickers_to_png(orders)
        create_pdf_from_png(orders, article)
        stickers = PdfReader(f"stickers/{article}.pdf").pages
        writer = PdfWriter()
        for sticker in stickers:
            writer.add_page(sticker)
            barcode = PdfReader(rf"barcodes\{article}.pdf").pages[0]
            writer.add_page(barcode)
        writer.write(rf"{path_name}\{article}.pdf")
    shutil.make_archive(path_name, 'zip', path_name)
    return f'{path_name}.zip'


def group_orders_by_article(orders: ModelSelect):
    grouped_orders = {
        order.product.article: []
        for order in orders
    }
    for order in orders:
        grouped_orders[order.product.article].append(order)
    return grouped_orders


def save_stickers_to_png(orders: list[OrderDbModel]):
    os.makedirs('stickers', exist_ok=True)
    for order in orders:
        sticker_in_byte_format = b64decode(order.sticker, validate=True)
        with open(f"stickers/{order.id}.png", "wb") as file:
            file.write(sticker_in_byte_format)


def create_pdf_from_png(orders: list[OrderDbModel], article: str):
    pdf = FPDF(format=(120, 75))
    pdf.set_auto_page_break(auto=False, margin=0)
    for order in orders:
        pdf.add_page()
        pdf.image(f"stickers/{order.id}.png", y=5, x=10, h=65, type="png")
    pdf.output(rf"stickers/{article}.pdf")

