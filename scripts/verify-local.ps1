[CmdletBinding()]
param(
    [string]$Python = "python",
    [switch]$SkipInstall,
    [switch]$SkipImage
)

$ErrorActionPreference = "Stop"
$root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))

function Invoke-Python {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $Python $($Arguments -join ' ')"
    }
}

Push-Location $root
try {
    if (-not $SkipInstall) {
        Invoke-Python -Arguments @("-m", "pip", "install", "--requirement", "requirements-dev.txt")
    }
    Invoke-Python -Arguments @("-m", "ruff", "check", ".")
    Invoke-Python -Arguments @("-m", "compileall", "-q", "app", "tests", "wsgi.py")
    Invoke-Python -Arguments @("-m", "pytest")

    if (-not $SkipImage) {
        $revision = (& git rev-parse HEAD).Trim()
        $dirty = -not [string]::IsNullOrWhiteSpace((& git status --porcelain) -join "`n")
        $tag = "ecommerce-payment:sha-$revision" + $(if ($dirty) { "-dirty" } else { "" })
        & docker build --label "org.opencontainers.image.revision=$revision" `
            --tag $tag .
        if ($LASTEXITCODE -ne 0) { throw "Payment image build failed." }
    }
}
finally {
    Pop-Location
}

Write-Host "Payment local gate passed."
