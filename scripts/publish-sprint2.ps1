# Run in normal Windows PowerShell. Login stays in the user's terminal/browser.
[CmdletBinding()]
param([switch]$VerifyFreshCluster)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$repository = 'CSCI-GA-2820-FA26-003/orders'
$branch = 'feature/sprint2-foundation'
$reportDir = Join-Path $repo ('.test-tmp/github-handoff-' + [guid]::NewGuid().ToString('N').Substring(0,12))
New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
foreach ($tool in @('git','gh')) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "Required command not found: $tool" }
}
$current = & git -C $repo branch --show-current
if ($LASTEXITCODE -ne 0 -or $current.Trim() -ne $branch) { throw "Expected branch $branch" }
$dirty = & git -C $repo status --porcelain
if ($LASTEXITCODE -ne 0 -or $dirty) { throw 'The repository has uncommitted changes; review and commit them before publishing.' }
& gh auth status --hostname github.com
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Complete GitHub login in your browser. The workflow scope is needed to push the CI workflow.'
    & gh auth login --hostname github.com --git-protocol https --web --scopes workflow
    if ($LASTEXITCODE -ne 0) { throw 'GitHub login did not complete.' }
}
$freshVerified = $false
if ($VerifyFreshCluster) {
    & (Join-Path $PSScriptRoot 'verify-kubernetes.ps1') -SkipPostgres
    $freshVerified = $true
}
# Use the logged-in gh identity for this push without changing global Git configuration.
function Push-SprintBranch {
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $output = & git -C $repo -c credential.helper= -c 'credential.helper=!gh auth git-credential' push --set-upstream origin "HEAD:refs/heads/$branch" 2>&1 | ForEach-Object { $_.ToString() }
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previousPreference }
    $output | Out-Host
    [System.IO.File]::WriteAllText((Join-Path $reportDir 'push.log'),($output -join [string][char]10),[System.Text.UTF8Encoding]::new($false))
    return [pscustomobject]@{ Code = $code; Text = ($output -join ' ') }
}
$push = Push-SprintBranch
if ($push.Code -ne 0 -and $push.Text -match '(?i)workflow.*scope|scope.*workflow') {
    Write-Host 'GitHub requires workflow permission for this CI file. Complete the browser authorization.'
    & gh auth refresh --hostname github.com --scopes workflow
    if ($LASTEXITCODE -ne 0) { throw 'Workflow authorization did not complete.' }
    $push = Push-SprintBranch
}
if ($push.Code -ne 0) { throw "Push failed; see $reportDir/push.log" }
$body = @'
Orders administrators can filter the collection by exact order status and cancel an eligible NEW order while preserving its items. Invalid queries return JSON 400; cancellation returns 404 for missing orders and 409 for invalid state transitions, with repeated cancellation remaining a no-op.

Adds /health, PostgreSQL-backed GitHub Actions tests and lint with a 95% coverage gate, Codecov integration, and local K3s deployment with PostgreSQL StatefulSet storage, Service and Ingress. Includes Windows launchers for recording external verification when the assistant session cannot access Docker.

Validation observed:
- 142 test methods passed on PostgreSQL 15 and SQLite; coverage 99.02%; flake8 and pylint passed.
- Actual make cluster/build/push/deploy executed with k3d 5.9.0 and K3s 1.35.5.
- Ingress health, CRUD, mixed-status filtering, cancellation, and JSON 400/404/409 passed.
- PostgreSQL Pod UID changed while PVC/PV identities stayed unchanged; order/item values survived Pod recreation and repeated deployment.
- Existing-cluster recovery corrected the registry DNS alias. New cluster configuration uses matching explicit registry names.

GitHub Actions and Codecov PR reports still need to be observed after this PR is opened. Windows browser ingress forwarding has not been checked. Keep the stories open for teammate review and sprint review.

Refs #36, #37, #38, #39, #40, #41, #42, #43, #44.
'@
if ($freshVerified) {
    $body += [char]10 + [char]10 + 'A fresh isolated K3s run with the corrected registry naming also passed before this branch was pushed.'
}
$bodyFile = Join-Path $reportDir 'pr-body.md'
[System.IO.File]::WriteAllText($bodyFile,$body,[System.Text.UTF8Encoding]::new($false))
$title = 'Sprint 2: Orders filtering, cancellation, CI and local K3s deployment'
$existing = & gh pr list --repo $repository --head $branch --base master --state open --json url --jq '.[0].url // empty'
if ($LASTEXITCODE -ne 0) { throw 'Could not check existing pull requests.' }
if ($existing) {
    $prUrl = $existing.Trim()
    & gh pr edit $prUrl --repo $repository --title $title --body-file $bodyFile
    if ($LASTEXITCODE -ne 0) { throw 'Could not update the existing PR description.' }
} else {
    $created = & gh pr create --repo $repository --base master --head $branch --title $title --body-file $bodyFile --draft
    if ($LASTEXITCODE -ne 0) { throw 'PR creation failed; the pushed branch is retained.' }
    $prUrl = ($created | Where-Object { $_ -match '^https://github.com/CSCI-GA-2820-FA26-003/orders/pull/[0-9]+$' } | Select-Object -Last 1)
}
if (-not $prUrl -or $prUrl -notmatch '^https://github.com/CSCI-GA-2820-FA26-003/orders/pull/[0-9]+$') { throw 'Could not verify the PR URL.' }
$head = & git -C $repo rev-parse HEAD
$result = [ordered]@{ prUrl=$prUrl; commit=$head.Trim(); freshKubernetesVerified=$freshVerified; publishedAtUtc=[DateTime]::UtcNow.ToString('o') }
[System.IO.File]::WriteAllText((Join-Path $reportDir 'result.json'),(ConvertTo-Json -InputObject $result),[System.Text.UTF8Encoding]::new($false))
Write-Host "Draft PR: $prUrl"
Write-Host "Reports: $reportDir"
Write-Host 'The PR now triggers GitHub Actions. CI and Codecov results still need review.'
