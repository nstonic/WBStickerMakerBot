import os
import shutil
from base64 import b64decode

from barcode import Code128
from barcode.writer import ImageWriter
from fpdf import FPDF
from pathvalidate import sanitize_filename
from peewee import ModelSelect
from pypdf import PdfWriter, PdfReader

from api.classes import Product
from models import OrderModel


def create_barcode_pdf(products: list[Product]) -> dict[str:list]:
    """Создает pdf со штрихкодом и описанием товара
    @param products: список товаров, представленных как результаты парсинга
    запросов к API
    @return: Ответ по созданным штрихкодам в виде словаря:
    {
        'successfully': [],  - список артикулов, для которых штрихкод успешно создан
        'failed': []         - список артикулов, для которых штрихкод создать не удалось
    }
    """
    products_report = {
        'successfully': [],
        'failed': []}
    for product in products:
        pdf = FPDF(format=(120, 75))
        pdf.set_auto_page_break(auto=False, margin=0)
        pdf.add_page()
        if product.barcode:
            with open('barcode.png', 'wb') as file:
                Code128(product.barcode, writer=ImageWriter()).write(file)
            pdf.image('barcode.png', y=3, x=33, w=55, h=33, type='png')
            pdf.add_font('Arial', fname='arial.ttf', uni=True)
            pdf.set_font('Arial', size=10)
            pdf.ln(30)
            pdf.multi_cell(
                w=0, h=5,
                txt=f'{product.name}\nАртикул: {product.article}\nСтрана: Россия\nБренд: CVT',
                align='L')
            products_report['successfully'].append(product.article)
        else:
            products_report['failed'].append(product.article)

        os.makedirs("barcodes", exist_ok=True)
        file_name = sanitize_filename(product.article.strip())
        barcode_path = os.path.join('barcodes', f'{file_name}.pdf')
        pdf.output(barcode_path)
    return products_report


def create_stickers(orders: ModelSelect, supply_id: str) -> str:
    """
    Создаёт результирующий файл с набором стикеров. По каждому артикулу отдельный файл
    Затем архивирует их в zip
    @param orders: Выборка заказов из БД
    @param supply_id: ID поставки
    @return: путь к zip-архиву
    """
    supply_path = f'Stickers for {supply_id}'
    grouped_orders = group_orders_by_article(orders)
    os.makedirs(supply_path, exist_ok=True)
    for article, orders in grouped_orders.items():
        file_name = f'{sanitize_filename(article.strip())}.pdf'
        barcode_path = os.path.join('barcodes', file_name)
        barcode = PdfReader(barcode_path).pages[0]
        save_stickers_to_png(orders)
        create_pdf_from_png(orders)
        sticker_path = os.path.join('stickers', file_name)
        stickers = PdfReader(sticker_path).pages
        writer = PdfWriter()
        for sticker in stickers:
            writer.add_page(sticker)
            writer.add_page(barcode)
        output_pdf_path = os.path.join(supply_path, f'{file_name}.pdf')
        writer.write(output_pdf_path)
    shutil.make_archive(supply_path, 'zip', supply_path)
    return f'{supply_path}.zip'


def group_orders_by_article(orders: ModelSelect) -> dict[str:OrderModel]:
    """
    Группирует заказы по артикулам
    @param orders: Выборка заказов из БД
    @return: словарь со сгруппированными заказами
    """
    grouped_orders = {
        order.product.article: []
        for order in orders}
    for order in orders:
        grouped_orders[order.product.article].append(order)
    return grouped_orders


def save_stickers_to_png(orders: list[OrderModel]):
    """
    Сохраняет стикер заказа в png файл
    @param orders: Список заказов, полученных из БД
    """
    os.makedirs('stickers', exist_ok=True)
    for order in orders:
        sticker_in_byte_format = b64decode(order.sticker, validate=True)
        sticker_path = os.path.join('stickers', f'{order.id}.png')
        with open(sticker_path, 'wb') as file:
            file.write(sticker_in_byte_format)


def create_pdf_from_png(orders: list[OrderModel]):
    """
    Из png стикера сохраняет pdf
    @param orders: Список заказов, полученных из БД
    """
    article = orders[0].product.article
    pdf = FPDF(format=(120, 75))
    pdf.set_auto_page_break(auto=False, margin=0)
    for order in orders:
        pdf.add_page()
        png_path = os.path.join('stickers', f'{order.id}.png')
        pdf.image(png_path, y=5, x=10, h=65, type='png')
    pdf_path = os.path.join('stickers', f'{article}.pdf')
    pdf.output(pdf_path)
