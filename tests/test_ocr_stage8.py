"""Actual Tesseract OCR tests on synthetic scanned PDF, no network services."""
from __future__ import annotations
from io import BytesIO
import shutil
import pytest
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader
from pydantic import ValidationError
from app.worker import extract_pages, claim_job, process_job, PDFLimit
from app.config import Settings
from .conftest import upload


def _font():
    for name in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"):
        if __import__('os').path.isfile(name):
            return ImageFont.truetype(name, 47)
    return ImageFont.load_default()


def scanned_pdf(text="INVOICE 12345 APPROVED"):
    im = Image.new('RGB', (1300, 460), color='white')
    ImageDraw.Draw(im).text((50, 170), text, font=_font(), fill='black')
    out = BytesIO()
    pdf = Canvas(out, pagesize=(600, 330))
    pdf.drawImage(ImageReader(im), 0, 0, width=600, height=330)
    pdf.showPage()
    pdf.save()
    return out.getvalue()


def test_actual_scanned_pdf_ocr_and_page_provenance():
    if shutil.which('tesseract') is None:
        pytest.skip('Tesseract not available on test host')
    doc = scanned_pdf()
    with pytest.raises(Exception):
        # Without OCR, a scanned PDF must never yield text.
        extract_pages(doc, 5, 30000)
    pages = extract_pages(doc, 5, 30000, ocr_enabled=True,
                          ocr_languages='eng', ocr_dpi=190)
    assert len(pages) == 1 and pages[0][0] == 1
    assert 'INVOICE' in pages[0][1]
    assert '12345' in pages[0][1]


def test_worker_scanned_pdf_reaches_text_extracted(context, tokens):
    if shutil.which('tesseract') is None:
        pytest.skip('Tesseract not available on test host')
    context['settings'].ocr_enabled = True
    context['settings'].ocr_languages = 'eng'
    res = upload(context['client'], tokens['alice'], scanned_pdf()).json()
    with context['sessions']() as db:
        job_id = claim_job(db)
        assert process_job(db, context['store'], context['settings'], job_id)
    job = context['client'].get(f'/api/v1/jobs/{job_id}', headers=tokens['alice']).json()
    assert job['status'] == 'TEXT_EXTRACTED'
    assert job['index_run_id'] is None  # GraphRAG publication is separate


def test_ocr_page_limit_is_enforced():
    with pytest.raises(PDFLimit):
        extract_pages(scanned_pdf(), 5, 30000, ocr_enabled=True, ocr_max_pages=0)


def test_ocr_language_setting_rejects_argument_injection():
    with pytest.raises(ValidationError):
        Settings(jwt_secret='test-strong-secret-0123456789abcdefghij',
                 ocr_languages='eng;rm -rf /')


def test_ukrainian_scanned_pdf_ocr():
    if shutil.which('tesseract') is None:
        pytest.skip('Tesseract not available on test host')
    pages = extract_pages(scanned_pdf('АКТ ПРИЙМАННЯ 12345'), 5, 30000,
                          ocr_enabled=True, ocr_languages='ukr', ocr_dpi=200)
    assert pages[0][0] == 1
    assert 'ПРИЙМАННЯ' in pages[0][1] and '12345' in pages[0][1]
