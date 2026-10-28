# Launch from normal Windows PowerShell with Docker access.
[CmdletBinding()]
param([string]$Container = 'nyu-project', [switch]$SkipPostgres, [string]$ResumeRun)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$runId = [guid]::NewGuid().ToString('N').Substring(0, 12)
$reports = Join-Path $repo ".test-tmp\kubernetes-$runId"
$workRoot = "/home/vscode/.cache/orders-sprint2-$runId"
$dockerLog = Join-Path $reports 'docker.log'
New-Item -ItemType Directory -Path $reports -Force | Out-Null
function Invoke-Docker {
    param([string[]]$DockerArgs, [string]$InputText, [switch]$CaptureOutput)
    "Docker step: $($DockerArgs -join ' ')" | Tee-Object -FilePath $dockerLog -Append | Out-Host
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        if ($CaptureOutput) {
            $output = $InputText | & docker @DockerArgs 2>&1 | ForEach-Object { $_.ToString() }
        } elseif ($PSBoundParameters.ContainsKey('InputText')) {
            $InputText | & docker @DockerArgs 2>&1 | ForEach-Object { $_.ToString() } | Tee-Object -FilePath $dockerLog -Append | Out-Host
        } else {
            & docker @DockerArgs 2>&1 | ForEach-Object { $_.ToString() } | Tee-Object -FilePath $dockerLog -Append | Out-Host
        }
        $exitCode = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previousPreference }
    if ($exitCode -ne 0) {
        if ($CaptureOutput) { $output | Tee-Object -FilePath $dockerLog -Append | Out-Host }
        throw "Docker $($DockerArgs[0]) failed (exit $exitCode); see $dockerLog."
    }
    if ($CaptureOutput) { return $output }
}
function New-Snapshot-Input {
    param([string]$SourceRoot, [string]$Destination)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $records = @(foreach ($entry in @('Makefile','Dockerfile','.dockerignore','Pipfile','Pipfile.lock','wsgi.py','service','k8s','config','scripts')) {
            $item = Get-Item -LiteralPath (Join-Path $SourceRoot $entry)
            if ($item.PSIsContainer) { $files = Get-ChildItem -LiteralPath $item.FullName -Recurse -File }
            else { $files = @($item) }
            foreach ($file in $files) {
                if ($file.FullName -match '\\__pycache__\\' -or $file.Extension -eq '.pyc') { continue }
                $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
                [pscustomobject]@{
                    path = $file.FullName.Substring($SourceRoot.Length + 1).Replace('\','/')
                    content = [Convert]::ToBase64String($bytes)
                    sha256 = ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()
                }
            }
        })
    } finally { $sha.Dispose() }
    $json = ConvertTo-Json -InputObject $records -Depth 4 -Compress
    $payload64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($json))
    $destination64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($Destination))
    $header = "payload64='$payload64'" + [char]10 + "destination64='$destination64'" + [char]10
    $body = @'
import base64, hashlib, json
from pathlib import Path, PurePosixPath
root = Path(base64.b64decode(destination64).decode('utf-8'))
root.mkdir(parents=True, exist_ok=False)
records = json.loads(base64.b64decode(payload64))
for record in records:
    relative = PurePosixPath(record['path'])
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Invalid snapshot path')
    content = base64.b64decode(record['content'], validate=True)
    if hashlib.sha256(content).hexdigest() != record['sha256']:
        raise ValueError('Snapshot checksum mismatch')
    target = root.joinpath(*relative.parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
print(f'PASS: transferred and checksum-verified {len(records)} snapshot files', flush=True)
'@
    return $header + $body + [char]10
}
function New-Report-Input {
    param([string]$Root)
    $root64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($Root))
    $header = "root64='$root64'" + [char]10
    $body = @'
import base64, json
from pathlib import Path
root = Path(base64.b64decode(root64).decode('utf-8')) / '.test-tmp' / 'kubernetes'
records = []
for name in ('verification.log','resources.txt','available-replicas.txt','orders-state.json','connection.txt','registries.yaml'):
    path = root / name
    if path.is_file():
        records.append({'path': name, 'content': base64.b64encode(path.read_bytes()).decode('ascii')})
print(json.dumps(records))
'@
    return $header + $body + [char]10
}
Invoke-Docker -DockerArgs @('info','--format','{{.ServerVersion}}')
$running = & docker inspect --format '{{.State.Running}}' $Container
if ($LASTEXITCODE -ne 0) { throw "Development container '$Container' was not found; open the project in VS Code Dev Containers or pass -Container NAME." }
if ($running.Trim() -ne 'true') { Invoke-Docker -DockerArgs @('start',$Container) }
Invoke-Docker -DockerArgs @('exec',$Container,'id')
Invoke-Docker -DockerArgs @('exec',$Container,'python3','--version')
Invoke-Docker -DockerArgs @('exec',$Container,'test','-w','/home/vscode')
$resume = $null
if ($ResumeRun) {
    if ($ResumeRun -notmatch '^[a-f0-9]{12}$') { throw 'Invalid resume run ID' }
    $oldReports = Join-Path $repo ".test-tmp\kubernetes-$ResumeRun"
    $log = [System.IO.File]::ReadAllText((Join-Path $oldReports 'verification.log'))
    $registryYaml = [System.IO.File]::ReadAllText((Join-Path $oldReports 'registries.yaml'))
    $clusterMatch = [regex]::Match($log, 'Creating an isolated K3s cluster: (orders-s2-[a-f0-9]{10})')
    $ingressMatch = [regex]::Match($log, "portmapping '127\.0\.0\.1:([0-9]+):80'")
    $portMatch = [regex]::Match($registryYaml, 'localhost:([0-9]+)')
    $registryMatch = [regex]::Match($log, "Successfully created registry '((?:k3d-)?orders-s2-[a-f0-9]{10}-registry)'")
    if (-not $clusterMatch.Success -or -not $ingressMatch.Success -or -not $portMatch.Success -or -not $registryMatch.Success) {
        throw 'Prior run metadata could not be verified; use a fresh run instead.'
    }
    $resume = [ordered]@{
        cluster = $clusterMatch.Groups[1].Value
        registry_name = $registryMatch.Groups[1].Value
        registry_port = [int]$portMatch.Groups[1].Value
        ingress_port = [int]$ingressMatch.Groups[1].Value
        source_root = "/home/vscode/.cache/orders-sprint2-$ResumeRun"
    }
    Write-Host "Resuming only the owned verification cluster: $($resume.cluster)"
}
if (-not $SkipPostgres -and -not $ResumeRun) { & (Join-Path $PSScriptRoot 'verify-postgres.ps1') }
Start-Transcript -Path (Join-Path $reports 'launcher.log') | Out-Null
$copied = $false
try {
    Write-Host "Preparing an isolated code snapshot in existing container: $Container"
    $program = New-Snapshot-Input -SourceRoot $repo -Destination $workRoot
    if ($resume) {
        $resume64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((ConvertTo-Json -InputObject $resume -Compress)))
        $program += [char]10 + "(root / '.resume.json').write_bytes(base64.b64decode('$resume64'))" + [char]10
    }
    Invoke-Docker -DockerArgs @('exec','-i',$Container,'python3','-') -InputText $program
    $copied = $true
    Invoke-Docker -DockerArgs @('exec',$Container,'bash',"$workRoot/scripts/verify-kubernetes.sh")
    Write-Host 'PASS: Kubernetes acceptance checks completed.'
} catch {
    $failure = $_
    Write-Host "Launcher failed: $($failure.Exception.Message)"
    try {
        Invoke-Docker -DockerArgs @('inspect','--format','{{json .State}}',$Container)
        Invoke-Docker -DockerArgs @('logs','--tail','100',$Container)
    } catch { Write-Host "Additional diagnostics unavailable: $($_.Exception.Message)" }
    throw $failure
} finally {
    if ($copied) {
        try {
            $program = New-Report-Input -Root $workRoot
            $json = Invoke-Docker -DockerArgs @('exec','-i',$Container,'python3','-') -InputText $program -CaptureOutput
            $bundle = @((($json -join [string][char]10) | ConvertFrom-Json))
            foreach ($record in $bundle) {
                if ([System.IO.Path]::GetFileName($record.path) -ne $record.path) { throw 'Invalid report filename' }
                [System.IO.File]::WriteAllBytes((Join-Path $reports $record.path),[Convert]::FromBase64String($record.content))
            }
            Write-Host 'Linux report bundle saved; kubeconfig and Secret values excluded.'
        } catch { Write-Host "Could not retrieve Linux reports: $($_.Exception.Message)" }
    }
    Write-Host "Reports: $reports"
    Write-Host 'Any created verification cluster is retained inside the development container.'
    Write-Host 'Its ingress is inside that container; Windows browser access needs a VS Code port forward.'
    Stop-Transcript | Out-Null
}
