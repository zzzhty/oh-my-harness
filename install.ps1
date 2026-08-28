[CmdletBinding()]
param(
    [switch]$MigrateMarketplace,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$InstallerArguments
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$DefaultBootstrapRepository = "https://github.com/zzzhty/oh-my-harness.git"
$DefaultBootstrapRef = "main"

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

function Resolve-BootstrapSource {
    param(
        [string[]]$Arguments
    )

    $repository = $DefaultBootstrapRepository
    $ref = $DefaultBootstrapRef
    for ($index = 0; $index -lt $Arguments.Count; $index++) {
        $argument = $Arguments[$index]
        if ($argument -eq "--repository") {
            if ($index + 1 -ge $Arguments.Count) {
                Write-AccentError -Message "error: --repository requires a value"
                exit 2
            }
            $index++
            $repository = $Arguments[$index]
        }
        elseif ($argument.StartsWith("--repository=")) {
            $repository = $argument.Substring("--repository=".Length)
        }
        elseif ($argument -eq "--ref") {
            if ($index + 1 -ge $Arguments.Count) {
                Write-AccentError -Message "error: --ref requires a value"
                exit 2
            }
            $index++
            $ref = $Arguments[$index]
        }
        elseif ($argument.StartsWith("--ref=")) {
            $ref = $argument.Substring("--ref=".Length)
        }
    }
    if ([string]::IsNullOrWhiteSpace($repository)) {
        Write-AccentError -Message "error: repository source must not be empty"
        exit 2
    }
    if ([string]::IsNullOrWhiteSpace($ref)) {
        Write-AccentError -Message "error: Git ref must not be empty"
        exit 2
    }
    [PSCustomObject]@{
        Repository = $repository
        Ref = $ref
    }
}

function Remove-BootstrapRoot {
    param(
        [AllowNull()]
        [string]$Path
    )

    if ($Path -and (Test-Path -LiteralPath $Path)) {
        Remove-Item -LiteralPath $Path -Recurse -Force
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

$forwardedInstallerArguments = @($InstallerArguments)
if ($MigrateMarketplace) {
    $forwardedInstallerArguments += "--migrate-marketplace"
}

$installer = $null
if ($PSScriptRoot) {
    $localInstaller = Join-Path $PSScriptRoot "scripts\install_oh_my_harness.py"
    if (Test-Path -LiteralPath $localInstaller -PathType Leaf) {
        $installer = $localInstaller
    }
}

$bootstrapRoot = $null
if (-not $installer) {
    $git = Get-Command git -CommandType Application -ErrorAction SilentlyContinue
    if (-not $git) {
        Write-AccentError -Message (
            "error: Git not found. Install Git before running the streamed installer."
        )
        exit 1
    }
    $bootstrapSource = Resolve-BootstrapSource -Arguments $forwardedInstallerArguments
    $bootstrapRoot = Join-Path (
        [System.IO.Path]::GetTempPath()
    ) ("oh-my-harness-install-" + [Guid]::NewGuid().ToString("N"))
    $bootstrapCheckout = Join-Path $bootstrapRoot "repo"
    New-Item -ItemType Directory -Path $bootstrapRoot | Out-Null
    try {
        & $git.Source clone `
            --depth 1 `
            --branch $bootstrapSource.Ref `
            --single-branch `
            -- `
            $bootstrapSource.Repository `
            $bootstrapCheckout
        $cloneExitCode = $LASTEXITCODE
    }
    catch {
        try {
            Remove-BootstrapRoot -Path $bootstrapRoot
        }
        catch {
            Write-AccentError -Message (
                "error: failed to clean bootstrap checkout '$bootstrapRoot': $($_.Exception.Message)"
            )
        }
        Write-AccentError -Message (
            "error: failed to start Git bootstrap clone: $($_.Exception.Message)"
        )
        exit 1
    }
    if ($cloneExitCode -ne 0) {
        Remove-BootstrapRoot -Path $bootstrapRoot
        Write-AccentError -Message (
            "error: Git bootstrap clone failed with exit code $cloneExitCode; see the error above."
        )
        exit $cloneExitCode
    }
    $installer = Join-Path $bootstrapCheckout "scripts\install_oh_my_harness.py"
    if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) {
        Remove-BootstrapRoot -Path $bootstrapRoot
        Write-AccentError -Message (
            "error: cloned bootstrap source has no scripts\install_oh_my_harness.py"
        )
        exit 1
    }
}

$installerExitCode = 0
$startFailure = $null
try {
    & $bootstrapPython $installer @forwardedInstallerArguments
    $installerExitCode = $LASTEXITCODE
}
catch {
    $startFailure = $_.Exception.Message
    $installerExitCode = 1
}

$cleanupFailure = $null
if ($bootstrapRoot) {
    try {
        Remove-BootstrapRoot -Path $bootstrapRoot
    }
    catch {
        $cleanupFailure = $_.Exception.Message
        if ($installerExitCode -eq 0) {
            $installerExitCode = 1
        }
    }
}

if ($startFailure) {
    Write-AccentError -Message (
        "error: failed to start the oh-my-harness installer with '$bootstrapPython': $startFailure"
    )
}
if ($cleanupFailure) {
    Write-AccentError -Message (
        "error: failed to clean bootstrap checkout '$bootstrapRoot': $cleanupFailure"
    )
}
if ($installerExitCode -ne 0) {
    Write-AccentError -Message (
        "error: oh-my-harness installation failed with exit code $installerExitCode; see the error above."
    )
    exit $installerExitCode
}
