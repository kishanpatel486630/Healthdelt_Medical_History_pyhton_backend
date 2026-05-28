import pytest

from app.services.ai_service import summarize_text, summarize_record


def test_summarize_text_short():
    s = "Short note"
    assert summarize_text(s) == "Short note"


def test_summarize_text_long():
    s = "x" * 500
    out = summarize_text(s, max_length=100)
    assert len(out) <= 100


def test_summarize_record():
    rec = {"title": "Checkup", "diagnosis": "Flu", "symptoms": "cough, fever", "notes": "Some notes"}
    res = summarize_record(rec)
    assert "summary" in res and isinstance(res["summary"], str)
