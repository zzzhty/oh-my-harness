[CmdletBinding()]
param(
    [string]$Harness,
    [string]$ManagerHome,
    [string]$BootstrapPython,
    [string]$CodexPath,
    [string]$CodexHome,
    [string]$ToolingPython,
    [string]$GitMarketplaceSource,
    [string]$GitRef = "main",
    [string]$MigrateFromRepo,
    [switch]$MigrateMarketplace,
    [switch]$Yes,
    [switch]$DryRun,
    [switch]$SkipCheck,
    [Alias("h")]
    [switch]$Help
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Show-Usage {
    @'
Usage: omh [-Harness ID] [options]

Refresh and verify one registry-selected oh-my-harness distribution.

Options:
  -Harness ID                  Registry harness id. Defaults to the registry value (currently codex).
  -ManagerHome PATH            Manager home. Defaults to OH_MY_HARNESS_HOME or ~/.oh-my-harness.
  -BootstrapPython PATH        Base Python used to create or refresh the tooling venv.
  -CodexPath PATH              Explicit Codex CLI executable. Otherwise uses CODEX_BIN, PATH, then managed installs.
  -CodexHome PATH              Codex home directory. Defaults to CODEX_HOME or ~/.codex.
  -ToolingPython PATH          Tooling Python used for harness helpers and Codex hooks.
  -GitMarketplaceSource URL    Git marketplace source. Defaults to remote.origin.url.
  -GitRef REF                  Git ref for first-time Git marketplace add. Defaults to main.
  -MigrateMarketplace          Apply the registry-owned retired Codex marketplace migration.
  -MigrateFromRepo PATH        Replace the exact former managed Codex AGENTS.md symlink after live confirmation.
  -Yes                         Confirm missing instructions creation and exact managed-stale prune plans.
  -DryRun                      Print commands without changing Codex state.
  -SkipCheck                   Skip the final closure check.
  -Help, -h                    Show this help without bootstrapping or refreshing.
'@ | Write-Output
}

if ($Help) {
    Show-Usage
    exit 0
}

$HarnessWasProvided = $PSBoundParameters.ContainsKey("Harness")
$CodexPathWasProvided = $PSBoundParameters.ContainsKey("CodexPath")
$GitRefWasProvided = $PSBoundParameters.ContainsKey("GitRef")

function Write-AccentError {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    if ((Test-Path Env:NO_COLOR) -or [Console]::IsErrorRedirected) {
        [Console]::Error.WriteLine($Message)
        return
    }
    $previousColor = [Console]::ForegroundColor
    try {
        [Console]::ForegroundColor = [ConsoleColor]::Red
        [Console]::Error.WriteLine($Message)
    }
    finally {
        [Console]::ForegroundColor = $previousColor
    }
}

function Stop-Upgrade {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,

        [int]$ExitCode = 1
    )

    Write-AccentError -Message "error: $Message"
    exit $ExitCode
}

trap {
    Stop-Upgrade `
        -Message "unexpected PowerShell failure: $($_.Exception.Message)" `
        -ExitCode 1
}

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

    Stop-Upgrade `
        -Message "$Label not found. Checked:$([Environment]::NewLine)$($checked -join [Environment]::NewLine)" `
        -ExitCode 1
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
            $env:OH_MY_HARNESS_BOOTSTRAP_PYTHON,
            "python",
            "py",
            (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"),
            (Join-Path $env:USERPROFILE ".oh-my-harness\venv\Scripts\python.exe")
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
    try {
        & $Exe @Arguments
        $commandExitCode = $LASTEXITCODE
    }
    catch {
        Stop-Upgrade `
            -Message "$Label could not start '$Exe': $($_.Exception.Message)" `
            -ExitCode 1
    }
    if ($commandExitCode -ne 0) {
        Stop-Upgrade `
            -Message "$Label failed with exit code $commandExitCode; see the preceding diagnostic." `
            -ExitCode $commandExitCode
    }
}

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $repoRoot

$env:OH_MY_HARNESS_ROOT = $repoRoot
if (-not $ManagerHome) {
    if ($env:OH_MY_HARNESS_HOME) {
        $ManagerHome = $env:OH_MY_HARNESS_HOME
    }
    else {
        $ManagerHome = Join-Path $env:USERPROFILE ".oh-my-harness"
    }
}
if (-not [System.IO.Path]::IsPathRooted($ManagerHome)) {
    Stop-Upgrade -Message "Manager home must be an absolute path: $ManagerHome" -ExitCode 1
}
$env:OH_MY_HARNESS_HOME = [System.IO.Path]::GetFullPath($ManagerHome)
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
    $ToolingPython = Join-Path $env:OH_MY_HARNESS_HOME "venv\Scripts\python.exe"
}
$env:OH_MY_HARNESS_PYTHON = [System.IO.Path]::GetFullPath($ToolingPython)
$env:OH_MY_HARNESS_TOOLING_PYTHON = $env:OH_MY_HARNESS_PYTHON
$env:PLUGIN_VALIDATOR = Join-Path $env:CODEX_HOME "skills\.system\plugin-creator\scripts\validate_plugin.py"

$venvPath = Join-Path $env:OH_MY_HARNESS_HOME "venv"

Write-Host "OH_MY_HARNESS_HOME=$env:OH_MY_HARNESS_HOME"
Write-Host "OH_MY_HARNESS_ROOT=$env:OH_MY_HARNESS_ROOT"
Write-Host "CODEX_HOME=$env:CODEX_HOME"
Write-Host "OH_MY_HARNESS_PYTHON=$env:OH_MY_HARNESS_PYTHON"
Write-Host "OH_MY_HARNESS_TOOLING_PYTHON=$env:OH_MY_HARNESS_TOOLING_PYTHON"
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
    -Label "oh-my-harness tooling bootstrap"

if (-not (Test-Path -LiteralPath $env:OH_MY_HARNESS_PYTHON -PathType Leaf)) {
    if ($DryRun) {
        Stop-Upgrade `
            -Message "tooling Python is unavailable after dry-run bootstrap: $env:OH_MY_HARNESS_PYTHON. Run the wrapper without -DryRun once to create the tooling environment." `
            -ExitCode 1
    }
    Stop-Upgrade `
        -Message "tooling Python is unavailable after bootstrap: $env:OH_MY_HARNESS_PYTHON" `
        -ExitCode 1
}

$refreshArgs = @(
    "scripts\refresh_harness.py",
    "--home", $env:OH_MY_HARNESS_HOME,
    "--codex-home", $env:CODEX_HOME,
    "--venv", $venvPath,
    "--python", $env:OH_MY_HARNESS_PYTHON,
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
if ($MigrateMarketplace) {
    $refreshArgs += "--migrate-marketplace"
}
if ($MigrateFromRepo) {
    $refreshArgs += @("--migrate-from-repo", $MigrateFromRepo)
}

Invoke-Checked `
    -Exe $env:OH_MY_HARNESS_PYTHON `
    -Arguments $refreshArgs `
    -Label "oh-my-harness refresh"

if ($DryRun -and -not $SkipCheck) {
    Write-Host "Dry run: skipping closure check because no local state was changed."
}
elseif (-not $SkipCheck) {
    $checkArgs = @(
        "scripts\check_harness.py",
        "--home", $env:OH_MY_HARNESS_HOME,
        "--codex-home", $env:CODEX_HOME,
        "--venv", $venvPath,
        "--python", $env:OH_MY_HARNESS_PYTHON
    )
    if ($HarnessWasProvided) {
        $checkArgs += @("--harness", $Harness)
    }
    if ($CodexPathWasProvided) {
        $checkArgs += @("--codex", $CodexPath)
    }
    Invoke-Checked `
        -Exe $env:OH_MY_HARNESS_PYTHON `
        -Arguments $checkArgs `
        -Label "oh-my-harness closure check"
}
