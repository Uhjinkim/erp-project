# 기능 모듈 브랜치·문서 협업 가이드

- 기준 브랜치: `dev`
- 릴리스 브랜치: `main`
- 적용 범위: 기능 모듈 개발, 공용 명세 동기화, 검토와 병합

## 1. 목표

기능 모듈을 별도 브랜치에서 병렬 개발하면서 공용 문서의 최신 내용을 계속 받아보고, 같은 Markdown
파일을 여러 명이 동시에 수정해 발생하는 충돌을 줄인다. 제품 명세와 구현 문서는 `dev`에서 하나의
정본을 유지하고 기능 브랜치는 고유 경로의 기여 초안만 작성한다.

Git의 `pull`은 특정 디렉터리만 갱신하는 기능이 아니다. 기능 브랜치에서 `dev`를 병합하거나
rebase하면 코드까지 함께 갱신된다. 이 저장소는 두 가지 동기화 방법을 구분한다.

- 전체 통합 동기화: `dev`를 기능 브랜치에 merge해 코드와 문서를 함께 갱신
- 문서 전용 동기화: 스크립트로 `dev`의 공용 문서 경로만 작업 트리에 반영

전체 통합 동기화를 정기적으로 수행하는 것이 기본이며, 문서 전용 동기화는 코드 병합 시점을 늦춰야
하지만 최신 명세를 먼저 확인해야 할 때 사용한다.

## 2. 문서 소유권

### 공용 문서

다음 경로는 문서 담당자가 `dev`에서 갱신한다.

- 루트 `README.md`
- `docs/specs/`
- `docs/reports/`
- `docs/guides/`
- `docs/contributions/README.md`

Notion 원문 수정과 `docs/specs/notion/` 스냅샷 동기화도 같은 담당자가 수행한다. 기능 브랜치의
개발자는 공용 문서의 변경 후보를 기여 초안에 기록한다.

### 기능 브랜치 기여 문서

각 기능 브랜치는 다음 고유 경로만 사용한다.

```text
docs/contributions/<module>/<branch-slug>/README.md
```

모듈명과 브랜치명이 경로에 포함되므로 여러 명이 동시에 문서를 추가해도 같은 파일을 수정할 가능성이
낮다. 사람 이름만으로 디렉터리를 나누는 방식보다 담당 모듈과 변경 목적을 Git 이력에서 찾기 쉽다.

## 3. 브랜치 시작

기능 브랜치는 최신 `dev`에서 생성한다.

```bash
git fetch origin
git switch dev
git pull --ff-only origin dev
git switch -c feature/<module>-<topic>
```

PowerShell에서도 같은 Git 명령을 사용한다. 공유 중인 기능 브랜치는 강제 push가 필요한 rebase보다
merge를 사용한다.

기여 문서를 생성한다.

macOS/Linux:

```bash
./scripts/docs-workflow.sh init <module>
```

Windows PowerShell:

```powershell
.\scripts\docs-workflow.ps1 init <module>
```

## 4. 개발 중 동기화

### 권장: dev 전체 병합

작업 내용을 먼저 commit한 뒤 최신 `dev`를 병합한다.

```bash
git fetch origin
git merge origin/dev
```

이 방식은 실제 병합 전에 코드 통합 문제도 조기에 발견하고 Git의 공통 이력을 보존한다.

### 선택: 공용 문서만 동기화

코드는 현재 기준을 유지하면서 공용 문서만 확인해야 할 때 사용한다.

macOS/Linux:

```bash
./scripts/docs-workflow.sh sync
git diff -- README.md docs
git add README.md docs
git commit -m "chore(docs): sync canonical docs from dev"
```

Windows PowerShell:

```powershell
.\scripts\docs-workflow.ps1 sync
git diff -- README.md docs
git add README.md docs
git commit -m "chore(docs): sync canonical docs from dev"
```

동기화 명령은 `origin/dev`를 fetch한 뒤 공용 문서만 복원한다. 기능 브랜치의
`docs/contributions/<module>/<branch-slug>/`는 변경하지 않는다. 공용 문서에 미커밋 변경이 있으면
덮어쓰지 않고 중단한다.

다른 원격 또는 기준 브랜치를 사용해야 할 때만 옵션으로 지정한다.

```bash
./scripts/docs-workflow.sh sync <remote> <base-branch>
```

```powershell
.\scripts\docs-workflow.ps1 sync -Remote <remote> -Base <base-branch>
```

## 5. 기능 브랜치 문서 작성

기여 초안에는 다음 내용을 유지한다.

1. 기능 범위와 제외 범위
2. 구현 중 확정한 도메인·애플리케이션 결정
3. API, 권한, 환경변수와 스키마 영향
4. migration 및 공유 인프라 주의사항
5. 실행한 테스트와 남은 검증
6. Notion 및 공용 저장소 문서에 반영할 항목

공용 문서의 문장을 복사해 별도 버전으로 관리하지 않는다. 변경이 필요한 제목과 이유, 관련 규칙 ID,
구현 파일을 기록해 문서 담당자가 정본에 반영할 수 있게 한다.

## 6. Pull Request 전 검사

기능 코드와 기여 문서를 commit한 뒤 다음 검사를 실행한다.

```bash
./scripts/docs-workflow.sh check
```

```powershell
.\scripts\docs-workflow.ps1 check
```

검사는 현재 브랜치가 `origin/dev`와 비교해 공용 문서를 직접 변경했는지 확인한다. 실패하면 공용 문서
변경 내용을 기능 브랜치의 기여 초안으로 옮기고 공용 파일은 `dev` 기준으로 되돌린다. 사용자 작업을
잃지 않도록 되돌리기 전에는 반드시 diff를 검토한다.

## 7. 검토와 병합

1. 기능 담당자는 모듈 코드, 테스트와 고유 기여 문서를 Pull Request로 제출한다.
2. 리뷰어는 기능 동작과 함께 기여 문서의 공용 명세 반영 후보를 확인한다.
3. 기능 브랜치를 `dev`에 병합한다.
4. 문서 담당자는 기여 초안을 검토해 Notion 원문과 공용 문서를 갱신한다.
5. Notion이 변경되면 `docs/specs/notion/` 스냅샷과 확인일을 함께 갱신한다.
6. 반영을 마친 기여 초안은 별도 `dev` commit에서 삭제한다.
7. 릴리스 시점에 검증된 `dev`를 `main`으로 병합한다.

공용 문서 통합을 기능 PR 안에서 해야 하는 예외 상황에는 문서 담당자가 해당 PR에 직접 참여하고,
기능 개발자가 독자적으로 공용 문서를 수정하지 않는다.

## 8. 권장 저장소 보호 설정

- `dev`와 `main` 직접 push 금지
- Pull Request 승인과 상태 검사 필수
- `docs/specs/`, `docs/reports/`, `docs/guides/`에 문서 담당자 CODEOWNERS 적용
- 기능 브랜치 삭제 전 기여 문서의 반영 여부 확인
- 공유 중인 브랜치의 강제 push 금지

CODEOWNERS의 실제 GitHub 사용자명과 승인 규칙은 팀 구성이 확정된 뒤 저장소 설정에 추가한다.
