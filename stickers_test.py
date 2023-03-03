import argparse
from pprint import pprint

from PyPDF2 import PdfReader, PdfWriter
from reportlab.graphics.barcode import code128
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm, inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Image, BaseDocTemplate, PageTemplate, Frame, NextPageTemplate, \
    PageBreak


def create_pdf():
    Elements = []

    doc = BaseDocTemplate('test.pdf', showBoundary=0)

    frame = Frame(0, 0, 120 * mm, 75 * mm)

    def barcode(canvas, doc):
        canvas.saveState()
        barcode128 = code128.Code128(123456789)
        barcode128.drawHumanReadable()
        barcode128.drawOn(canvas, 20, 20)
        canvas.restoreState()

    Elements.append(Image('image.png', useDPI=300, width=95 * mm, height=65 * mm))
    Elements.append(NextPageTemplate('Barcode'))
    Elements.append(PageBreak())
    Elements.append(NextPageTemplate('Image'))
    Elements.append(PageBreak())
    Elements.append(Image('image.png', useDPI=300, width=95 * mm, height=65 * mm))
    Elements.append(NextPageTemplate('Barcode'))
    Elements.append(PageBreak())
    Elements.append(PageBreak())

    doc.addPageTemplates([PageTemplate(id='Image', frames=frame, pagesize=[120 * mm, 75 * mm]),
                          PageTemplate(id='Barcode', frames=frame, pagesize=[120 * mm, 75 * mm], onPage=barcode)])
    doc.build(Elements)


def join_page_by_page(*pdf_files):
    pdfs = [PdfReader(pdf_file) for pdf_file in pdf_files]
    pdf_lens = [len(pdf.pages) for pdf in pdfs]
    if len(set(pdf_lens)) != 1:
        print('Количество страниц в файлах должно быть одинаковым')
        return
    else:
        pdf_len = pdf_lens[0]

    writer = PdfWriter()
    for page in range(pdf_len):
        for pdf in pdfs:
            writer.add_page(pdf.pages[page])
    writer.write('result.pdf')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--join_page_by_page',
        nargs='*',
        type=str,
        help='Соединить pdf файлы постранично. '
             'Например python main.py --join_page_by_page 1.pdf 2.pdf 3.pdf 4.pdf'
    )
    parser.add_argument(
        '--create_pdf',
        action='store_true',
        help='Создает pdf файл'
    )
    args = parser.parse_args()
    if args.join_page_by_page:
        join_page_by_page(*args.join_page_by_page)
    if args.create_pdf:
        create_pdf()


if __name__ == '__main__':
    main()
