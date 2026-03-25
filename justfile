# arxiv-mcp — fleet recipes (uv). Run: just --list

default:
    @just --list

sync:
    uv sync --extra dev

lint:
    uv run ruff check src tests

fmt:
    uv run ruff format src tests

test:
    uv run pytest

ty:
    uv run ty check src

precommit:
    uv run pre-commit run --all-files

serve:
    uv run python -m arxiv_mcp --serve

stdio:
    uv run python -m arxiv_mcp --stdio

# Pack Claude Desktop bundle (requires `mcpb` CLI on PATH; see assets/prompts + manifest.json)
mcpb-pack:
    mcpb pack . dist/arxiv-mcp.mcpb
