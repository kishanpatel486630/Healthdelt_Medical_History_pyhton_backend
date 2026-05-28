"""PDF service."""

from __future__ import annotations

from textwrap import wrap


def build_text_lines(title: str, sections: list[tuple[str, str]]) -> list[str]:
	lines = [title, ""]
	for heading, body in sections:
		lines.append(heading)
		lines.extend(wrap(body or "", width=90) or [""])
		lines.append("")
	return lines


def _escape_pdf_text(text: str) -> str:
	return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def render_text_pdf_bytes(title: str, lines: list[str]) -> bytes:
	content_lines = []
	y = 760
	content_lines.append("BT")
	content_lines.append("/F1 18 Tf")
	content_lines.append(f"72 {y} Td")
	content_lines.append(f"({_escape_pdf_text(title)}) Tj")
	content_lines.append("/F1 11 Tf")
	for line in lines:
		y -= 16
		content_lines.append(f"0 -16 Td")
		content_lines.append(f"({_escape_pdf_text(line)}) Tj")
	content_lines.append("ET")

	stream = "\n".join(content_lines).encode("latin-1", errors="replace")

	objects = []
	objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
	objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
	objects.append(
		b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
	)
	objects.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
	objects.append(f"5 0 obj << /Length {len(stream)} >> stream\n".encode("latin-1") + stream + b"\nendstream endobj\n")

	buffer = bytearray(b"%PDF-1.4\n")
	offsets = [0]
	for obj in objects:
		offsets.append(len(buffer))
		buffer.extend(obj)
	xref_offset = len(buffer)
	buffer.extend(f"xref\n0 {len(offsets)}\n".encode("latin-1"))
	buffer.extend(b"0000000000 65535 f \n")
	for offset in offsets[1:]:
		buffer.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
	buffer.extend(f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode("latin-1"))
	return bytes(buffer)


def render_simple_pdf(title: str, sections: list[tuple[str, str]]) -> bytes:
	return render_text_pdf_bytes(title, build_text_lines(title, sections))


class PdfService:
	"""Class wrapper for PDF helper functions to enable DI and testing."""

	def build_text_lines(self, title: str, sections: list[tuple[str, str]]) -> list[str]:
		return build_text_lines(title, sections)

	def render_text_pdf_bytes(self, title: str, lines: list[str]) -> bytes:
		return render_text_pdf_bytes(title, lines)

	def render_simple_pdf(self, title: str, sections: list[tuple[str, str]]) -> bytes:
		return render_simple_pdf(title, sections)
