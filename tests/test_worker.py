from app.models import IngestionJob, DocumentVersion, Chunk
from app.worker import claim_job, process_job
from .conftest import upload, blank_pdf_fixture


def test_pdf_text_worker_preserves_page_number_and_not_indexed(context, tokens):
    c = context["client"]
    res = upload(c, tokens["alice"]).json()
    with context["sessions"]() as db:
        job_id = claim_job(db)
        assert job_id == res["job_id"]
        assert process_job(db, context["store"], context["settings"], job_id)
    status = c.get(f"/api/v1/jobs/{job_id}", headers=tokens["alice"])
    assert status.status_code == 200
    assert status.json()["status"] == "TEXT_EXTRACTED"
    assert status.json()["index_run_id"] is None
    with context["sessions"]() as db:
        chunks = db.query(Chunk).filter_by(version_id=res["version_id"]).all()
        assert len(chunks) > 0
        assert all(chunk.page_number == 1 and chunk.index_run_id is None for chunk in chunks)
        assert "Secret corporate report" in context["store"].path(chunks[0].text_object_key).read_text()
        assert claim_job(db) is None


def test_scanned_pdf_is_not_falsely_marked_ready(context, tokens):
    c = context["client"]
    res = upload(c, tokens["alice"], blank_pdf_fixture()).json()
    with context["sessions"]() as db:
        job_id = claim_job(db)
        assert process_job(db, context["store"], context["settings"], job_id)
    job = c.get(f"/api/v1/jobs/{res['job_id']}", headers=tokens["alice"]).json()
    assert job["status"] == "NEEDS_OCR"
    assert job["failure_code"] == "PDF_NO_EXTRACTABLE_TEXT"
    assert job["index_run_id"] is None
