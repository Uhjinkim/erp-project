# workforce / codex/workforce-registration-roles 기여 문서

- 대상 모듈: workforce, 연계 vacation·board 및 메뉴
- 작업 브랜치: `codex/workforce-registration-roles`
- 기준 브랜치: `dev`
- 검토일: 2026-10-30
- 상태: 구현·자동 검증·운영 migration 및 배포 완료

## 기능 범위와 사용자 결정

- FN-HR-006 신규 등록·FN-HR-009 재입사의 역할별 권한 설명, 선택 상태, 전체 해제 버튼을
  보완하고 로그인 계정 생성 영역을 분리한다. 일반 사원은 추가 역할이 필요 없다.
- 사용자 확정: **인사 관리자와 휴가 승인 인사담당자는 동일한 역할이다.**
- 사용자 후속 확정: **인사관리자 여러 명 중 누구나 인사담당자 단계의 휴가를 승인한다.**
- 게시판 사용자 후속 확정: **게시판 운영자는 경영 담당자와 동일한 역할이다.**
  기존 `MANAGEMENT_OFFICER`를 재사용하고 `경영 담당자 (게시판 운영자)`로 표시한다.
  등록 화면에 경영 공지 작성·타인 글/댓글 삭제 권한과 타인 내용 수정 불가를 설명한다.
- 앞선 별도 역할 안내는 폐기한다. 통합 코드는 `HR_MANAGER`이며 `HR_LEAVE_APPROVER`는
  신규 부여와 역할 조회 선택지에서 제외한다.
- 초기 구현 이후 사용자가 migration 적용과 운영 배포까지 명시적으로 요청했다.
  운영 반영은 아래 실행 기록을 따른다. 개발 공유 DB·Notion·정본 문서는 수정하지 않는다.

## 설계와 권한

- LV-003~005: 부서장·상위 부서장 개인 승인 우선순위는 유지한다. 담당 부서장을 결정할 수
  없으면 재직 중이고 현재 활성 `HR_MANAGER` 배정을 가진 인사관리자들의 공용 승인 대상이다.
- 공용 신청의 대기 중 `approver_no`는 null이다. 현재 활성 인사관리자는 모두 목록을 조회하고
  승인·반려할 수 있다. 부서장 개인에게 지정된 신청에는 인사관리자 역할만으로 개입할 수 없다.
- 승인·반려 시 실제 처리 사번을 `approver_no`에 기록한다. 이력 actor도 같은 사번이다.
  기존 transaction·행 잠금 안에서 상태 변경·잔여 차감·이력 기록을 수행한다.
- 한 관리자가 처리한 뒤 다른 관리자는 다시 승인·반려할 수 없다. 회수는 기존대로 실제
  승인자만 가능하며, 재신청 시 현재 조직과 인사관리자 가용 여부로 다시 라우팅한다.
- 활성 인사관리자도 부서장도 없으면 신청을 거절한다. 일반 사원·퇴사자에게 공용 승인 권한을
  주지 않는다. 서버 판정이 최종 권한이며 프론트 역할 판정은 버튼 안내용이다.
- 미리 개인 승인자가 저장된 기존 신청은 조직의 과거 상태를 추정하여 공용 신청으로
  자동 재배정하지 않는다. 기존 승인자와 이력은 유지하며 재신청부터 새 라우팅을 적용한다.
- BD-003·BD-006 / 기존 BD-03 의제: 경영 담당자의 게시판 운영 권한을 별도 Role로 나누지
  않는다. 기존 게시판 서버 정책(경영 공지 작성·타인 글/댓글 소프트 삭제, 타인 수정 불가)을
  유지한다. 프론트는 기존 `can_edit`·`can_delete` 응답을 계속 사용한다.
- vacation은 application port와 workforce infrastructure gateway를 통해 조직·역할을 조회한다.
  도메인과 애플리케이션에 ORM 또는 다른 컨텍스트의 모델 의존성을 추가하지 않았다.

## API·스키마·데이터 영향

- 역할 목록·상세는 이전 `HR_LEAVE_APPROVER`를 노출하지 않는다. 직접 부여 요청도 거절한다.
  `HR_MANAGER`의 한 명 제한은 없으며 인사 관리와 휴가 공용 승인 권한을 함께 제공한다.
- 휴가 응답의 `approver_no`가 nullable이 된다. 신청자는 값을 지정할 수 없다.
  프론트 목록·상세에는 null을 `인사 관리자 공용 승인`으로 표시한다.
- `GET /api/vacations/approvals/`는 인사관리자에게 본인의 기존 개인 처리 대상과 공용 대기
  신청을 반환한다. 타 인사관리자가 처리한 신청은 공용 대기함에서 사라진다.
- `vacation.0004`: `leave_requests.approver_no` nullable 변경.
- `workforce.0008`: 이전 역할 배정의 ID·시작 시각·기간 이력을 보존하며 `HR_MANAGER`로
  통합하고 이전 역할 마스터를 제거한다. 무기한 활성 중복은 한 개만 남기고 나머지 배정의
  회수 시각을 migration 시각으로 기록한다. 미래 시작·예정 회수 기간은 임의 변경하지 않는다.
  원래 역할 구분을 복원할 수 없으므로 해당 데이터 migration은 의도적으로 역변환을 제공하지 않는다.
- `workforce.0009`: 기존 필수 역할 migration에 빠져 있던 `MANAGEMENT_OFFICER` 마스터를
  보장하고 표시명을 `경영 담당자 (게시판 운영자)`로 통일한다. 기존 역할 코드·배정은 보존한다.
  별도 `BOARD_MODERATOR` 역할이나 추가 권한은 만들지 않는다.
- 환경변수·의존성 변경 없음. 개발용 설정의 인사담당자 라우팅도 개인 지정 대신 공용으로 맞춘다.
- 초기 구현 검증은 공유 서비스에 의존하지 않았다. 후속 사용자 승인으로 운영 RDS의 실제
  스키마·배정/신청 건수를 읽기 전용 확인한 뒤 세 migration을 적용했다(아래 실행 기록).
  개발 공유 DB는 변경하지 않는다. 기존 역할 목록 캐시는 TTL(기본 180초) 동안 남을 수 있다.

## 검증

- SQLite·fakes로 테스트하며 SSH 터널·공유 서비스에 의존하지 않는다.
- 신규 회귀 검증: 두 인사관리자의 공용 목록·승인·반려, 일반 사원의 처리 차단,
  중복 처리 차단과 잔여 차감, 실제 actor 기록, 실제 승인자만 회수, 재신청 라우팅,
  승인자 부재 시 등록 차단, 역할 migration의 이력 보존과 중복 병합, 복수 관리자 부여,
  이전 역할 선택지·직접 부여 차단, 프론트 메뉴·버튼 권한.
- `bun test ./tests`: 71개 통과. `bun run lint`, `bun run build`: 통과.
- `uv run ruff check .`, 테스트 설정의 `python manage.py check`: 통과.
- migration 생성·drift 검사에서는 `/tmp`의 임시 설정으로 테스트용 SQLite·로컬 캐시를
  유지한 채 `MIGRATION_MODULES = {}`만 복원했다. 일반 테스트 설정은 legacy 앱의 migration을
  비활성화하므로 이 설정이 필요하다. `makemigrations --check --dry-run`: 변경 없음.
- `sqlmigrate vacation 0004`: 로컬 SQLite SQL 생성·검토만 수행했다.
- 실제 브라우저·동시 연결 기반 경합 검증은 실행하지 않았다. 운영 migration은 후속 승인으로
  적용했으며 아래 기록과 구분한다.
  중복 처리 테스트는 기존 DB 행 잠금 경계 안의 순차 재시도를 검증한다.
- `uv run pytest -q`: 전체 백엔드 570개 통과.
- 게시판 후속 변경은 기존 경영담당자의 글·댓글 삭제/수정 거절 API와 새 역할 마스터의
  최초 생성·기존 배정 보존·재실행 중복 방지·목록 노출을 포함해 관련 테스트 47개가 통과했다.
  Ruff·Django check·migration drift 및 프론트 lint·build 재검사도 통과했다.
- `git diff --check`, `./scripts/docs-workflow.sh check`: 통과. 작업 트리의 정본 문서 변경도 없음.

## 정본 반영 후보와 upstream 확인

- Notion 비즈니스 규칙 원문 `https://app.notion.com/p/3d78eced448d81528023db7f8dd1b49a`
  조회를 시도했으나 연결 도구가 404/접근 불가를 반환했다. 원문을 검증·수정했다고 주장하지 않는다.
- 저장소 `02-business-rules.md`의 LV-004는 인사관리자 fallback을 명시한다.
  반면 `06-api-specification.md`는 두 역할을 분리한다. 이번 사용자 명시 결정으로 구현을 통합하며
  문서 담당자가 Notion과 정본의 충돌을 정리해야 한다.
- `06-api-specification.md` 2절 역할 설명, 5.5 역할 단일 지정 제한, 휴가 승인자 결정과
  승인 목록 계약에 통합 역할·공용 승인·nullable `approver_no`를 반영한다.
- `08-table-specification.md`의 roles·leave_requests 설명 및 workforce 구현 매핑도 갱신한다.
- BD-03 및 게시판 역할 설명에 사용자 확정된 경영 담당자=게시판 운영자 관계와 기존
  삭제 전용 운영 권한을 반영한다. `roles` 표의 표시명과 마스터 공급 migration도 반영한다.
- 운영 DB 적용 여부와 Notion 반영 여부는 별도 관리한다. Notion은 미반영이며 운영 적용은
  아래 실행 기록을 따른다.

## 사용자 승인 후 운영 반영 · 2026-10-30

- 대상: AWS 계정 610849077646 / ap-northeast-2 / RDS erp-postgres의 erp-db, 앱 사용자 erp.
  EC2 i-0a4ecf2b587053b08, 공개 HTTPS https://13.125.22.237.
- 사용자 명시 요청: “마이그레이션 후 배포까지 진행해”. 별도 DB 생성·계정 생성·개발 데이터
  복사 없이 검증한 역할 변경과 해당 migration만 반영한다.
- 실행 전 RDS available, 자동 백업 보존 1일, LatestRestorableTime=2026-10-30T04:41:02Z 확인.
  실행 중 릴리스는 d1ff8072d07bc5634362e34861bf4ab17d5dca72였다.
- 운영 PostgreSQL 읽기 전용 검사에서 역할 배정 0건·휴가 신청 0건, approver_no nullable을
  확인했다. 실제 sqlmigrate 결과는 해당 컬럼 DROP NOT NULL 하나이며 삭제/축소 DDL은 없다.
- 코드 commit: 276a6f42e75dc117d65c82e83bda92bf4b52a6a8.
  [dev CI 41004793722](https://github.com/Uhjinkim/erp-project/actions/runs/41004793722) 성공.
- 기존 backend 컨테이너의 비밀 환경을 출력하지 않고 /tmp 임시 migration 패키지를 사용했다.
  정확히 vacation.0004, workforce.0008, workforce.0009만 실행할 계획임을 검증한 뒤
  단일 외부 transaction에서 적용했다. lock timeout 5초, statement timeout 60초로 제한했다.
  Django ORM·MigrationExecutor가 실제 변경을 수행했으며 migration fake는 사용하지 않았다.
- SSM SQL 검토: 228cd217-097f-4fba-8f9a-3e6e235b80ba.
  SSM 적용: e45603b2-1cd4-4508-a77f-8da74c54bd3c, Success. 적용 후 대상 잔여 계획 0개,
  roles는 HR_MANAGER·MANAGEMENT_OFFICER·PAYROLL_MANAGER로 확인했다.
- AWS Python SDK 스킬과 Secrets Manager 스킬의 비밀 비노출 규칙을 따랐다. AWS/SSM API는
  AWS Core 연결 도구로 실행하고 Secret 원문·컨테이너 환경·개인정보를 출력하지 않았다.
- 전체 최종 로컬 backend 572개·배포 회귀 10개 통과. main backend/frontend CI도 성공했다.
  [main CI/CD 41004989448](https://github.com/Uhjinkim/erp-project/actions/runs/41004989448)에서
  동일 commit의 backend/frontend/deploy 작업이 모두 Success로 완료됐다.
- 배포 후 SSM 검증 65c3b4b0-ec7f-4c70-ac05-294ff436c64f Success:
  current symlink와 backend/nginx 이미지가 모두 276a6f42e75dc117d65c82e83bda92bf4b52a6a8,
  두 컨테이너 healthy, 전체 migration 잔여 계획 0개. 실제 역할 표시명도 세 개 모두 확인했다.
- 공개 HTTPS health는 online/connected이며 실제 제공 JS는 `/assets/index-jzNZ2cvd.js`다.
  통합 HR 설명·경영 담당자/게시판 운영자 설명·인사관리자 공용 승인 문구가 이 파일에 포함됨을
  확인했다. 직원·휴가·급여 등 업무 데이터를 생성하거나 관리자 비밀번호를 조회하지 않았다.
- 실제 로그인한 사원 등록·휴가 승인 등 업무 쓰기 smoke test와 host 재부팅은 수행하지 않았다.
  해당 흐름의 자동 검증은 앞선 SQLite/fakes 및 CI 결과를 따른다.
