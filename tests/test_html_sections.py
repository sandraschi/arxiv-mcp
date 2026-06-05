"""Section-aware HTML chunking for depot ingest."""

from __future__ import annotations

from arxiv_mcp.html_sections import chunk_texts_from_html_dom, prepare_ingest_from_html


def test_chunk_texts_from_html_dom_sections() -> None:
    html = """
    <html><body><main>
    <section class="ltx_section">
      <h2 class="ltx_title">Introduction</h2>
      <p>First paragraph about the topic.</p>
    </section>
    <section class="ltx_section">
      <h2 class="ltx_title">Methods</h2>
      <p>We describe the experimental setup in detail here.</p>
    </section>
    </main></body></html>
    """
    chunks = chunk_texts_from_html_dom(html)
    assert chunks is not None
    assert len(chunks) >= 2
    assert any("Introduction" in c for c in chunks)
    assert any("Methods" in c for c in chunks)


def test_prepare_ingest_from_html_math_and_strategy() -> None:
    html = """
    <html><body><main>
    <section><h2>Results</h2><p>Outcome text.</p>
    <math><annotation encoding="application/x-tex">\\alpha</annotation></math>
    </section>
    </main></body></html>
    """
    md, chunks, meta = prepare_ingest_from_html(html)
    assert md.strip()
    assert chunks
    assert meta.get("chunk_strategy") in ("html_sections", "markdown_headings")
