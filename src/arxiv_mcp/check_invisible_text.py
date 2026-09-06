"""Detect invisible/hidden text in PDFs using PyMuPDF.

Complements ``sanitize.py`` (Unicode-level stripping) with PDF rendering-level
detection: transparent text, off-page text, zero-size fonts, white-on-white,
and hidden text discrepancies.

Usage as CLI:
    uv run python -m arxiv_mcp.check_invisible_text paper.pdf

Usage as library:
    from arxiv_mcp.check_invisible_text import detect_invisible_text
    results = detect_invisible_text(pdf_path)

## Return Format
{"success": bool, "total_instances": int, "pages_affected": int,
 "types_found": [str], "findings": {...}, "error": str|null}

## Examples
    detect_invisible_text("/path/to/paper.pdf")
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

log = logging.getLogger(__name__)


def _get_fitz():
    try:
        import fitz

        return fitz
    except ImportError:
        return None


def detect_invisible_text(pdf_path: str) -> dict[str, Any]:
    """Detect invisible text in a PDF using PyMuPDF (synchronous).

    Returns a dict with findings grouped by category and a summary.
    """
    fitz = _get_fitz()
    if fitz is None:
        return {
            "success": False,
            "error": "PyMuPDF (fitz) is not installed. Install with: uv sync --extra inspect",
            "error_type": "MissingDependency",
        }

    doc = fitz.open(pdf_path)
    results: dict[str, list] = {
        "transparent_text": [],
        "off_page_text": [],
        "zero_size_text": [],
        "white_text_on_white": [],
        "hidden_text": [],
    }
    pages_with_findings: set[int] = set()

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_rect = page.rect
        text_dict = page.get_text("dict")

        _check_transparent(text_dict, page_num, results, pages_with_findings)
        _check_off_page(text_dict, page_rect, page_num, results, pages_with_findings)
        _check_zero_size(text_dict, page_num, results, pages_with_findings)
        _check_white(text_dict, page_num, results, pages_with_findings)
        _check_hidden(page, page_num, results, pages_with_findings)

    doc.close()

    total = sum(len(v) for v in results.values())
    types_found = [k for k, v in results.items() if v]
    return {
        "success": True,
        "total_instances": total,
        "pages_affected": len(pages_with_findings),
        "types_found": types_found,
        "findings": {k: v for k, v in results.items() if v},
        "pdf_path": pdf_path,
    }


def _check_transparent(text_dict: dict, page_num: int, results: dict, pages: set[int]) -> None:
    for block in text_dict.get("blocks", []):
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line.get("spans", []):
                color = span.get("color", 0)
                if color is None:
                    continue
                r = (color >> 16) & 255
                g = (color >> 8) & 255
                b = color & 255
                if (r > 250 and g > 250 and b > 250) or color == 0xFFFFFF:
                    text = (span.get("text") or "").strip()
                    if text:
                        pages.add(page_num)
                        results["transparent_text"].append(
                            {
                                "page": page_num,
                                "text": text[:200],
                                "color": f"RGB({r},{g},{b})",
                                "reason": "Very light/white text color",
                            }
                        )


def _check_off_page(text_dict: dict, page_rect, page_num: int, results: dict, pages: set[int]) -> None:
    fitz = _get_fitz()
    if fitz is None:
        return
    for block in text_dict.get("blocks", []):
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line.get("spans", []):
                bbox = span.get("bbox")
                if bbox and not fitz.Rect(bbox).intersects(page_rect):
                    text = (span.get("text") or "").strip()
                    if text:
                        pages.add(page_num)
                        results["off_page_text"].append(
                            {
                                "page": page_num,
                                "text": text[:200],
                                "reason": "Text positioned outside page boundaries",
                            }
                        )


def _check_zero_size(text_dict: dict, page_num: int, results: dict, pages: set[int]) -> None:
    for block in text_dict.get("blocks", []):
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line.get("spans", []):
                size = span.get("size", 0)
                if size <= 0.5:
                    text = (span.get("text") or "").strip()
                    if text:
                        pages.add(page_num)
                        results["zero_size_text"].append(
                            {
                                "page": page_num,
                                "text": text[:200],
                                "font_size": size,
                                "reason": f"Font size too small: {size}",
                            }
                        )


def _check_white(text_dict: dict, page_num: int, results: dict, pages: set[int]) -> None:
    for block in text_dict.get("blocks", []):
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line.get("spans", []):
                color = span.get("color", 0)
                if color in (0xFFFFFF, 16777215):
                    text = (span.get("text") or "").strip()
                    if text:
                        pages.add(page_num)
                        results["white_text_on_white"].append(
                            {
                                "page": page_num,
                                "text": text[:200],
                                "color": "White (RGB(255,255,255))",
                                "reason": "White text on white background",
                            }
                        )


def _check_hidden(page, page_num: int, results: dict, pages: set[int]) -> None:
    all_text = page.get_text()
    blocks = page.get_text("blocks")
    visible_text = "".join(b[4] for b in blocks if isinstance(b, tuple) and len(b) >= 5)
    all_clean = re.sub(r"\s+", " ", all_text.strip())
    vis_clean = re.sub(r"\s+", " ", visible_text.strip())
    if len(all_clean) > len(vis_clean) * 1.1:
        diff = len(all_clean) - len(vis_clean)
        pages.add(page_num)
        results["hidden_text"].append(
            {
                "page": page_num,
                "all_text_length": len(all_clean),
                "visible_text_length": len(vis_clean),
                "potential_hidden_chars": diff,
                "reason": "Extractable text significantly longer than visible text",
            }
        )


async def check_invisible_text(pdf_path: str) -> dict[str, Any]:
    """Async wrapper - runs detection in a thread pool to avoid blocking."""
    return await asyncio.to_thread(detect_invisible_text, pdf_path)


def print_results(results: dict[str, Any]) -> None:
    if not results.get("success"):
        print(f"Error: {results.get('error', 'Unknown error')}")
        return
    print("=" * 60)
    print("INVISIBLE TEXT DETECTION RESULTS")
    print("=" * 60)
    print(f"Total instances: {results['total_instances']}")
    print(f"Pages affected:  {results['pages_affected']}")
    print(f"Types found:     {', '.join(results['types_found'])}")
    print()
    for category, items in results.get("findings", {}).items():
        print(f"\n{category.replace('_', ' ').upper()}:")
        print("-" * 40)
        for item in items:
            print(f"  Page {item['page']}: {item.get('reason', '')}")
            if "text" in item:
                t = item["text"][:100] + ("..." if len(item["text"]) > 100 else "")
                print(f"  Text: '{t}'")
            if "font_size" in item:
                print(f"  Font size: {item['font_size']}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: uv run python -m arxiv_mcp.check_invisible_text <pdf_path>", file=sys.stderr)
        sys.exit(1)
    results = detect_invisible_text(sys.argv[1])
    print_results(results)
    if not results.get("success"):
        sys.exit(1)
