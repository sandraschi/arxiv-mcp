"""JSON Schema for MCP ``output_schema`` — HTML/Jina tools (success + structured errors)."""

from __future__ import annotations

# Flexible: success discriminates; other keys depend on path (additionalProperties allows paper fields).
_HTML_TOOL_BASE_PROPS: dict[str, object] = {
    "type": "object",
    "required": ["success"],
    "properties": {
        "success": {
            "type": "boolean",
            "description": "False means validation/HTTP/transport failure; see error, recovery_options.",
        },
        "error": {"type": "string"},
        "error_type": {"type": "string"},
        "http_status": {"type": ["integer", "null"]},
        "url": {"type": ["string", "null"]},
        "recovery_options": {"type": "array", "items": {"type": "string"}},
        "query": {"type": "string"},
        "total_results": {"type": "integer"},
        "papers": {"type": "array", "description": "List of paper dicts when success."},
        "page": {"type": "integer"},
        "page_size": {"type": "integer"},
        "parse_stats": {
            "type": "object",
            "description": "blocks_seen, parsed_ok, parse_failed for HTML scraping.",
        },
        "paper": {"type": "object", "description": "Present when getPaper succeeds."},
        "content": {"type": "string", "description": "Jina Reader body when getContent succeeds."},
        "abs_url": {"type": "string"},
        "jina_url": {"type": "string"},
        "category": {"type": "string"},
        "category_name": {"type": "string"},
        "count": {"type": "integer"},
        "categories": {"type": "array"},
    },
    "additionalProperties": True,
}

HTML_SEARCH_OUTPUT_SCHEMA: dict[str, object] = {
    **_HTML_TOOL_BASE_PROPS,
    "description": "arxiv.org HTML search: success with papers + parse_stats, or structured error.",
}

GET_PAPER_HTML_OUTPUT_SCHEMA: dict[str, object] = {
    **_HTML_TOOL_BASE_PROPS,
    "description": "Abs-page HTML metadata: success with paper, or structured error.",
}

GET_CONTENT_OUTPUT_SCHEMA: dict[str, object] = {
    **_HTML_TOOL_BASE_PROPS,
    "description": "Jina Reader full text: success with content/abs_url/jina_url, or structured error.",
}

GET_RECENT_OUTPUT_SCHEMA: dict[str, object] = {
    **_HTML_TOOL_BASE_PROPS,
    "description": "Category recent list HTML: success with papers + parse_stats, or structured error.",
}

LIST_CATEGORIES_OUTPUT_SCHEMA: dict[str, object] = {
    **_HTML_TOOL_BASE_PROPS,
    "description": "Static category catalog: success with categories array.",
}
