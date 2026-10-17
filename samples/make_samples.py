"""Generate sample PDFs and negative-test files. Run: python samples/make_samples.py"""
import os

import numpy as np
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))


def make_pdf(name, lines):
    c = canvas.Canvas(os.path.join(HERE, name), pagesize=A4)
    y = 780
    for size, text in lines:
        c.setFont("Helvetica", size)
        c.drawString(60, y, text)
        y -= size + 14
    c.save()


make_pdf("invoice.pdf", [
    (18, "SUPPLIER INVOICE  INV-2041"), (11, "Date: 2026-10-10"),
    (11, "Ship to: Main Warehouse"), (11, ""),
    (12, "Item: Widget A     SKU: SKU-A     Qty: 100"),
])
make_pdf("receipt.pdf", [
    (18, "WAREHOUSE GOODS RECEIPT  GR-7788"), (11, "Date: 2026-10-12"),
    (11, "Reference: INV-2041"), (11, ""),
    (12, "Item: Widget A     SKU: SKU-A     Received: 90"),
])
make_pdf("blank.pdf", [])  # empty page, negative test

rng = np.random.default_rng(0)
Image.fromarray(rng.integers(0, 256, (240, 320, 3), dtype=np.uint8)).save(
    os.path.join(HERE, "garbage.jpg"))  # random noise, negative test
print("wrote invoice.pdf receipt.pdf blank.pdf garbage.jpg in", HERE)
