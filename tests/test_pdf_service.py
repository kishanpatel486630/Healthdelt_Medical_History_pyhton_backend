from app.services.pdf_service import build_text_lines, render_simple_pdf


def test_build_text_lines_and_render():
    sections = [("Heading", "This is a test body."), ("Next", "Another body.")]
    lines = build_text_lines("Title", sections)
    assert isinstance(lines, list)
    pdf = render_simple_pdf("Title", sections)
    assert isinstance(pdf, (bytes, bytearray))
    assert pdf.startswith(b"%PDF-1.4")
