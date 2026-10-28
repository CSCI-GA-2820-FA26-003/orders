# Run from a normal Windows PowerShell. No administrator elevation is requested.
# Creates only disposable, uniquely named verification containers and a network.
[CmdletBinding()]
param([switch]$SmokeOnly)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$runId = [guid]::NewGuid().ToString('N').Substring(0, 12)
$prefix = "orders-s2-$runId"
$reports = Join-Path $repo ".test-tmp\postgres-$runId"
$pg = "$prefix-pg"
$app = "$prefix-app"
$network = "$prefix-net"
$image = "orders:s2-verify-$runId"
$networkCreated = $false
$pgCreated = $false
$appCreated = $false
$imageBuilt = $false
$oldDatabaseUri = $env:DATABASE_URI
$oldPgPassword = $env:POSTGRES_PASSWORD
$result = 'FAILED'
New-Item -ItemType Directory -Path $reports -Force | Out-Null
Start-Transcript -Path (Join-Path $reports 'verification.log') | Out-Null
function Invoke-Docker {
    param([string[]]$DockerArgs)
    & docker @DockerArgs
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed (exit $LASTEXITCODE)." }
}
function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}
function Get-AppUrl {
    $binding = & docker port $app '8080/tcp'
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($binding)) {
        throw 'Could not discover the application port.'
    }
    $url = "http://$($binding.Trim())"
    Write-Host "Application address: $url"
    return $url
}
function Wait-Health {
    param([string]$BaseUrl)
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        try {
            $health = Invoke-RestMethod "$BaseUrl/health" -TimeoutSec 2
            if ($health.status -eq 'OK') { return }
        } catch { }
        Start-Sleep -Seconds 1
    }
    throw 'The container health endpoint did not become ready.'
}
function Assert-HttpStatus {
    param([string]$Uri, [string]$Method, [int]$Expected)
    $actual = 0
    try {
        $response = Invoke-WebRequest -Uri $Uri -Method $Method -UseBasicParsing
        $actual = [int]$response.StatusCode
    } catch {
        if ($null -ne $_.Exception.Response) { $actual = [int]$_.Exception.Response.StatusCode }
        else { throw }
    }
    Assert-True ($actual -eq $Expected) "Expected HTTP $Expected, received $actual."
}
try {
    Write-Host 'Checking Docker Engine access...'
    Invoke-Docker -DockerArgs @('info', '--format', '{{.ServerVersion}}')
    $env:POSTGRES_PASSWORD = [guid]::NewGuid().ToString('N')
    $env:DATABASE_URI = "postgresql+psycopg://postgres:$($env:POSTGRES_PASSWORD)@postgres:5432/orders"
    Invoke-Docker -DockerArgs @('network', 'create', $network)
    $networkCreated = $true
    Invoke-Docker -DockerArgs @('run', '-d', '--name', $pg, '--network', $network, '--network-alias', 'postgres', '--env', 'POSTGRES_PASSWORD', '--env', 'POSTGRES_DB=orders', 'postgres:15-alpine')
    $pgCreated = $true
    $ready = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        & docker exec $pg pg_isready -U postgres -d orders *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Seconds 1
    }
    Assert-True $ready 'PostgreSQL did not become ready.'
    if (-not $SmokeOnly) {
        Write-Host 'Running locked Linux dependencies, lint, and the full suite against PostgreSQL 15...'
        $checks = 'python -m pip install pipenv && pipenv sync --dev --system && python -m flake8 service tests && python -m pylint service tests && python -m pytest tests -p no:cacheprovider --cov=service --cov-report=term-missing --cov-report=xml:/reports/coverage.xml --cov-fail-under=95 --junitxml=/reports/junit.xml'
        Invoke-Docker -DockerArgs @('run', '--rm', '--network', $network, '--mount', "type=bind,source=$repo,target=/app,readonly", '--mount', "type=bind,source=$reports,target=/reports", '--workdir', '/app', '--env', 'DATABASE_URI', '--env', 'PYTHONDONTWRITEBYTECODE=1', '--env', 'COVERAGE_FILE=/reports/.coverage', 'python:3.12-slim', 'sh', '-ec', $checks)
    } else {
        Write-Host 'SmokeOnly: skipping the previously completed unit suite and lint.'
    }
    Write-Host 'Building the actual application Dockerfile...'
    Invoke-Docker -DockerArgs @('build', '--pull', '--tag', $image, $repo)
    $imageBuilt = $true
    Invoke-Docker -DockerArgs @('run', '-d', '--name', $app, '--network', $network, '--publish', '127.0.0.1::8080', '--env', 'DATABASE_URI', $image)
    $appCreated = $true
    $baseUrl = Get-AppUrl
    Wait-Health $baseUrl
    $payload = @{ customer_id = 987654; status = 'NEW' } | ConvertTo-Json
    $created = Invoke-WebRequest "$baseUrl/orders" -Method Post -ContentType 'application/json' -Body $payload -UseBasicParsing
    Assert-True ([int]$created.StatusCode -eq 201) 'Create did not return 201.'
    $order = $created.Content | ConvertFrom-Json
    $id = $order.id
    $cancelled = Invoke-RestMethod "$baseUrl/orders/$id/cancel" -Method Put
    Assert-True ($cancelled.status -eq 'CANCELLED') 'Cancellation was not persisted.'
    $again = Invoke-RestMethod "$baseUrl/orders/$id/cancel" -Method Put
    Assert-True ($again.status -eq 'CANCELLED') 'Repeated cancellation failed.'
    # Keep a nonmatching order present so ignoring the status parameter cannot pass.
    $otherPayload = @{ customer_id = 987656; status = 'NEW' } | ConvertTo-Json
    $other = Invoke-RestMethod "$baseUrl/orders" -Method Post -ContentType 'application/json' -Body $otherPayload
    Assert-True ($other.status -eq 'NEW') 'Could not create the nonmatching control order.'
    $matches = @(Invoke-RestMethod "$baseUrl/orders?status=CANCELLED")
    Assert-True (@($matches | Where-Object { $_.id -eq $id }).Count -eq 1) 'Status filtering did not return the cancelled order.'
    Assert-True (@($matches | Where-Object { $_.status -ne 'CANCELLED' }).Count -eq 0) 'Status filter returned a nonmatching order.'
    Assert-HttpStatus "$baseUrl/orders?status=invalid" 'Get' 400
    Assert-HttpStatus "$baseUrl/orders?unsupported=1" 'Get' 400
    Assert-HttpStatus "$baseUrl/orders/0/cancel" 'Put' 404
    $shippedPayload = @{ customer_id = 987655; status = 'SHIPPED' } | ConvertTo-Json
    $shipped = Invoke-RestMethod "$baseUrl/orders" -Method Post -ContentType 'application/json' -Body $shippedPayload
    Assert-HttpStatus "$baseUrl/orders/$($shipped.id)/cancel" 'Put' 409
    Write-Host 'Restarting PostgreSQL and checking that the order still exists...'
    Invoke-Docker -DockerArgs @('restart', $pg)
    # Restart the application after PostgreSQL is ready to avoid stale pooled connections.
    $ready = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        & docker exec $pg pg_isready -U postgres -d orders *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Seconds 1
    }
    Assert-True $ready 'PostgreSQL did not recover after restart.'
    $sql = 'SELECT status::text FROM "order" WHERE id = ' + [int]$id + ';'
    $persistedStatus = $sql | & docker exec -i $pg psql -U postgres -d orders -At -v ON_ERROR_STOP=1
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL persistence query failed.' }
    Assert-True ($persistedStatus.Trim() -eq 'CANCELLED') 'Database row did not survive PostgreSQL restart.'
    Write-Host 'PASS: cancelled order exists in PostgreSQL after restart.'
    Invoke-Docker -DockerArgs @('restart', $app)
    # Docker assigns an ephemeral host port; discover the current mapping again.
    $baseUrl = Get-AppUrl
    Wait-Health $baseUrl
    $persisted = Invoke-RestMethod "$baseUrl/orders/$id"
    Assert-True ($persisted.status -eq 'CANCELLED') 'The order did not survive the PostgreSQL container restart.'
    $result = 'PASSED'
    if (-not $SmokeOnly) { Write-Host 'PASS: PostgreSQL unit suite/coverage and lint.' }
    Write-Host 'PASS: image build, HTTP actions/filtering/errors, and container restart persistence.'
    Write-Host 'This run does not verify Kubernetes, make targets, CI, or Codecov.'
} catch {
    Write-Host "FAIL: $($_.Exception.Message)"
    $savedPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    if ($appCreated) {
        & docker inspect --format '{{json .State}}' $app | Out-File (Join-Path $reports 'app-state.json') -Encoding utf8
        & docker port $app | Out-File (Join-Path $reports 'app-ports.txt') -Encoding utf8
        & docker logs --tail 150 $app 2>&1 | ForEach-Object { "$_" } | Out-File (Join-Path $reports 'app.log') -Encoding utf8
    }
    if ($pgCreated) {
        & docker logs --tail 100 $pg 2>&1 | ForEach-Object { "$_" } | Out-File (Join-Path $reports 'postgres.log') -Encoding utf8
    }
    $ErrorActionPreference = $savedPreference
    throw
} finally {
    # Remove only resources created by this run, including its disposable DB data.
    if ($appCreated) { & docker rm -fv $app | Out-Host }
    if ($pgCreated) { & docker rm -fv $pg | Out-Host }
    if ($networkCreated) { & docker network rm $network | Out-Host }
    if ($imageBuilt) { & docker image rm $image | Out-Host }
    $env:DATABASE_URI = $oldDatabaseUri
    $env:POSTGRES_PASSWORD = $oldPgPassword
    Write-Host "Result: $result"
    Write-Host "Reports: $reports"
    Stop-Transcript | Out-Null
}