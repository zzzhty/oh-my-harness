# Invoke with: & <harness-root>/.omh-runtime/run.ps1 <group> <script> [args...]
$ErrorActionPreference = 'Stop'
$group = $args[0]
if ($group -cnotmatch '^[A-Za-z0-9_-]+$') { throw 'Invalid runtime group' }
$python = if (Test-Path Env:OMH_PYTHON) { $env:OMH_PYTHON } else { (Get-Content -LiteralPath (Join-Path $PSScriptRoot "$group.python") -Raw -Encoding UTF8).TrimEnd("`r", "`n") }
if ($python -notmatch '^(?:[A-Za-z]:[\\/]|[\\/]{2}[^\\/]+[\\/][^\\/]+[\\/])') { throw 'Prepare a runtime or set an absolute OMH_PYTHON venv interpreter' }
# .NET Framework and modern PowerShell both use the Windows native argv rule.
# ProcessStartInfo avoids PowerShell 5 dropping empty native arguments.
function Quote-NativeArgument([string]$value) {
    return '"' + ([regex]::Replace(([regex]::Replace($value, '(\\*)"', '$1$1\"')), '(\\+)$', '$1$1')) + '"'
}
$forward = @('-I', '-B', (Join-Path $PSScriptRoot 'omh_runtime.py'), 'run', '--binding', (Join-Path $PSScriptRoot "$group.json"), '--') + @($args | Select-Object -Skip 1)
$start = New-Object System.Diagnostics.ProcessStartInfo
$start.FileName = $python
$start.UseShellExecute = $false
$start.Arguments = (($forward | ForEach-Object { Quote-NativeArgument ([string]$_) }) -join ' ')
$process = [System.Diagnostics.Process]::Start($start)
$process.WaitForExit()
exit $process.ExitCode
