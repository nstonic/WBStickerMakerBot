import os
from base64 import b64decode

from pathvalidate import sanitize_filename
from reportlab.graphics.barcode import code128
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, PageTemplate, NextPageTemplate
from reportlab.platypus import Image, Frame, PageBreak
from reportlab.platypus.para import Paragraph
from reportlab.platypus.tables import Table

from models import OrderModel


def save_stickers_to_png(orders: list[OrderModel]):
    """
    Сохраняет стикер заказа в png файл
    @param orders: Список заказов, полученных из БД
    """
    os.makedirs('Stickers', exist_ok=True)
    sticker_pathes = []
    for order in orders:
        sticker_in_byte_format = b64decode(order.sticker, validate=True)
        with open(order.sticker_path, 'wb') as file:
            file.write(sticker_in_byte_format)
        sticker_pathes.append(order.sticker_path)
    return sticker_pathes


def create_pdf(grouped_orders: dict[str:list[OrderModel]], supply_id: str) -> tuple[str, dict]:
    """
    Создает pdf файлы со стикерами для каждого артикула.
    В файл помещаются стикеры и штрихкоды для каждого заказ по данному артикулу
    @param grouped_orders: словарь со заказами, сгруппированными по артикулам
                            {
                              Артикул1 : [Заказ1, Заказ2]
                              и т.д.
                            }
    @param supply_id: ID поставки
    @return: путь к папке с полученными файлами и отчёт о создании стикеров
    """
    stickers_report = {
        'successfully': [],
        'failed': []
    }

    supply_path = sanitize_filename(f'Stickers for {supply_id}')
    os.makedirs(supply_path, exist_ok=True)
    pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
    style = getSampleStyleSheet()['BodyText']
    style.fontName = 'Arial'
    frame_sticker = Frame(0, 0, 120 * mm, 75 * mm)
    frame_description = Frame(10 * mm, 5 * mm, 100 * mm, 40 * mm)

    for article, orders in grouped_orders.items():
        file_name = sanitize_filename(article.strip())
        output_pdf_path = os.path.join(supply_path, f'{file_name}.pdf')
        pdf = BaseDocTemplate(output_pdf_path, showBoundary=0)
        save_stickers_to_png(orders)

        elements = []
        for order in orders:
            try:
                data = [
                    [Paragraph(order.product.name, style)],
                    [Paragraph(f'Артикул: {order.product.article}', style)],
                    [Paragraph('Страна: Россия', style)],
                    [Paragraph('Бренд: CVT', style)]
                ]
            except TypeError:
                stickers_report['failed'].append(order.product.article)
                continue
            else:
                stickers_report['successfully'].append(order.product.article)

            elements.append(Image(order.sticker_path, useDPI=300, width=95 * mm, height=65 * mm))
            elements.append(NextPageTemplate('Barcode'))
            elements.append(PageBreak())
            elements.append(Table(data, colWidths=[100 * mm]))
            elements.append(NextPageTemplate('Image'))
            elements.append(PageBreak())

            def barcode(canvas, doc):
                canvas.saveState()
                barcode128 = code128.Code128(order.product.barcode, barHeight=50, barWidth=1.45, humanReadable=True)
                barcode128.drawOn(canvas, x=19.5 * mm, y=53 * mm)
                canvas.restoreState()

            pdf.addPageTemplates(
                [
                    PageTemplate(id='Image', frames=frame_sticker, pagesize=[120 * mm, 75 * mm]),
                    PageTemplate(id='Barcode', frames=frame_description, pagesize=[120 * mm, 75 * mm],
                                 onPage=barcode)
                ]
            )
        pdf.build(elements)
    return supply_path, stickers_report
