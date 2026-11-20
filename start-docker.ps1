# Recover Docker Desktop from stale Windows Unix sockets left after shutdown.
param([switch]$WaitForUbuntu)

$ErrorActionPreference = 'Stop'
$docker = (Get-Command docker.exe -CommandType Application).Source
$localDocker = Join-Path $env:LOCALAPPDATA 'Docker'
$dockerRoot = Join-Path $env:ProgramFiles 'Docker\Docker'

function Test-EngineReady {
    try {
        $server = & $docker --context desktop-linux version --format '{{.Server.Os}}' 2>$null
        return ($LASTEXITCODE -eq 0 -and $server -eq 'linux')
    } catch [System.Management.Automation.RemoteException] {
        return $false
    }
}

function Test-UbuntuEngineReady {
    try {
        $server = & wsl.exe -d Ubuntu --exec docker version --format '{{.Server.Os}}' 2>$null
        return ($LASTEXITCODE -eq 0 -and $server -eq 'linux')
    } catch [System.Management.Automation.RemoteException] {
        return $false
    }
}

$desktopRunning = Get-Process -Name 'Docker Desktop','com.docker.backend' -ErrorAction SilentlyContinue
$wslStatus = (& wsl.exe --list --verbose | Out-String).Replace([string][char]0,'')
if ($LASTEXITCODE -ne 0) { throw 'Could not read WSL status.' }
$stopped = $wslStatus -match '(?im)^\s*\*?\s*docker-desktop\s+(Stopped|\u5DF2\u505C\u6B62)\s+2\s*$'

if ($stopped) {
    if ($desktopRunning) {
        $report = Get-Item -LiteralPath (Join-Path $localDocker 'backend.error.json') -ErrorAction SilentlyContinue
        $ownProcesses = @($desktopRunning | Where-Object {
            $_.Path -and $_.Path.StartsWith($dockerRoot + '\', [StringComparison]::OrdinalIgnoreCase)
        })
        $backend = $ownProcesses | Where-Object ProcessName -eq 'com.docker.backend' |
            Sort-Object StartTime | Select-Object -First 1
        $backendLog = Join-Path $localDocker 'log\host\com.docker.backend.exe.log'
        $failure = Get-Content -LiteralPath $backendLog -Tail 100 -ErrorAction SilentlyContinue |
            Where-Object { $_ -match 'backend crashed, dumping.*initializing (Inference manager|Secrets Engine).*?(dockerInference|engine\.sock)' } |
            Select-Object -Last 1
        if (-not ($backend -and $report -and $report.LastWriteTime -ge $backend.StartTime -and
            $failure)) {
            throw 'Docker Desktop is already starting or has an unrelated error. Left it running.'
        }
        Stop-Process -InputObject $ownProcesses
        Wait-Process -InputObject $ownProcesses -Timeout 10 -ErrorAction SilentlyContinue
    }

    $knownSockets = @(
        (Join-Path $localDocker 'run\dockerInference'),
        (Join-Path $localDocker 'run\userAnalyticsOtlpHttp.sock'),
        (Join-Path $env:LOCALAPPDATA 'docker-secrets-engine\engine.sock')
    )
    $stale = @(
        foreach ($socket in $knownSockets) {
            $parent = Split-Path -LiteralPath $socket
            $entry = Get-ChildItem -LiteralPath $parent -Force -ErrorAction SilentlyContinue |
                Where-Object FullName -eq $socket
            if ($entry -and -not $entry.PSIsContainer -and $entry.Length -eq 0 -and
                ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint)) { $socket }
        }
    )
    if ($stale.Count) {
        $renameSocket = @'
import os
import pathlib
import stat
import subprocess
import sys
import uuid

for windows_path in sys.argv[1:]:
    path = pathlib.Path(subprocess.check_output(["wslpath", "-u", windows_path], text=True).strip())
    if any(parent.is_symlink() for parent in path.parents):
        raise SystemExit(f"Unexpected directory link: {path.parent}")
    try:
        info = path.lstat()
    except FileNotFoundError:
        continue
    if info.st_size or not (stat.S_ISREG(info.st_mode) or stat.S_ISSOCK(info.st_mode)):
        raise SystemExit(f"Unexpected socket type: {path}")
    backup = path.with_name(path.name + ".stale-" + uuid.uuid4().hex[:12])
    os.rename(path, backup)
    print(f"Backed up {path.name} as {backup.name}")
'@
        $renameSocket | & wsl.exe -d Ubuntu --exec python3 - @stale
        if ($LASTEXITCODE -ne 0) { throw 'Could not move a stale Docker socket.' }
        # DrvFS sometimes omits the dedicated Secrets Engine directory even
        # though the Windows directory still contains its AF_UNIX endpoint.
        foreach ($socket in $stale) {
            $parent = Split-Path -LiteralPath $socket
            $entries = @(Get-ChildItem -LiteralPath $parent -Force)
            $left = $entries | Where-Object FullName -eq $socket
            if (-not $left) { continue }
            $secrets = Join-Path $env:LOCALAPPDATA 'docker-secrets-engine'
            $dir = Get-Item -LiteralPath $parent -Force
            if ($dir.FullName -ne $secrets -or -not $dir.PSIsContainer -or
                ($dir.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
                $entries.Count -ne 1 -or $left.Name -ne 'engine.sock' -or
                $left.PSIsContainer -or $left.Length -ne 0 -or
                -not ($left.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
                throw "Windows still sees the endpoint after WSL recovery: $socket"
            }
            $backupName = $dir.Name + '.stale-' + [Guid]::NewGuid().ToString('N')
            Rename-Item -LiteralPath $dir.FullName -NewName $backupName
            Write-Output "Backed up $($dir.Name) including its lone stale endpoint to $backupName"
        }
    }
    & $docker desktop start --detach
    if ($LASTEXITCODE -ne 0) { throw "Docker Desktop could not start (exit $LASTEXITCODE)." }
}

$deadline = (Get-Date).AddSeconds(60)
do {
    $engineReady = Test-EngineReady
    if ($engineReady -and (!$WaitForUbuntu -or (Test-UbuntuEngineReady))) {
        & $docker --context desktop-linux version --format 'Docker engine ready: {{.Server.Os}} {{.Server.Version}}'
        if ($WaitForUbuntu) { 'Ubuntu Docker integration is ready.' }
        return
    }
    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $deadline)
if ($engineReady -and $WaitForUbuntu) {
    throw 'Docker Desktop is running, but Ubuntu cannot reach its engine. Check Docker Desktop WSL Integration.'
}
throw "Docker Desktop did not become ready. See $localDocker\log\host."
