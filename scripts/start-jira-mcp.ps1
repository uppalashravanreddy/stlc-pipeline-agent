# Load .env from project root and start the JIRA MCP server.
# VS Code's ${env:VAR} reads Windows system env vars, not .env files —
# this wrapper bridges the gap for local development.

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

# Map legacy JIRA_API_KEY to the name @sooperset/mcp-atlassian expects
$env:JIRA_PERSONAL_TOKEN = $env:JIRA_API_KEY
$env:JIRA_SERVER_URL     = $env:JIRA_INSTANCE_URL

npx -y @sooperset/mcp-atlassian
