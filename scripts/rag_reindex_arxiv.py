"""Full arXiv depot vector reindex — use with just rag-gpu (venv python, not uv run)."""

from __future__ import annotations

from arxiv_mcp.services.vector_rag import reindex_all_vectors


def main() -> int:
    result = reindex_all_vectors()
    if not result.get("success"):
        print(f"[rag] Failed: {result}")
        return 1
    print(f"[rag] Indexed {result.get('papers', 0)} papers, {result.get('chunks', 0)} chunks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
