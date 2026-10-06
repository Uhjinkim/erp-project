# board / board 기여 문서

- 대상 모듈: `board`
- 작업 브랜치: `board`
- 기준 브랜치: `dev`
- 상태: 작성 중

## 기능 범위

- 구현 범위: 게시글(일반/공지) 작성·수정·삭제·목록·상세 조회, 댓글/대댓글(1단계 답글만 허용),
  게시글 소프트 삭제, 작성자/작성자명 기준 검색을 위한 API 응답 보강.
- 제외 범위: 첨부파일, 조회수, `board_notice_categories` 시드 데이터 삽입(별도 승인 필요).

## 설계 결정

- 관련 규칙·기능 ID: `BD-001`~`BD-008`, `FN-BD-001`~`FN-BD-007`.
- 도메인·애플리케이션 결정:
  - 게시글 유형은 `일반`/`공지`로 구분하고(`BD-001`), 공지만 업무 분류를 가진다.
  - 공지 분류는 작성자의 workforce 역할/구조로 자동 판정한다(`BD-003`, `BD-004`, `BD-008`):
    경영 → `MANAGEMENT_OFFICER_ROLE`, 인사 → 기존 `HR_MANAGER_ROLE`, 급여 →
    `PAYROLL_MANAGER_ROLE`, 부서 → `Department.head`가 본인인 경우(별도 Role 없음).
  - 한 사원이 공지 자격 역할을 여러 개 보유하면, 클라이언트가 보낸 분류가 보유 자격 집합에
    속하는지만 검증한다(자격이 하나면 사실상 자동 고정). 이 선택 로직은 `BD-008` 원문에
    없는 구현 디테일이라 다중 역할 실사례가 나오면 제품 결정을 재확인해야 한다.
  - 수정·삭제는 작성자 본인 또는 시스템관리자만 가능하다(`BD-006`). 시스템관리자는 새
    workforce Role을 만들지 않고 기존 `request.user.is_superuser` 관례를 재사용한다.
  - 삭제는 소프트 삭제다(`board_posts.deleted_at`). 하드 삭제로 갔다가 사용자 지시로 다시
    소프트 삭제로 되돌렸다.
  - 댓글은 `parent_comment_id`로 1단계 답글만 허용하고(답글에 답글 금지,
    `NestedReplyNotAllowedError`), 소프트 삭제로 처리한다.

## 인터페이스와 데이터 영향

- API·권한 변경: `/api/board/posts/`, `/api/board/posts/<id>/`,
  `/api/board/posts/<id>/comments/`, `/api/board/comments/<id>/` 신규 추가. 전부
  `IsAuthenticated` + 기존 `workforce.presentation.permissions.request_employee_no` 재사용.
- 스키마·migration 변경:
  - `board_posts`, `board_notice_categories`는 공유 DB에 이미 존재하는 테이블이었다(읽기 전용
    확인 후 발견). `writer_emp_no`, `notice_category_code`는 실제 컬럼명을 그대로 맞췄고,
    `notice_category_code`는 `board_notice_categories`를 참조하는 FK다(영문 코드
    `MANAGEMENT`/`HR`/`PAYROLL`/`DEPARTMENT`는 이번에 결정, 테이블이 비어 있어 시드는
    별도 진행 필요).
  - `board/migrations/0001_initial.py`는 두 기존 테이블을 `SeparateDatabaseAndState`로
    상태만 등록한다(실제 DDL 없음).
  - `board/migrations/0002_postmodel_deleted_at_commentmodel.py`는 `board_posts.deleted_at`
    컬럼 추가와 `board_comments`(완전 신규 테이블, 공유 DB에 존재하지 않음을 확인 후 설계)
    생성을 포함한다. `sqlmigrate`로 DDL을 먼저 공개하고 사용자 승인을 받은 뒤 공유 개발 DB
    (`erp_dev.public`)에 `migrate board`로 적용 완료(2026-10-01).
  - 게시글 응답에 `writer_name`을 추가했다(`Employee.person.name`을 `select_related`로 조인,
    스키마 변경 아님, 작성자 검색용).
- 환경변수·인프라 영향: 없음. 기존 세션 인증, SSH 터널 경로를 그대로 사용한다.

## 검증

- 실행한 테스트: `uv run pytest`(backend 전체, board 37개 포함), `uv run ruff check .`,
  `uv run python manage.py check`, `uv run python manage.py makemigrations --check --dry-run`.
  프론트는 `bun run lint`, `bun run build`.
- 남은 검증: `board_notice_categories` 시드 후 공지 작성 운영 DB 동작 확인. 프론트엔드
  게시판 화면(`BoardPanel.tsx`)은 로컬에서 수동 확인했고 별도 자동화 E2E는 없다.

## 공용 문서 반영 후보

- Notion 원문: 비즈니스 규칙(`BD-001`~`008`), 기능 명세(`FN-BD-001`~`007`) 페이지에 아래
  상세가 이미 반영되어 있는지 Notion 쪽에서 확인 필요 — 원문은
  <https://app.notion.com/p/3d78eced448d81528023db7f8dd1b49a> (비즈니스 규칙),
  <https://app.notion.com/p/3d78eced448d8118bd7ce952069417ed> (기능 명세).
- 저장소 명세·README 반영 제안 (문서 담당자 검토용, 이번 브랜치에서는 직접 반영하지 않음):
  - `02-business-rules.md`의 "다른 모듈과의 경계" 아래에 게시판 상세 규칙 추가:
    - `BD-001` 게시글 유형 — 게시글은 `일반`과 `공지`로 구분한다.
    - `BD-002` 일반글 작성 — 재직 사원은 일반글을 작성할 수 있다.
    - `BD-003` 공지 작성 권한 — 공지는 해당 분류의 작성 권한을 가진 역할만 작성한다.
    - `BD-004` 공지 분류 — 경영·인사·급여·부서 등 업무 목적에 따라 분류한다.
    - `BD-005` 게시글 필수값 — 제목·내용 필수, 제목 100자 이하.
    - `BD-006` 수정·삭제 권한 — 작성자 본인 또는 시스템관리자.
    - `BD-007` 공지 열람 범위 — 모든 재직 사원 열람 가능, `부서` 분류는 열람 제한이 아니라
      작성자 소속 표시용.
    - `BD-008` 공지 카테고리 자동 고정 — 작성 시점에 역할 기준으로 자동 결정, 변경 불가.
  - `03-feature-specification.md`에 `FN-BD-001`~`007` 표(기능·수행 주체·관련 규칙) 추가.
  - `04-detailed-features.md`에 "Board 상세 흐름" 절 추가(공지 분류 자동 결정, 수정·삭제
    권한, **소프트 삭제**로 처리한다는 점 — 과거 기여 초안에는 하드 삭제로 잘못 적혀 있었음).
  - `08-table-specification.md`의 게시판 섹션에 `board_posts.deleted_at` 컬럼과
    `board_comments` 테이블(신규) 추가, "Django 모델 또는 생성 마이그레이션이 없다"는
    설명을 "있음"으로 갱신.
  - 신규 역할 코드 `MANAGEMENT_OFFICER_ROLE`("MANAGEMENT_OFFICER"),
    `PAYROLL_MANAGER_ROLE`("PAYROLL_MANAGER")를 `roles` 테이블 관련 문서(해당 시)에 반영.
