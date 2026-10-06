param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("init", "sync", "check")]
    [string]$Command,

    [Parameter(Position = 1)]
    [string]$Module,

    [string]$Remote = "origin",
    [string]$Base = "dev"
)

$ErrorActionPreference = "Stop"

$repositoryDir = Split-Path -Parent $PSScriptRoot
$canonicalPaths = @(
    "README.md",
    "docs/specs",
    "docs/reports",
    "docs/guides",
    "docs/contributions/README.md"
)

function Invoke-Git {
    param([string[]]$Arguments)

    $output = & git -C $repositoryDir @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Git command failed: git $($Arguments -join ' ')"
    }
    return $output
}

function ConvertTo-Slug {
    param([string]$Value)

    return $Value.ToLowerInvariant().Replace("/", "-") -replace "[^a-z0-9._-]+", "-" -replace "^-+|-+$", ""
}

function Assert-BaseReference {
    & git -C $repositoryDir rev-parse --verify "$Remote/$Base" *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Remote branch not found: $Remote/$Base"
    }
}

function New-ContributionDocument {
    if ([string]::IsNullOrWhiteSpace($Module)) {
        throw "Module is required. Example: .\scripts\docs-workflow.ps1 init vacation"
    }

    $branchName = (Invoke-Git -Arguments @("branch", "--show-current")) -join ""
    if ([string]::IsNullOrWhiteSpace($branchName)) {
        throw "A contribution document cannot be created from detached HEAD."
    }

    $moduleSlug = ConvertTo-Slug -Value $Module
    $branchSlug = ConvertTo-Slug -Value $branchName
    if ([string]::IsNullOrWhiteSpace($moduleSlug) -or [string]::IsNullOrWhiteSpace($branchSlug)) {
        throw "Module or branch name cannot be converted to a document path."
    }

    $contributionDir = Join-Path $repositoryDir "docs/contributions/$moduleSlug/$branchSlug"
    $contributionFile = Join-Path $contributionDir "README.md"
    if (Test-Path -LiteralPath $contributionFile) {
        throw "Contribution document already exists: $contributionFile"
    }

    $null = New-Item -ItemType Directory -Path $contributionDir -Force
    $content = @"
# $Module / $branchName 기여 문서

- 대상 모듈: ``$Module``
- 작업 브랜치: ``$branchName``
- 기준 브랜치: ``dev``
- 상태: 작성 중

## 기능 범위

- 구현 범위:
- 제외 범위:

## 설계 결정

- 관련 규칙·기능 ID:
- 도메인·애플리케이션 결정:

## 인터페이스와 데이터 영향

- API·권한 변경:
- 스키마·migration 변경:
- 환경변수·인프라 영향:

## 검증

- 실행한 테스트:
- 남은 검증:

## 공용 문서 반영 후보

- Notion 원문:
- 저장소 명세·README:
"@
    [System.IO.File]::WriteAllText(
        $contributionFile,
        $content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "Created: docs/contributions/$moduleSlug/$branchSlug/README.md"
}

function Sync-CanonicalDocuments {
    $changes = & git -C $repositoryDir status --porcelain -- @canonicalPaths
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to inspect canonical document status."
    }
    if ($changes) {
        [Console]::Error.WriteLine(($changes -join [Environment]::NewLine))
        throw "Canonical documents have uncommitted changes. Commit or stash them before syncing."
    }

    Invoke-Git -Arguments @("fetch", $Remote, $Base) | Out-Null
    Assert-BaseReference
    $arguments = @(
        "restore",
        "--source", "$Remote/$Base",
        "--worktree",
        "--"
    ) + $canonicalPaths
    Invoke-Git -Arguments $arguments | Out-Null

    Write-Host "Canonical documents were synchronized from $Remote/$Base."
    Write-Host "Review the diff and commit the synchronized files. Contribution drafts were preserved."
}

function Test-DocumentScope {
    Assert-BaseReference
    $arguments = @("diff", "--name-only", "$Remote/$Base", "HEAD", "--") + $canonicalPaths
    $changedFiles = Invoke-Git -Arguments $arguments
    if ($changedFiles) {
        [Console]::Error.WriteLine(($changedFiles -join [Environment]::NewLine))
        throw "This branch changes canonical documents. Move proposals under docs/contributions/."
    }

    Write-Host "Document scope check passed against $Remote/$Base."
}

switch ($Command) {
    "init" { New-ContributionDocument }
    "sync" { Sync-CanonicalDocuments }
    "check" { Test-DocumentScope }
}
