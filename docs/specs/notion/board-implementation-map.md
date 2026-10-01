# Board 명세 구현 대응표

- Notion 원문(비즈니스 규칙): <https://app.notion.com/p/3d78eced448d81528023db7f8dd1b49a>
- 점검일: 2026-10-01 (공유 DB 실제 스키마 확인 후 설계 교체)

## 실제 DB 스키마 (읽기 전용 확인, 2026-10-01)

`board_posts`, `board_notice_categories` 테이블이 이미 공유 PostgreSQL에 존재한다. 최초
구현은 이 사실을 모른 채 작성되어 실제 스키마와 달랐고(소프트 삭제용 컬럼 없음, 분류가
FK 대신 문자열), 사용자가 확인해준 아래 정의에 맞춰 모델/마이그레이션을 다시 작성했다.

```
board_notice_categories: notice_category_code (PK, VARCHAR20), category_name (VARCHAR50)
board_posts: post_id (PK), writer_emp_no (FK -> employees), post_type (VARCHAR10, default '일반'),
             notice_category_code (FK -> board_notice_categories, nullable), title (VARCHAR100),
             content (TEXT), created_at (NOT NULL), updated_at (nullable)
```

`board_notice_categories`는 확인 시점에 행이 하나도 없었다. 코드 값(`MANAGEMENT`/`HR`/
`PAYROLL`/`DEPARTMENT`)은 이번에 정했으며, 실제 행 INSERT(시드)는 공유 DB 쓰기 작업이라
이번 범위에서 제외했다 — 공지 작성 기능은 해당 코드의 행이 실제로 들어가기 전까지는 FK
제약으로 인해 운영 DB에서 동작하지 않는다(자동화 테스트는 SQLite에 동일한 코드로 행을
직접 만들어 검증한다).

마이그레이션(`board/migrations/0001_initial.py`)은 `workforce`/`vacation`의 레거시 테이블과
동일하게 `SeparateDatabaseAndState(database_operations=[], ...)`로 작성해 Django 상태만
등록하고 실제 DDL은 실행하지 않는다.

**2026-10-01 적용 완료**: `sqlmigrate`로 실행될 DDL을 사용자에게 먼저 보여주고 승인받은 뒤,
공유 DB에 `migrate board`를 실행했다(`0001_initial`은 상태 등록만, `0002_postmodel_deleted_at_commentmodel`은
`board_posts.deleted_at` 컬럼 추가 + `board_comments` 테이블 생성 — 둘 다 적용 완료). 적용 후
`/api/health/`로 DB 연결 정상 확인.

## 현재 구현

- 게시글은 `일반`/`공지` 두 유형으로 구분하며(`BD-001`), 공지만 업무 분류(`경영`/`인사`/
  `급여`/`부서`)를 가진다. 분류는 `board_notice_categories`를 참조하는 FK(`notice_category`)
  이며, 코드값은 영문(`MANAGEMENT`/`HR`/`PAYROLL`/`DEPARTMENT`)으로 정했다(workforce의
  `Role.role_code` 관례와 동일하게 영문 코드 + 한글 표시명 구조).
- 재직 사원 여부는 `workforce.infrastructure.gateways.DjangoWorkforceQueryGateway`를 재사용해
  판정한다(vacation 모듈과 동일한 연동 방식).
- 공지 작성 자격은 다음과 같이 workforce 역할/구조에 매핑한다.
  - 경영 — `MANAGEMENT_OFFICER_ROLE`("MANAGEMENT_OFFICER") 활성 보유
  - 인사 — 기존 `HR_MANAGER_ROLE`("HR_MANAGER") 활성 보유
  - 급여 — `PAYROLL_MANAGER_ROLE`("PAYROLL_MANAGER") 활성 보유
  - 부서 — `Department.head`가 본인인 경우(부서장), 별도 Role 레코드 없음
- 시스템관리자 권한(`BD-006`)은 새 workforce Role을 만들지 않고 `workforce/presentation/permissions.py`의
  `IsHRManager`가 이미 쓰는 `request.user.is_superuser` 관례를 재사용한다.
- 수정·삭제는 작성자 본인 또는 `is_superuser`만 가능하다. **삭제는 소프트 삭제다** —
  `board_posts.deleted_at` 컬럼 추가 마이그레이션을 공유 DB에 적용 완료했다(2026-10-01).
- 공지 분류는 생성 시점에 고정되며 수정 API는 title/content만 받는다.
- 게시글 목록 API 응답에 `writer_name`을 추가했다(`workforce.Employee.person.name`을
  `select_related`로 조인) — 프론트 "작성자로 검색"을 위한 순수 조회 확장이며 스키마 변경은
  아니다.
- 댓글/대댓글(`board_comments`, 완전히 새 테이블, 공유 DB에 생성 완료)을 추가했다.
  `parent_comment_id`로 1단계 답글만 허용하고(답글에 다시 답글 금지,
  `NestedReplyNotAllowedError`), 소프트 삭제로 처리한다. `writer_emp_no`는
  `workforce.Employee`, `post_id`는 `board_posts`를 참조하는 FK다. 이 테이블은 공유 DB에
  사전 존재가 확인되지 않아(사용자 확인) 새로 설계했다.

## 구현 가정(노션에 명시되지 않음)

- 한 사원이 공지 자격 역할을 두 개 이상 보유한 경우(예: 부서장이면서 인사관리자), 시스템은
  "자동 결정"을 작성 시점 강제 단일 선택으로 구현한다 — 클라이언트가 `notice_category`를
  지정하면 서버는 그 값이 작성자가 보유한 자격 집합에 속하는지만 검증한다. 자격이 하나뿐이면
  선택의 여지가 없어 사실상 자동 고정과 동일하다. 이 우선순위/선택 로직 자체는 `BD-008`
  원문에 없는 구현 디테일이므로, 실제 다중 역할 사례가 나오면 제품 결정을 다시 확인해야 한다.

## 후속 구현

- 첨부파일, 조회수 등은 이번 범위에서 제외했다(댓글/대댓글은 추가 완료).
- `board_notice_categories`에 `MANAGEMENT`/`HR`/`PAYROLL`/`DEPARTMENT` 행을 넣는 시드 작업이
  남아있다 — 공유 DB 쓰기이므로 별도 승인 절차 후 진행한다. 그 전까지 공지 작성은 운영 DB에서
  FK 제약으로 실패한다.
- `board_posts.deleted_at` 추가와 `board_comments` 신설은 2026-10-01에 사용자 승인을 받고
  공유 DB에 적용 완료했다(`sqlmigrate`로 DDL 선공개 → 승인 → `migrate board` 적용 → health
  check로 확인).
- 프론트엔드 게시판 탭(`frontend/src/components/BoardPanel.tsx`)을 추가했다 — 목록(제목만
  노출) → 상세(본문·댓글·본인 글이면 수정/삭제) 2단 구조, 제목/작성자 드롭다운 검색 포함.
