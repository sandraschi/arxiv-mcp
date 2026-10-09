#Requires -Version 5.1
# Shim -> canonical fleet pack script (fleet-mcpb-pack.ps1). Do not vendor logic here;
# fixes reach the whole fleet at once. See MCPB_PACKAGING_STANDARDS.md 2.2/2.2b.
param([string]$RepoRoot = (Split-Path -Parent $PSScriptRoot))
$fleet = Join-Path (Split-Path -Parent $RepoRoot) 'mcp-central-docs\scripts\fleet-mcpb-pack.ps1'
& $fleet -RepoRoot $RepoRoot
