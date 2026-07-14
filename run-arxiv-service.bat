@echo off
cd /d D:\Dev\repos\arxiv-mcp
set PATH=C:\Users\sandr\.local\bin;%PATH%
set UV_PROJECT_ENVIRONMENT=D:\Dev\repos\arxiv-mcp\.venv
C:\Users\sandr\.local\bin\uv.exe run --directory D:\Dev\repos\arxiv-mcp python -m arxiv_mcp.__main__ --serve
