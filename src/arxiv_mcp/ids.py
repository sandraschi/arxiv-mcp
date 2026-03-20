"""Normalize user-supplied arXiv identifiers."""

import re

_ARXIV_ABS = re.compile(
    r"arxiv\.org/(?:abs|pdf|html)/(?P<id>[\d.]+v?\d*)(?:\.pdf)?",
    re.IGNORECASE,
)
_RAW_ID = re.compile(r"^(?:arxiv:)?(?P<id>[\d]{4}\.[\d]{4,5}(?:v\d+)?)$", re.IGNORECASE)


def normalize_arxiv_id(paper_id: str) -> str:
    """Return a canonical arXiv id fragment like ``2401.00001v2`` or ``2401.00001``.

    Accepts bare ids, ``arxiv:...`` prefixes, and arxiv.org abs/pdf/html URLs.
    """
    s = paper_id.strip()
    m = _ARXIV_ABS.search(s)
    if m:
        return m.group("id")
    m = _RAW_ID.match(s.replace(" ", ""))
    if m:
        return m.group("id")
    # Fallback: last path-like segment
    if "/" in s:
        tail = s.rstrip("/").split("/")[-1]
        tail = tail.removesuffix(".pdf")
        if re.match(r"^[\d]{4}\.[\d]{4,5}(v\d+)?$", tail):
            return tail
    raise ValueError(f"Unrecognized arXiv id or URL: {paper_id!r}")
