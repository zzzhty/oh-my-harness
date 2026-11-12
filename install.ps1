# OMH bootstrap installer (ADR 0036). Windows PowerShell 5.1 and PowerShell 7; stateless.
#
#   irm https://raw.githubusercontent.com/zzzhty/oh-my-harness/main/install.ps1 -OutFile $env:TEMP\omh-install.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File $env:TEMP\omh-install.ps1
#
# Environment (the same contract as install.sh):
#   OMH_VERSION   tag to install or upgrade to (default: latest release)
#   OMH_HARNESS   comma-separated harness list for a fresh bootstrap (default: codex)
#   OMH_HOME      manager home (default: the user profile's .oh-my-harness); the clone lands at <home>/repo
#   OMH_REPO      repository URL or local path (default: the GitHub repository)
#   OMH_REF_URL   verification asset URL or local file path (default: the release's omh-<tag>.ref asset)
#   OMH_PYTHON    absolute bootstrap interpreter override
#
# The script acquires and verifies the source tree, then delegates every
# target mutation to the standalone CLI. It keeps no state and exits.
$ErrorActionPreference = 'Stop'
# Git for Windows opens a credential prompt when a fetch cannot authenticate
# and would hang a non-interactive upgrade. Verified tags never need it.
$env:GIT_TERMINAL_PROMPT = '0'
$env:GCM_INTERACTIVE = 'Never'

trap {
    [Console]::Error.WriteLine("install.ps1: $($_.Exception.Message)")
    exit 1
}

function log([string]$Message) {
    [Console]::Error.WriteLine("install.ps1: $Message")
}
function die([string]$Message) {
    [Console]::Error.WriteLine("install.ps1: $Message")
    exit 1
}

# Same Windows argv quoting as plugins/workflow/scripts/run.ps1. Start-Process
# receives one pre-quoted string so PowerShell 5.1 does not split on spaces.
function Quote-NativeArgument([string]$value) {
    if ($null -eq $value) { $value = '' }
    return '"' + ([regex]::Replace(([regex]::Replace($value, '(\\*)"', '$1$1\"')), '(\\+)$', '$1$1')) + '"'
}

function Read-Captured([string]$Path) {
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -eq 0) { return '' }
    if ($bytes.Length -ge 2 -and $bytes[0] -eq 255 -and $bytes[1] -eq 254) {
        return [System.Text.Encoding]::Unicode.GetString($bytes, 2, $bytes.Length - 2)
    }
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191) {
        $utf8 = New-Object System.Text.UTF8Encoding $false
        return $utf8.GetString($bytes, 3, $bytes.Length - 3)
    }
    # PowerShell 5.1 redirection is UTF-16 LE without a BOM: ASCII then has a
    # NUL in every other byte. UTF-8 payloads from git and Python do not.
    $sample = [Math]::Min($bytes.Length, 64)
    $nuls = 0
    for ($i = 0; $i -lt $sample; $i++) { if ($bytes[$i] -eq 0) { $nuls++ } }
    if ($nuls -gt 0 -and $nuls * 2 -ge $sample) {
        return [System.Text.Encoding]::Unicode.GetString($bytes)
    }
    $utf8 = New-Object System.Text.UTF8Encoding $false
    return $utf8.GetString($bytes)
}

function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)][string]$File,
        [string[]]$ArgumentList = @(),
        [string]$WorkingDirectory
    )
    $outFile = [System.IO.Path]::GetTempFileName()
    $errFile = [System.IO.Path]::GetTempFileName()
    try {
        $params = @{
            FilePath = $File
            Wait = $true
            PassThru = $true
            RedirectStandardOutput = $outFile
            RedirectStandardError = $errFile
        }
        # Windows PowerShell 5.1 rejects -NoNewWindow together with redirection.
        if ($PSVersionTable.PSVersion.Major -ge 6) { $params.NoNewWindow = $true }
        if ($WorkingDirectory) { $params.WorkingDirectory = $WorkingDirectory }
        if (@($ArgumentList).Count -gt 0) {
            $quoted = @(foreach ($argument in @($ArgumentList)) { Quote-NativeArgument ([string]$argument) })
            $params.ArgumentList = ($quoted -join ' ')
        }
        $proc = Start-Process @params
        return [pscustomobject]@{
            Code = [int]$proc.ExitCode
            Out = (Read-Captured $outFile)
            Err = (Read-Captured $errFile)
        }
    } finally {
        Remove-Item -LiteralPath $outFile, $errFile -Force -ErrorAction SilentlyContinue
    }
}

function Resolve-CommandPath([string]$Name) {
    if (-not $Name) { return $null }
    if ([System.IO.Path]::IsPathRooted($Name)) {
        if (Test-Path -LiteralPath $Name -PathType Leaf) {
            return (Resolve-Path -LiteralPath $Name).Path
        }
        return $null
    }
    $cmd = Get-Command -Name $Name -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.CommandType -eq 'Application' -and $cmd.Source) { return $cmd.Source }
    return $null
}

function Require-Tool([string[]]$Names, [string]$Label) {
    foreach ($name in $Names) {
        $resolved = Resolve-CommandPath $name
        if ($resolved) { return $resolved }
    }
    die "$Label is required"
}

$repoDefault = 'https://github.com/zzzhty/oh-my-harness'
$repo = if ($env:OMH_REPO) { $env:OMH_REPO } else { $repoDefault }
if ($env:OMH_HOME) {
    $homeDir = $env:OMH_HOME
} elseif ($env:USERPROFILE) {
    # Python's Path.home() on Windows is USERPROFILE, not HOME.
    $homeDir = Join-Path $env:USERPROFILE '.oh-my-harness'
} elseif ($env:HOME) {
    $homeDir = Join-Path $env:HOME '.oh-my-harness'
} else {
    die 'OMH_HOME is required when USERPROFILE and HOME are unset'
}
$clone = Join-Path $homeDir 'repo'

$git = Require-Tool @('git.exe', 'git') 'git'
$curl = Require-Tool @('curl.exe', 'curl') 'curl'

function Require-CleanTree {
    # checkout can retain edits, including at the same tag. Ignored files can
    # also enter the distributor's file walk, so they are not exempt.
    $state = Invoke-Native -File $git -ArgumentList @(
        '-C', $clone, 'status', '--porcelain', '--untracked-files=all', '--ignored')
    if ($state.Err) { [Console]::Error.Write($state.Err) }
    if ($state.Code -ne 0) { die "cannot inspect $clone; leaving the checkout unchanged" }
    if ($state.Out.Trim()) {
        die "$clone has local changes or untracked files (including ignored files); preserve or move them outside the clone before retrying"
    }
}
# Refuse before fetching or running any code from an existing managed clone.
if (Test-Path -LiteralPath (Join-Path $clone '.git') -PathType Container) { Require-CleanTree }

# --- interpreter: >= 3.11 and able to seed a usable venv --------------------
# Same strategy selection as the runtime (ADR 0037): private copies first,
# symlinked seeding as the verified fallback for relocated builds (uv-managed
# CPython). Never a silently broken environment.
if ($env:OMH_PYTHON) {
    $python = Resolve-CommandPath $env:OMH_PYTHON
    if (-not $python) { die "cannot resolve an absolute path for $($env:OMH_PYTHON)" }
} else {
    $python = $null
    foreach ($name in @('python3', 'python', 'py')) {
        $python = Resolve-CommandPath $name
        if ($python) { break }
    }
    if (-not $python) { die 'Python 3.11 or newer is required' }
}
$version = Invoke-Native -File $python -ArgumentList @('-c', 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)')
if ($version.Code -ne 0) { die "$python is older than Python 3.11" }

$probe = Join-Path ([System.IO.Path]::GetTempPath()) ('omh-venv-probe-' + [guid]::NewGuid().ToString('n'))
[void][System.IO.Directory]::CreateDirectory($probe)
$seeded = $false
$venvErr = ''
$windows = [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT
try {
    foreach ($strategy in @('--copies', '--symlinks')) {
        $venv = Join-Path $probe 'venv'
        if (Test-Path -LiteralPath $venv) { Remove-Item -LiteralPath $venv -Recurse -Force }
        $result = Invoke-Native -File $python -ArgumentList @('-I', '-B', '-m', 'venv', $strategy, '--without-pip', $venv)
        if ($windows) {
            $venvPython = Join-Path (Join-Path $venv 'Scripts') 'python.exe'
        } else {
            $venvPython = Join-Path (Join-Path $venv 'bin') 'python'
        }
        $importOk = $false
        if ($result.Code -eq 0 -and (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
            $import = Invoke-Native -File $venvPython -ArgumentList @('-c', 'import json')
            if ($import.Code -eq 0) { $importOk = $true }
        }
        if ($importOk) { $seeded = $true; break }
        $venvErr = [string]$result.Err
    }
} finally {
    if (Test-Path -LiteralPath $probe) {
        Remove-Item -LiteralPath $probe -Recurse -Force -ErrorAction SilentlyContinue
    }
}
if (-not $seeded) {
    if ($venvErr) {
        $lines = @($venvErr -split "`r?`n" | Where-Object { $_ -ne '' })
        $tail = @($lines | Select-Object -Last 5) -join "`n"
        if ($tail) { [Console]::Error.WriteLine($tail) }
    }
    die "$python cannot seed a usable venv (private copies and symlinks both failed); set OMH_PYTHON to a standard interpreter"
}

# --- release ----------------------------------------------------------------
$prefix = 'https://github.com/'
$api = $null
if ($repo.StartsWith($prefix)) { $api = $repo.Substring($prefix.Length) }
$tag = $env:OMH_VERSION
if (-not $tag) {
    if (-not $api) { die 'OMH_VERSION is required when OMH_REPO is not a GitHub URL' }
    $latest = Invoke-Native -File $curl -ArgumentList @('-fsSL', "https://api.github.com/repos/$api/releases/latest")
    if ($latest.Err) { [Console]::Error.Write($latest.Err) }
    $tag = $null
    if ($latest.Code -eq 0 -and $latest.Out) {
        try { $tag = (ConvertFrom-Json -InputObject $latest.Out).tag_name } catch { $tag = $null }
    }
    if (-not $tag) { die 'could not resolve the latest release tag' }
}
log "release: $tag"

# --- verification: pin the tag to the release ref asset ---------------------
$refUrl = $env:OMH_REF_URL
if (-not $refUrl) {
    if (-not $api) { die 'OMH_REF_URL is required when OMH_REPO is not a GitHub URL' }
    $refUrl = "https://github.com/$api/releases/download/$tag/omh-$tag.ref"
}
if ($refUrl -match '://') {
    $ref = Invoke-Native -File $curl -ArgumentList @('-fsSL', $refUrl)
    if ($ref.Err) { [Console]::Error.Write($ref.Err) }
    if ($ref.Code -ne 0) { die "ref asset not found: $refUrl" }
    $pinnedRaw = $ref.Out
} else {
    if (-not (Test-Path -LiteralPath $refUrl -PathType Leaf)) { die "ref asset not found: $refUrl" }
    $pinnedRaw = [System.IO.File]::ReadAllText($refUrl)
}
$pinned = [regex]::Replace([string]$pinnedRaw, '\s', '')
if ($pinned.Length -lt 40) { die "the ref asset does not hold a commit SHA: $refUrl" }
# Peeled (^{}) advertisement exists for annotated tags only; a lightweight
# tag's plain ref already points at the commit. Both yield a commit SHA.
function Resolve-TagSha([string]$Suffix) {
    $result = Invoke-Native -File $git -ArgumentList @('ls-remote', $repo, ('refs/tags/' + $tag + $Suffix))
    if ($result.Err) { [Console]::Error.Write($result.Err) }
    if ($result.Code -ne 0) { die "tag $tag was not found in $repo" }
    foreach ($candidate in ($result.Out -split "`r?`n")) {
        if ($candidate) { return (($candidate -split '\s+', 2)[0].Trim()) }
    }
    return ''
}
$resolved = Resolve-TagSha '^{}'
if (-not $resolved) { $resolved = Resolve-TagSha '' }
if (-not $resolved) { die "tag $tag was not found in $repo" }
if ($resolved -ne $pinned) { die "tag $tag resolves to $resolved but the release pins $pinned" }

# --- acquire: bootstrap clone or in-place upgrade ---------------------------
function Head-Of([string]$Directory) {
    $result = Invoke-Native -File $git -ArgumentList @('-C', $Directory, 'rev-parse', 'HEAD')
    if ($result.Err) { [Console]::Error.Write($result.Err) }
    if ($result.Code -ne 0) { return '' }
    return $result.Out.Trim()
}
if ((Test-Path -LiteralPath $clone) -and -not (Test-Path -LiteralPath (Join-Path $clone '.git') -PathType Container)) {
    die "$clone exists and is not a git clone"
}
$mode = 'upgrade'
if (Test-Path -LiteralPath (Join-Path $clone '.git') -PathType Container) {
    log "upgrading $clone"
    $fetch = Invoke-Native -File $git -ArgumentList @('-C', $clone, 'fetch', '--tags', '--force', 'origin')
    if ($fetch.Out) { [Console]::Out.Write($fetch.Out) }
    if ($fetch.Err) { [Console]::Error.Write($fetch.Err) }
    if ($fetch.Code -ne 0) { die 'git fetch failed' }
} else {
    $mode = 'bootstrap'
    log "cloning $repo into $clone"
    $staging = Join-Path $homeDir ('.repo.clone.' + $PID)
    if (Test-Path -LiteralPath $staging) { Remove-Item -LiteralPath $staging -Recurse -Force }
    [void][System.IO.Directory]::CreateDirectory($homeDir)
    # autocrlf=false keeps the checkout byte-for-byte. Git for Windows
    # defaults to true, which would smudge a clean tree and fail closed.
    $cloned = Invoke-Native -File $git -ArgumentList @(
        '-c', 'advice.detachedHead=false', '-c', 'core.autocrlf=false',
        'clone', '--quiet', '--branch', $tag, $repo, $staging)
    if ($cloned.Out) { [Console]::Out.Write($cloned.Out) }
    if ($cloned.Err) { [Console]::Error.Write($cloned.Err) }
    if ($cloned.Code -ne 0) {
        if (Test-Path -LiteralPath $staging) { Remove-Item -LiteralPath $staging -Recurse -Force }
        die 'git clone failed'
    }
    $got = Head-Of $staging
    if ($got -ne $pinned) {
        if (Test-Path -LiteralPath $staging) { Remove-Item -LiteralPath $staging -Recurse -Force }
        die "clone HEAD $got does not match the pinned $pinned"
    }
    Move-Item -LiteralPath $staging -Destination $clone
}
$checked = Invoke-Native -File $git -ArgumentList @(
    '-C', $clone, '-c', 'advice.detachedHead=false', '-c', 'core.autocrlf=false',
    'checkout', '--quiet', ('refs/tags/' + $tag))
if ($checked.Out) { [Console]::Out.Write($checked.Out) }
if ($checked.Err) { [Console]::Error.Write($checked.Err) }
if ($checked.Code -ne 0) { die "checkout $tag failed (a dirty clone fails closed)" }
$got = Head-Of $clone
if ($got -ne $pinned) { die "checkout HEAD $got does not match the pinned $pinned" }
Require-CleanTree

# --- delegate to the standalone CLI -----------------------------------------
# Match install.sh: preserve every indexed target, and pass each path as one
# native argument rather than flattening the index into harness names.
$targetCode = @'
import json, subprocess, sys
from pathlib import Path

sys.stderr.reconfigure(encoding='utf-8')
clone, home, mode, harness_list = sys.argv[1:]
index = Path(home) / 'targets.json'
try:
    targets = json.loads(index.read_bytes()) if mode == 'upgrade' and index.exists() else {}
    if not isinstance(targets, dict):
        raise ValueError('expected an object')
    selected = []
    for entry in targets.values():
        if (not isinstance(entry, dict)
                or not isinstance(entry.get('harness'), str) or not entry['harness']
                or not isinstance(entry.get('skillsRoot'), str) or not entry['skillsRoot']
                or not Path(entry['skillsRoot']).is_absolute()):
            raise ValueError('expected harness and absolute skillsRoot for every target')
        selected.append((entry['harness'], entry['skillsRoot']))
except (OSError, ValueError) as error:
    sys.exit(f'cannot read target index {index}: {error}')
if not selected:
    selected = [(harness, None) for harness in harness_list.split(',') if harness]
verb = 'install' if mode == 'bootstrap' else 'refresh'
for harness, skills_root in selected:
    print(f'{verb} target: {harness}' + (f' at {skills_root}' if skills_root else ''), file=sys.stderr)
    command = [sys.executable, '-B', '-m', 'omh', verb, '--home', home,
               '--harness', harness, '--python', sys.executable]
    if skills_root is not None:
        command += ['--skills-root', skills_root]
    result = subprocess.run(command, cwd=clone)
    if result.returncode:
        sys.exit(result.returncode)
'@
$harnessList = if ($env:OMH_HARNESS) { $env:OMH_HARNESS } else { 'codex' }
$ran = Invoke-Native -File $python -ArgumentList @(
    '-B', '-c', $targetCode, $clone, $homeDir, $mode, $harnessList)
if ($ran.Out) { [Console]::Out.Write($ran.Out) }
if ($ran.Err) { [Console]::Error.Write($ran.Err) }
if ($ran.Code -ne 0) { die 'target installation failed' }

log "done: $tag at $clone"
$status = Invoke-Native -File $python -WorkingDirectory $clone -ArgumentList @('-B', '-m', 'omh', 'status', '--home', $homeDir)
if ($status.Out) { [Console]::Out.Write($status.Out) }
if ($status.Err) { [Console]::Error.Write($status.Err) }
exit 0
