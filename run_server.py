"""Entry point for PyInstaller-bundled arxiv-mcp backend."""

import _strptime  # noqa: F401
import sys

sys.path.insert(0, ".")

from arxiv_mcp.__main__ import main

if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv.append("--serve")
    main()
