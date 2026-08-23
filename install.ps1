[CmdletBinding()]
param(
    [switch]$MigrateMarketplace,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$InstallerArguments
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

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

$bootstrapPython = if ($env:OH_MY_HARNESS_BOOTSTRAP_PYTHON) {
    $env:OH_MY_HARNESS_BOOTSTRAP_PYTHON
}
elseif (Get-Command python -CommandType Application -ErrorAction SilentlyContinue) {
    "python"
}
elseif (Get-Command py -CommandType Application -ErrorAction SilentlyContinue) {
    "py"
}
else {
    Write-AccentError -Message (
        "error: Bootstrap Python not found. Set OH_MY_HARNESS_BOOTSTRAP_PYTHON or install Python."
    )
    exit 1
}

$installer = Join-Path $PSScriptRoot "scripts\install_oh_my_harness.py"
$forwardedInstallerArguments = @($InstallerArguments)
if ($MigrateMarketplace) {
    $forwardedInstallerArguments += "--migrate-marketplace"
}
try {
    & $bootstrapPython $installer @forwardedInstallerArguments
    $installerExitCode = $LASTEXITCODE
}
catch {
    Write-AccentError -Message (
        "error: failed to start the oh-my-harness installer with '$bootstrapPython': $($_.Exception.Message)"
    )
    exit 1
}
if ($installerExitCode -ne 0) {
    Write-AccentError -Message (
        "error: oh-my-harness installation failed with exit code $installerExitCode; see the error above."
    )
    exit $installerExitCode
}
