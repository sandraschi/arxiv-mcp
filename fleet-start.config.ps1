# Per-repo fleet start config for arxiv-mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'arxiv-mcp'
    BackendPort  = 10770
    FrontendPort = 10771
    HealthPath   = '/api/health'
    WebRoot      = 'D:\Dev\repos\arxiv-mcp\web_sota'
    NssmService  = 'arxiv-mcp'
    Backend = @{
        Kind = 'nssm'
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}
