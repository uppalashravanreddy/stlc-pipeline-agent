# Load .env and start the GitHub MCP server.
# Uses @modelcontextprotocol/server-github (official GitHub MCP server).

$envFile = Join-Path $PSScriptRoot "..\\.env"
if (Test-Path $envFile) {
    foreach ($line in Get-Content $envFile) {
        $line = $line.Trim()
        if ($line -and !$line.StartsWith('#') -and $line -match '^([^=]+)=(.*)$') {
            $name  = $Matches[1].Trim()
            $value = $Matches[2].Trim().Trim('"')
            [System.Environment]::SetEnvironmentVariable($name, $value, 'Process')
        }
    }
}

npx -y @modelcontextprotocol/server-github
