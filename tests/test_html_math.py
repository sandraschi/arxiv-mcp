"""MathML → TeX injection for arXiv HTML conversion."""

from __future__ import annotations

from arxiv_mcp.html_extract import assess_conversion_quality, html_to_markdown


def test_html_to_markdown_injects_tex_from_mathml() -> None:
    html = """
    <html><body><main>
    <p>Intro</p>
    <math display="block">
      <annotation encoding="application/x-tex">E = mc^2</annotation>
    </math>
    </main></body></html>
    """
    md = html_to_markdown(html)
    assert "mc^2" in md or "E" in md
    quality = assess_conversion_quality(html, md, tex_replaced=1)
    assert quality["tex_injected_count"] >= 1
