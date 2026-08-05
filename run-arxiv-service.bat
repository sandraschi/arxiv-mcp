@echo off
cd /d D:\Dev\repos\arxiv-mcp
set PATH=C:\Users\sandr\.local\bin;%PATH%
"%~dp0.venv\Scripts\python.exe" -m arxiv_mcp.__main__ --serve
