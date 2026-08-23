[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$InstallerArguments
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

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
    throw "Bootstrap Python not found. Set OH_MY_HARNESS_BOOTSTRAP_PYTHON or install Python."
}

$installer = Join-Path $PSScriptRoot "scripts\install_oh_my_harness.py"
& $bootstrapPython $installer @InstallerArguments
if ($LASTEXITCODE -ne 0) {
    throw "oh-my-harness installer failed with exit code $LASTEXITCODE"
}
