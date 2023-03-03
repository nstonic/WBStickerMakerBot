import os
from base64 import b64decode

from pathvalidate import sanitize_filename
from reportlab.graphics.barcode import code128
from reportlab.lib.units import mm
from reportlab.platypus import Image, BaseDocTemplate, PageTemplate, Frame, NextPageTemplate, \
    PageBreak

from models import OrderModel


def save_stickers_to_png(orders: list[OrderModel]):
    """
    Сохраняет стикер заказа в png файл
    @param orders: Список заказов, полученных из БД
    """
    os.makedirs('stickers', exist_ok=True)
    sticker_pathes = []
    for order in orders:
        sticker_in_byte_format = b64decode(order.sticker, validate=True)
        with open(order.sticker_path, 'wb') as file:
            file.write(sticker_in_byte_format)
        sticker_pathes.append(order.sticker_path)
    return sticker_pathes


def create_pdf(grouped_orders: dict[str:list[OrderModel]], supply_id: str):
    supply_path = sanitize_filename(f'Stickers for {supply_id}')
    os.makedirs(supply_path, exist_ok=True)

    for article, orders in grouped_orders.items():
        file_name = sanitize_filename(article.strip())
        output_pdf_path = os.path.join(supply_path, f'{file_name}.pdf')

        doc = BaseDocTemplate(output_pdf_path, showBoundary=0)
        frame = Frame(0, 0, 120 * mm, 75 * mm)
        save_stickers_to_png(orders)
        Elements = []
        for order in orders:
            Elements.append(Image(order.sticker_path, useDPI=300, width=95 * mm, height=65 * mm))
            Elements.append(NextPageTemplate('Barcode'))
            Elements.append(PageBreak())
            Elements.append(PageBreak())

            def barcode(canvas, doc):
                canvas.saveState()
                barcode128 = code128.Code128(order.product.barcode)
                barcode128.drawHumanReadable()
                barcode128.drawOn(canvas, 20, 20)
                canvas.restoreState()

            doc.addPageTemplates([PageTemplate(id='Image', frames=frame, pagesize=[120 * mm, 75 * mm]),
                                  PageTemplate(id='Barcode', frames=frame, pagesize=[120 * mm, 75 * mm],
                                               onPage=barcode)])
        doc.build(Elements)
    return supply_path


# def create_barcode_pdf(products: list[Product]) -> dict[str:list]:
#     """Создает pdf со штрихкодом и описанием товара
#     @param products: список товаров, представленных как результаты парсинга
#     запросов к API
#     @return: Ответ по созданным штрихкодам в виде словаря:
#     {
#         'successfully': [],  - список артикулов, для которых штрихкод успешно создан
#         'failed': []         - список артикулов, для которых штрихкод создать не удалось
#     }
#     """
#     products_report = {
#         'successfully': [],
#         'failed': []}
#     for product in products:
#         pdf = FPDF(format=(120, 75))
#         pdf.set_auto_page_break(auto=False, margin=0)
#         pdf.add_page()
#         if product.barcode:
#             with open('barcode.png', 'wb') as file:
#                 Code128(product.barcode, writer=ImageWriter()).write(file)
#             pdf.image('barcode.png', y=3, x=33, w=55, h=33, type='png')
#             pdf.add_font('Arial', fname='arial.ttf', uni=True)
#             pdf.set_font('Arial', size=10)
#             pdf.ln(30)
#             pdf.multi_cell(
#                 w=0, h=5,
#                 txt=f'{product.name}\nАртикул: {product.article}\nСтрана: Россия\nБренд: CVT',
#                 align='L')
#             products_report['successfully'].append(product.article)
#         else:
#             products_report['failed'].append(product.article)
#
#         os.makedirs("barcodes", exist_ok=True)
#         file_name = sanitize_filename(product.article.strip())
#         barcode_path = os.path.join('barcodes', f'{file_name}.pdf')
#         pdf.output(barcode_path)
#     return products_report