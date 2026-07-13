# NSSM service wrapper for arxiv-mcp
$ErrorActionPreference = "Stop"
$env:ARXIV_MCP_PORT = "10770"
$env:ARXIV_MCP_HOST = "127.0.0.1"
Set-Location "D:\Dev\repos\arxiv-mcp"
C:\Users\sandr\.local\bin\uv.exe run python -m arxiv_mcp.__main__ --serve
