"""Extract plain text from PDF URLs (arXiv PDF fallback for fetch_full_text)."""

from __future__ import annotations

import logging
from io import BytesIO

from arxiv_mcp.config import Settings, load_settings
from arxiv_mcp.http import get_bytes

log = logging.getLogger(__name__)


async def fetch_pdf_plaintext(
    pdf_url: str,
    *,
    max_chars: int = 100_000,
    settings: Settings | None = None,
    max_body_bytes: int = 50_000_000,
) -> tuple[bool, str, str | None]:
    """Download PDF and extract text with pypdf. Returns (ok, text_or_message, error_type)."""
    settings = settings or load_settings()
    payload = await get_bytes(
        pdf_url,
        settings=settings,
        cache_endpoint="pdf",
        max_body_bytes=max_body_bytes,
        use_cache=True,
    )
    if not payload.ok or payload.content is None:
        err = payload.error or {}
        return False, err.get("error", "PDF download failed"), err.get("error_type", "HTTPError")

    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(payload.content))
        parts: list[str] = []
        total = 0
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
                total += len(text)
            if total >= max_chars:
                break
        body = "\n\n".join(parts)[:max_chars].strip()
        if not body:
            return False, "PDF contained no extractable text.", "EmptyPDF"
        return True, body, None
    except Exception as exc:
        log.warning("PDF text extraction failed: %s", exc)
        return False, f"PDF text extraction failed: {exc}", type(exc).__name__
