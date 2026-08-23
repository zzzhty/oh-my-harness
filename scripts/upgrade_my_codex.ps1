[CmdletBinding()]
param(
    [string]$Harness,
    [string]$BootstrapPython,
    [string]$CodexPath,
    [string]$CodexHome,
    [string]$ToolingPython,
    [string]$GitMarketplaceSource,
    [string]$GitRef = "main",
    [switch]$Yes,
    [switch]$DryRun,
    [switch]$SkipCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$HarnessWasProvided = $PSBoundParameters.ContainsKey("Harness")
$CodexPathWasProvided = $PSBoundParameters.ContainsKey("CodexPath")
$GitRefWasProvided = $PSBoundParameters.ContainsKey("GitRef")

function Resolve-ExecutableCandidate {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Candidate
    )

    $expanded = [Environment]::ExpandEnvironmentVariables($Candidate)
    if ($expanded.StartsWith("~")) {
        $expanded = Join-Path $env:USERPROFILE $expanded.Substring(1).TrimStart("\", "/")
    }

    if (Test-Path -LiteralPath $expanded -PathType Leaf) {
        return (Resolve-Path -LiteralPath $expanded).Path
    }

    $command = Get-Command -Name $expanded -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($command) {
        if ($command.Path) {
            return $command.Path
        }
        if ($command.Source) {
            return $command.Source
        }
        return $command.Name
    }

    return $null
}

function Resolve-Executable {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Label,

        [string[]]$Candidates
    )

    $checked = New-Object System.Collections.Generic.List[string]
    foreach ($candidate in $Candidates) {
        if (-not $candidate) {
            continue
        }
        $checked.Add($candidate)
        $resolved = Resolve-ExecutableCandidate -Candidate $candidate
        if ($resolved) {
            return $resolved
        }
    }

    throw "$Label not found. Checked:$([Environment]::NewLine)$($checked -join [Environment]::NewLine)"
}

function Resolve-BootstrapPython {
    param(
        [string]$ExplicitPath
    )

    if ($ExplicitPath) {
        return Resolve-Executable -Label "Bootstrap Python" -Candidates @($ExplicitPath)
    }

    return Resolve-Executable `
        -Label "Bootstrap Python" `
        -Candidates @(
            $env:MY_CODEX_BOOTSTRAP_PYTHON,
            "python",
            "py",
            (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"),
            (Join-Path $env:USERPROFILE ".codex\venvs\my-codex\Scripts\python.exe")
        )
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Exe,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,

        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    Write-Host ("+ {0} {1}" -f $Exe, ($Arguments -join " "))
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $repoRoot

$env:MY_CODEX_ROOT = $repoRoot
if (-not $CodexHome) {
    if ($env:CODEX_HOME) {
        $CodexHome = $env:CODEX_HOME
    }
    else {
        $CodexHome = Join-Path $env:USERPROFILE ".codex"
    }
}
$env:CODEX_HOME = [System.IO.Path]::GetFullPath($CodexHome)

if (-not $BootstrapPython) {
    $BootstrapPython = Resolve-BootstrapPython
}
else {
    $BootstrapPython = Resolve-BootstrapPython -ExplicitPath $BootstrapPython
}

if (-not $ToolingPython) {
    $ToolingPython = Join-Path $env:CODEX_HOME "venvs\my-codex\Scripts\python.exe"
}
$env:MY_CODEX_PYTHON = [System.IO.Path]::GetFullPath($ToolingPython)
$env:MY_CODEX_TOOLING_PYTHON = $env:MY_CODEX_PYTHON
$env:PLUGIN_VALIDATOR = Join-Path $env:CODEX_HOME "skills\.system\plugin-creator\scripts\validate_plugin.py"

$venvPath = Join-Path $env:CODEX_HOME "venvs\my-codex"

Write-Host "MY_CODEX_ROOT=$env:MY_CODEX_ROOT"
Write-Host "CODEX_HOME=$env:CODEX_HOME"
Write-Host "MY_CODEX_PYTHON=$env:MY_CODEX_PYTHON"
Write-Host "MY_CODEX_TOOLING_PYTHON=$env:MY_CODEX_TOOLING_PYTHON"
Write-Host "PLUGIN_VALIDATOR=$env:PLUGIN_VALIDATOR"
Write-Host "BootstrapPython=$BootstrapPython"
if ($CodexPathWasProvided) {
    Write-Host "CodexPath=$CodexPath"
}
else {
    Write-Host "CodexPath=auto-if-required-by-harness"
}
if ($HarnessWasProvided) {
    Write-Host "Harness=$Harness"
}
else {
    Write-Host "Harness=registry-default"
}

$bootstrapArgs = @(
    "scripts\bootstrap_tooling_env.py",
    "--venv", $venvPath
)
if ($DryRun) {
    $bootstrapArgs += "--dry-run"
}
Invoke-Checked `
    -Exe $BootstrapPython `
    -Arguments $bootstrapArgs `
    -Label "my-codex tooling bootstrap"

if (-not (Test-Path -LiteralPath $env:MY_CODEX_PYTHON -PathType Leaf)) {
    if ($DryRun) {
        throw "tooling Python is unavailable after dry-run bootstrap: $env:MY_CODEX_PYTHON. Run the wrapper without -DryRun once to create the tooling environment."
    }
    throw "tooling Python is unavailable after bootstrap: $env:MY_CODEX_PYTHON"
}

$refreshArgs = @(
    "scripts\refresh_my_codex.py",
    "--codex-home", $env:CODEX_HOME,
    "--venv", $venvPath,
    "--python", $env:MY_CODEX_PYTHON,
    "--skip-bootstrap"
)
if ($HarnessWasProvided) {
    $refreshArgs += @("--harness", $Harness)
}
if ($CodexPathWasProvided) {
    $refreshArgs += @("--codex", $CodexPath)
}
if ($GitMarketplaceSource) {
    $refreshArgs += @("--git-marketplace-source", $GitMarketplaceSource)
}
if ($GitRefWasProvided) {
    $refreshArgs += @("--git-ref", $GitRef)
}
if ($DryRun) {
    $refreshArgs += "--dry-run"
}
if ($Yes) {
    $refreshArgs += "--yes"
}

Invoke-Checked `
    -Exe $env:MY_CODEX_PYTHON `
    -Arguments $refreshArgs `
    -Label "my-codex refresh"

if ($DryRun -and -not $SkipCheck) {
    Write-Host "Dry run: skipping closure check because no local state was changed."
}
elseif (-not $SkipCheck) {
    $checkArgs = @(
        "scripts\check_my_codex.py",
        "--codex-home", $env:CODEX_HOME,
        "--venv", $venvPath,
        "--python", $env:MY_CODEX_PYTHON
    )
    if ($HarnessWasProvided) {
        $checkArgs += @("--harness", $Harness)
    }
    if ($CodexPathWasProvided) {
        $checkArgs += @("--codex", $CodexPath)
    }
    Invoke-Checked `
        -Exe $env:MY_CODEX_PYTHON `
        -Arguments $checkArgs `
        -Label "my-codex closure check"
}
