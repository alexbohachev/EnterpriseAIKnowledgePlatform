"""Minimal offline PDF text extraction worker.

Document is *not* marked indexed/READY: Stage 4 publishes Qdrant+Neo4j together.
"""
from datetime import datetime, timedelta, timezone
import subprocess
import shutil
from io import BytesIO
import time
from pypdf import PdfReader
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from .config import Settings
from .db import make_session_factory
from .models import IngestionJob, DocumentVersion, Chunk, AuditEvent, utc_now
from .storage import LocalStorage


class PDFNoText(Exception):
    pass


class PDFLimit(Exception):
    pass


class OCRUnavailable(Exception):
    pass


class OCRProcessingError(Exception):
    pass


def _ocr_page(pdf_bytes: bytes, page_index: int, *, languages: str, dpi: int,
              timeout_seconds: int) -> str:
    """Bounded local raster + offline Tesseract, no network or shell invocation.

    This does NOT isolate untrusted PDF parsing. Run the OCR worker in a
    separate restricted sandbox/container on production deployments.
    """
    if shutil.which("tesseract") is None:
        raise OCRUnavailable("Local Tesseract executable is not installed")
    try:
        import fitz  # PyMuPDF rasterizer; only required with OCR enabled
    except ImportError as exc:
        raise OCRUnavailable("PyMuPDF missing") from exc
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
            page = document.load_page(page_index)
            scale = dpi / 72.0
            est_pixels = int(page.rect.width * scale) * int(page.rect.height * scale)
            if est_pixels > 9_000_000:
                raise PDFLimit("OCR raster exceeds pixel budget")
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale),
                                     colorspace=fitz.csGRAY, alpha=False)
            if pixmap.width * pixmap.height > 9_000_000:
                raise PDFLimit("OCR raster exceeds pixel budget")
            image = pixmap.tobytes("png")
        # Controlled argv and bounded subprocess duration. Stderr is not copied
        # into user-facing exceptions because it may include document data.
        proc = subprocess.run(
            ["tesseract", "stdin", "stdout", "-l", languages, "--psm", "3"],
            input=image, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout_seconds, check=False)
        if proc.returncode != 0:
            raise OCRProcessingError("Local OCR returned nonzero status")
        return proc.stdout.decode("utf-8", errors="replace").strip()
    except subprocess.TimeoutExpired as exc:
        raise OCRProcessingError("Local OCR exceeded page timeout") from exc
    except PDFLimit:
        raise
    except OCRProcessingError:
        raise
    except (ValueError, RuntimeError) as exc:
        raise OCRProcessingError("Failed to rasterize page for OCR") from exc


def extract_pages(pdf_bytes: bytes, max_pages: int, max_chars: int, *,
                  ocr_enabled: bool = False, ocr_languages: str = "eng+ukr+rus",
                  ocr_dpi: int = 170, ocr_timeout_seconds: int = 25,
                  ocr_max_pages: int = 20):
    reader = PdfReader(BytesIO(pdf_bytes), strict=False)
    if reader.is_encrypted:
        raise PDFLimit("Encrypted PDFs not supported in Stage 3")
    if len(reader.pages) > max_pages:
        raise PDFLimit("Too many pages")
    extracted = []
    budget = 0
    ocr_attempts = 0
    for index, page in enumerate(reader.pages, start=1):
        data = (page.extract_text() or "").strip()
        if not data and ocr_enabled:
            ocr_attempts += 1
            if ocr_attempts > ocr_max_pages:
                raise PDFLimit("Too many pages needing OCR")
            data = _ocr_page(pdf_bytes, index - 1, languages=ocr_languages,
                             dpi=ocr_dpi, timeout_seconds=ocr_timeout_seconds)
        budget += len(data)
        if budget > max_chars:
            raise PDFLimit("Excessive extracted text")
        if data:
            extracted.append((index, data))
    if not extracted:
        raise PDFNoText()
    return extracted


def make_chunks(text: str, length=1400, overlap=150):
    # Deterministic, bounded splitter; preserves page provenance, not semantic chunking.
    if length <= overlap:
        raise ValueError("Invalid chunk settings")
    result = []
    for start in range(0, len(text), length - overlap):
        chunk = text[start:start + length]
        if chunk:
            result.append(chunk)
        if start + length >= len(text):
            break
    return result


def claim_job(session: Session) -> str | None:
    now = utc_now()
    # SELECT FOR UPDATE SKIP LOCKED works with PostgreSQL; SQLite tests run sequentially.
    job = session.scalar(
        select(IngestionJob)
        .where(or_(IngestionJob.status == "PENDING",
                   (IngestionJob.status == "PROCESSING") & (IngestionJob.lease_until < now)))
        .where(IngestionJob.attempts < 3)
        .order_by(IngestionJob.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if not job:
        return None
    job.attempts += 1
    job.status = "PROCESSING"
    job.lease_until = now + timedelta(minutes=10)
    session.commit()
    return job.id


def process_job(session: Session, store: LocalStorage, cfg: Settings, job_id: str):
    job = session.get(IngestionJob, job_id)
    if not job or job.status != "PROCESSING":
        return False
    version = session.get(DocumentVersion, job.version_id)
    written = []
    try:
        pdf = store.path(version.object_key).read_bytes()
        pages = extract_pages(
            pdf, cfg.max_pdf_pages, cfg.max_extracted_chars,
            ocr_enabled=cfg.ocr_enabled, ocr_languages=cfg.ocr_languages,
            ocr_dpi=cfg.ocr_dpi, ocr_timeout_seconds=cfg.ocr_timeout_seconds,
            ocr_max_pages=cfg.ocr_max_pages)
        ordinal = 0
        for page_number, page_text in pages:
            for piece in make_chunks(page_text):
                key = store.save_text(piece)
                written.append(key)
                session.add(Chunk(version_id=version.id, page_number=page_number,
                                  ordinal=ordinal, text_object_key=key))
                ordinal += 1
        job.status = "TEXT_EXTRACTED"  # not searchable yet; Stage 4 will index
        job.failure_code = None
        job.lease_until = None
        session.add(AuditEvent(actor_id=None, action="text_extracted", decision="allow",
                               target_id=version.document_id))
        session.commit()
    except (PDFNoText, OCRUnavailable):
        session.rollback()
        # OCR is not implemented; do not silently treat scanned PDF as successful.
        job = session.get(IngestionJob, job_id)
        job.status = "NEEDS_OCR"
        job.failure_code = "PDF_NO_EXTRACTABLE_TEXT"
        job.lease_until = None
        session.commit()
    except Exception as exc:
        session.rollback()
        for key in written:
            store.delete(key)
        job = session.get(IngestionJob, job_id)
        job.status = "FAILED"
        job.failure_code = (
            "PDF_LIMIT" if isinstance(exc, PDFLimit) else
            "OCR_PROCESSING_ERROR" if isinstance(exc, OCRProcessingError) else
            "PDF_PARSE_ERROR")
        job.lease_until = None
        session.commit()
    return True


def run_forever(poll_seconds=2.0):
    cfg = Settings()
    _, factory = make_session_factory(cfg.database_url)
    store = LocalStorage(cfg.storage_root)
    print("PDF worker online (OCR optional; GraphRAG indexed separately)", flush=True)
    while True:
        with factory() as session:
            job_id = claim_job(session)
            if job_id:
                process_job(session, store, cfg, job_id)
        if not job_id:
            time.sleep(poll_seconds)


if __name__ == "__main__":
    run_forever()
