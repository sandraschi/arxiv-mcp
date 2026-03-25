"""arxiv.org HTML search UI scraping and Jina Reader full-text fetch.

Complements the official ``arxiv`` PyPI client in ``services.papers`` with
tools that use the public website HTML (``search``, ``searchAdvanced``, etc.).

All network I/O returns structured dicts (``success``); HTTP errors do not raise.
"""

from __future__ import annotations

import re
import urllib.parse
from functools import lru_cache
from typing import Any

import httpx
from bs4 import BeautifulSoup

from arxiv_mcp.config import Settings, load_settings
from arxiv_mcp.ids import normalize_arxiv_id

URL_BASE = "https://arxiv.org"

ARXIV_CATEGORIES: dict[str, str] = {
    "cs.AI": "Artificial Intelligence",
    "cs.CL": "Computation and Language",
    "cs.CV": "Computer Vision and Pattern Recognition",
    "cs.LG": "Machine Learning",
    "cs.NE": "Neural and Evolutionary Computing",
    "cs.RO": "Robotics",
    "cs.SE": "Software Engineering",
    "cs.DS": "Data Structures and Algorithms",
    "cs.DB": "Databases",
    "cs.DC": "Distributed, Parallel, and Cluster Computing",
    "cs.CR": "Cryptography and Security",
    "cs.HC": "Human-Computer Interaction",
    "cs.IR": "Information Retrieval",
    "cs.IT": "Information Theory",
    "cs.MA": "Multiagent Systems",
    "cs.PL": "Programming Languages",
    "stat.ML": "Machine Learning (Statistics)",
    "stat.TH": "Statistics Theory",
    "stat.ME": "Methodology",
    "math.OC": "Optimization and Control",
    "math.ST": "Statistics Theory",
    "math.PR": "Probability",
    "math.NA": "Numerical Analysis",
    "quant-ph": "Quantum Physics",
    "cond-mat": "Condensed Matter",
    "hep-th": "High Energy Physics - Theory",
    "eess.SP": "Signal Processing",
    "eess.IV": "Image and Video Processing",
    "eess.AS": "Audio and Speech Processing",
    "q-bio.NC": "Neurons and Cognition",
    "q-bio.QM": "Quantitative Methods",
    "q-fin.ST": "Statistical Finance",
    "q-fin.CP": "Computational Finance",
}

SORT_OPTIONS: dict[str, str] = {
    "relevance": "",
    "date_desc": "-announced_date_first",
    "date_asc": "announced_date_first",
    "submissions_desc": "-submittedDate",
    "submissions_asc": "submittedDate",
}


def tool_error(
    message: str,
    *,
    error_type: str = "Error",
    http_status: int | None = None,
    url: str | None = None,
    recovery_options: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "success": False,
        "error": message,
        "error_type": error_type,
        "http_status": http_status,
        "url": url,
        "recovery_options": list(recovery_options or []),
    }


def _httpx_to_tool_error(exc: BaseException, url: str) -> dict[str, Any]:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        recovery = (
            [
                "Confirm the arXiv id or URL is valid.",
                "Try get_paper_details (API-backed) instead of HTML getPaper.",
            ]
            if status == 404
            else [
                "Retry after a short delay.",
                "Increase ARXIV_MCP_ARXIV_HTTP_TIMEOUT_SECONDS if timeouts persist.",
            ]
        )
        return tool_error(
            f"HTTP {status} when fetching {url}",
            error_type="HTTPStatusError",
            http_status=status,
            url=str(exc.request.url),
            recovery_options=recovery,
        )
    if isinstance(exc, httpx.TimeoutException):
        return tool_error(
            f"Timeout fetching {url}",
            error_type="TimeoutException",
            url=url,
            recovery_options=[
                "Increase ARXIV_MCP_ARXIV_HTTP_TIMEOUT_SECONDS.",
                "For getContent, Jina can be slow; retry or use fetch_full_text (local HTML).",
            ],
        )
    if isinstance(exc, httpx.RequestError):
        return tool_error(
            f"Request failed: {exc}",
            error_type=type(exc).__name__,
            url=url,
            recovery_options=["Check network connectivity and DNS.", "Retry later."],
        )
    return tool_error(
        str(exc),
        error_type=type(exc).__name__,
        url=url,
        recovery_options=["Inspect the message and retry with different inputs."],
    )


def _loose_id_patterns() -> list[re.Pattern[str]]:
    return [
        re.compile(r"arxiv\.org/abs/([\d.]+v?\d*)", re.I),
        re.compile(r"arxiv\.org/pdf/([\d.]+v?\d*)", re.I),
        re.compile(r"^([\d]{4}\.[\d]{4,5}v?\d*)$"),
    ]


def extract_paper_id_loose(raw: str) -> str | None:
    """Best-effort id for Jina/abs URLs; prefers ``normalize_arxiv_id`` when possible."""
    s = raw.strip()
    try:
        return normalize_arxiv_id(s)
    except ValueError:
        pass
    for pat in _loose_id_patterns():
        m = pat.search(s)
        if m:
            return m.group(1)
    return None


def clean_text(text: str) -> str:
    text = text.replace("\n", " ")
    text = " ".join(text.split())
    return text.strip()


def parse_search_results(html: str, query: str, page: int, page_size: int) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select(".arxiv-result")
    blocks_seen = len(items)

    total_results = 0
    total_text = soup.select_one(".title.is-clearfix")
    if total_text:
        match = re.search(r"of ([\d,]+) results", total_text.text)
        if match:
            total_results = int(match.group(1).replace(",", ""))

    papers: list[dict[str, Any]] = []
    parse_failed = 0
    for item in items:
        try:
            title_elem = item.select_one(".title")
            title = clean_text(title_elem.text) if title_elem else "Unknown Title"

            abstract_elem = item.select_one(".abstract-full")
            if not abstract_elem:
                abstract_elem = item.select_one(".abstract")
            abstract = clean_text(abstract_elem.text) if abstract_elem else ""
            abstract = re.sub(r"\s*(Less|More)\s*$", "", abstract)
            abstract = re.sub(r"^Abstract:\s*", "", abstract)

            url_elem = item.select_one(".list-title > span > a")
            url_abstract = url_elem.get("href") if url_elem else ""
            if url_elem is None or not url_abstract:
                parse_failed += 1
                continue
            if not url_abstract.startswith("http"):
                url_abstract = urllib.parse.urljoin(URL_BASE, url_abstract)
            id_arxiv = extract_paper_id_loose(url_abstract) or ""

            authors: list[str] = []
            for author in item.select(".authors a"):
                authors.append(author.text.strip())

            categories: list[str] = []
            for tag in item.select(".tag.is-small"):
                cat_text = tag.text.strip()
                if cat_text and not cat_text.startswith("doi:"):
                    categories.append(cat_text)

            date_published = None
            date_updated = None
            date_elem = item.select_one(".is-size-7")
            if date_elem:
                date_text = date_elem.text
                submitted_match = re.search(r"Submitted\s+(\d+\s+\w+,?\s+\d+)", date_text)
                if submitted_match:
                    date_published = submitted_match.group(1)

            papers.append(
                {
                    "id_arxiv": id_arxiv,
                    "title": title,
                    "abstract": abstract,
                    "authors": authors,
                    "categories": categories,
                    "url_abstract": url_abstract,
                    "url_pdf": f"{URL_BASE}/pdf/{id_arxiv}.pdf" if id_arxiv else "",
                    "date_published": date_published,
                    "date_updated": date_updated,
                }
            )
        except Exception:
            parse_failed += 1
            continue

    parsed_ok = len(papers)
    return {
        "query": query,
        "total_results": total_results,
        "papers": papers,
        "page": page,
        "page_size": page_size,
        "parse_stats": {
            "blocks_seen": blocks_seen,
            "parsed_ok": parsed_ok,
            "parse_failed": parse_failed,
        },
    }


def parse_abs_page(html: str, id_arxiv: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    title_elem = soup.select_one(".title.mathjax")
    title = clean_text(title_elem.text.replace("Title:", "")) if title_elem else "Unknown"

    abstract_elem = soup.select_one(".abstract.mathjax")
    abstract = clean_text(abstract_elem.text.replace("Abstract:", "")) if abstract_elem else ""

    authors: list[str] = []
    authors_div = soup.select_one(".authors")
    if authors_div:
        for a in authors_div.select("a"):
            authors.append(a.text.strip())

    categories: list[str] = []
    subj_elem = soup.select_one(".tablecell.subjects")
    if subj_elem:
        for span in subj_elem.select("span.primary-subject"):
            cat_match = re.search(r"\(([^)]+)\)", span.text)
            if cat_match:
                categories.append(cat_match.group(1))
        subj_text = subj_elem.text
        cat_matches = re.findall(r"\(([a-z-]+\.[A-Z]+)\)", subj_text)
        for cat in cat_matches:
            if cat not in categories:
                categories.append(cat)

    date_submitted = None
    date_history = soup.select_one(".dateline")
    if date_history:
        date_match = re.search(r"Submitted.*?(\d+\s+\w+\s+\d+)", date_history.text)
        if date_match:
            date_submitted = date_match.group(1)

    url_abstract = f"{URL_BASE}/abs/{id_arxiv}"
    return {
        "id_arxiv": id_arxiv,
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "categories": categories,
        "url_abstract": url_abstract,
        "url_pdf": f"{URL_BASE}/pdf/{id_arxiv}.pdf",
        "date_published": date_submitted,
        "date_updated": None,
    }


def parse_recent_list(html: str, category: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    papers: list[dict[str, Any]] = []
    entries = soup.select("dl#articles dt, dl#articles dd")

    pair_blocks_seen = 0
    parse_failed = 0
    i = 0
    while i < len(entries) - 1:
        if entries[i].name == "dt" and entries[i + 1].name == "dd":
            pair_blocks_seen += 1
            dt = entries[i]
            dd = entries[i + 1]
            try:
                id_arxiv = ""
                id_link = dt.select_one("a[href*='/abs/']")
                if id_link:
                    href = id_link.get("href", "")
                    id_match = re.search(r"/abs/([\d.]+v?\d*)", href)
                    if id_match:
                        id_arxiv = id_match.group(1)

                title_elem = dd.select_one(".list-title")
                title = clean_text(title_elem.text.replace("Title:", "")) if title_elem else ""

                authors: list[str] = []
                authors_elem = dd.select_one(".list-authors")
                if authors_elem:
                    for a in authors_elem.select("a"):
                        authors.append(a.text.strip())

                categories: list[str] = []
                subj_elem = dd.select_one(".list-subjects")
                if subj_elem:
                    subj_text = subj_elem.text
                    cat_matches = re.findall(r"([a-z-]+\.[A-Z]+)", subj_text)
                    categories = list(dict.fromkeys(cat_matches))

                if id_arxiv:
                    papers.append(
                        {
                            "id_arxiv": id_arxiv,
                            "title": title,
                            "abstract": "",
                            "authors": authors,
                            "categories": categories,
                            "url_abstract": f"{URL_BASE}/abs/{id_arxiv}",
                            "url_pdf": f"{URL_BASE}/pdf/{id_arxiv}.pdf",
                            "date_published": None,
                            "date_updated": None,
                        }
                    )
                else:
                    parse_failed += 1
            except Exception:
                parse_failed += 1
            i += 2
        else:
            i += 1

    return {
        "category": category,
        "category_name": ARXIV_CATEGORIES.get(category, category),
        "count": len(papers),
        "papers": papers,
        "parse_stats": {
            "blocks_seen": pair_blocks_seen,
            "parsed_ok": len(papers),
            "parse_failed": parse_failed,
        },
    }


@lru_cache(maxsize=1)
def list_categories_payload() -> list[dict[str, str]]:
    categories: list[dict[str, str]] = []
    for code, name in ARXIV_CATEGORIES.items():
        if code.startswith("cs."):
            group = "Computer Science"
        elif code.startswith("stat."):
            group = "Statistics"
        elif code.startswith("math."):
            group = "Mathematics"
        elif code.startswith("eess."):
            group = "Electrical Engineering"
        elif code.startswith("q-bio."):
            group = "Quantitative Biology"
        elif code.startswith("q-fin."):
            group = "Quantitative Finance"
        else:
            group = "Physics"
        categories.append({"code": code, "name": name, "group": group})
    return sorted(categories, key=lambda x: (x["group"], x["code"]))


async def http_get_text_safe(
    url: str,
    *,
    settings: Settings | None = None,
    follow_redirects: bool = False,
    timeout_mult: float = 1.0,
) -> tuple[str | None, dict[str, Any] | None]:
    """Return (text, None) or (None, error dict). Never raises for transport."""
    settings = settings or load_settings()
    timeout = settings.arxiv_http_timeout_seconds * timeout_mult
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=follow_redirects) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text, None
    except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError) as e:
        return None, _httpx_to_tool_error(e, url)
    except Exception as e:
        return None, tool_error(
            str(e),
            error_type=type(e).__name__,
            url=url,
            recovery_options=["Unexpected error during HTTP fetch."],
        )


async def arxiv_org_search_html(
    query: str,
    category: str | None = None,
    author: str | None = None,
    sort_by: str = "relevance",
    page: int = 1,
    page_size: int = 25,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or load_settings()
    page_size = min(page_size, 50)
    start = (page - 1) * page_size

    search_terms: list[str] = []
    if query:
        search_terms.append(query)
    if author:
        search_terms.append(f"au:{author}")
    if category:
        search_terms.append(f"cat:{category}")

    if not search_terms:
        return tool_error(
            "Provide at least one of: query, author, category",
            error_type="ValidationError",
            recovery_options=[
                "Set query and/or author and/or category.",
                "Use searchAdvanced for field-specific filters.",
            ],
        )

    full_query = " AND ".join(search_terms) if len(search_terms) > 1 else search_terms[0]
    encoded_query = urllib.parse.quote_plus(full_query)
    sort_order = SORT_OPTIONS.get(sort_by, "")
    url = (
        f"{URL_BASE}/search/?query={encoded_query}"
        f"&searchtype=all&abstracts=show"
        f"&order={sort_order}&size={page_size}&start={start}"
    )

    html, err = await http_get_text_safe(url, settings=settings)
    if err:
        return err
    data = parse_search_results(html, full_query, page, page_size)
    return {"success": True, **data}


async def arxiv_org_search_advanced_html(
    title: str | None = None,
    abstract: str | None = None,
    author: str | None = None,
    category: str | None = None,
    id_arxiv: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort_by: str = "relevance",
    page: int = 1,
    page_size: int = 25,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or load_settings()
    page_size = min(page_size, 50)
    start = (page - 1) * page_size

    query_parts: list[str] = []
    if title:
        query_parts.append(f"ti:{title}")
    if abstract:
        query_parts.append(f"abs:{abstract}")
    if author:
        query_parts.append(f"au:{author}")
    if category:
        query_parts.append(f"cat:{category}")
    if id_arxiv:
        query_parts.append(f"id:{id_arxiv}")

    if not query_parts:
        return tool_error(
            "At least one search field is required",
            error_type="ValidationError",
            recovery_options=[
                "Pass title, abstract, author, category, and/or id_arxiv.",
                "Use search for simple keyword + author/category filters.",
            ],
        )

    full_query = " AND ".join(query_parts)
    encoded_query = urllib.parse.quote_plus(full_query)
    sort_order = SORT_OPTIONS.get(sort_by, "")
    url = (
        f"{URL_BASE}/search/advanced?terms-0-operator=AND"
        f"&terms-0-term={encoded_query}&terms-0-field=all"
        f"&classification-physics_archives=all"
        f"&classification-include_cross_list=include"
        f"&abstracts=show&size={page_size}&start={start}"
        f"&order={sort_order}"
    )
    if date_from:
        url += f"&date-from_date={date_from}"
    if date_to:
        url += f"&date-to_date={date_to}"

    html, err = await http_get_text_safe(url, settings=settings)
    if err:
        return err
    data = parse_search_results(html, full_query, page, page_size)
    return {"success": True, **data}


async def arxiv_abs_metadata_from_html(
    id_or_url: str, *, settings: Settings | None = None
) -> dict[str, Any]:
    settings = settings or load_settings()
    id_resolved = extract_paper_id_loose(id_or_url)
    if not id_resolved:
        return tool_error(
            f"Could not extract arXiv ID from: {id_or_url}",
            error_type="ValidationError",
            recovery_options=[
                "Use id like 2401.00001 or a full https://arxiv.org/abs/2401.00001 URL.",
                "Try get_paper_details with the same string.",
            ],
        )

    url_abstract = f"{URL_BASE}/abs/{id_resolved}"
    html, err = await http_get_text_safe(url_abstract, settings=settings, follow_redirects=True)
    if err:
        return err
    paper = parse_abs_page(html, id_resolved)
    return {"success": True, "paper": paper}


async def jina_reader_fetch(id_or_url: str, *, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or load_settings()
    id_resolved = extract_paper_id_loose(id_or_url)
    if id_resolved:
        abs_url = f"{URL_BASE}/abs/{id_resolved}"
        url_target = abs_url
    else:
        url_target = (
            id_or_url.strip()
            if id_or_url.strip().startswith("http")
            else f"{URL_BASE}/abs/{id_or_url.strip()}"
        )
        abs_url = url_target

    jina_url = f"{settings.jina_reader_base_url.rstrip('/')}/{url_target}"
    text, err = await http_get_text_safe(jina_url, settings=settings, timeout_mult=2.0)
    if err:
        return err
    return {
        "success": True,
        "content": text,
        "abs_url": abs_url,
        "jina_url": jina_url,
    }


async def arxiv_category_recent_html(
    category: str = "cs.AI",
    count: int = 10,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or load_settings()
    count = min(count, 50)
    url = f"{URL_BASE}/list/{category}/recent?skip=0&show={count}"
    html, err = await http_get_text_safe(url, settings=settings, follow_redirects=True)
    if err:
        return err
    data = parse_recent_list(html, category)
    return {"success": True, **data}


def list_categories_response() -> dict[str, Any]:
    """Wrapped catalog for MCP tool return shape."""
    return {"success": True, "categories": list_categories_payload()}
