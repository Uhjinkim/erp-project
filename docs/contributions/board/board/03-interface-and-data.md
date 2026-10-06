# 인터페이스와 데이터 영향

## API·권한 변경

모든 엔드포인트는 `IsAuthenticated`이며 사번은 기존
`workforce.presentation.permissions.request_employee_no`로 얻는다.

| 메서드 | 경로 | 용도 |
| --- | --- | --- |
| GET, POST | `/api/board/posts/` | 게시글 목록, 작성 |
| GET, PATCH, DELETE | `/api/board/posts/<post_id>/` | 상세, 수정, 소프트 삭제 |
| GET, POST | `/api/board/posts/<post_id>/comments/` | 댓글 목록, 댓글·답글 작성 |
| PATCH, DELETE | `/api/board/comments/<comment_id>/` | 댓글 수정, 소프트 삭제 |
| GET | `/api/board/notice-categories/eligible/` | 로그인 사원이 작성 가능한 공지 분류 코드 목록 |

- 게시글·댓글 응답에 `writer_name`을 포함한다(`Employee.person.name`을 `select_related`로
  조인, 스키마 변경 아님).
- `notice-categories/eligible/`은 `{"categories": ["PAYROLL", ...]}` 형태이며, 비어 있으면
  프론트가 게시글 유형·공지 분류 선택창을 숨긴다.

## 스키마·migration 변경

- `board_posts`, `board_notice_categories`는 공유 DB에 이미 존재하던 테이블이다. 실제 컬럼명
  (`writer_emp_no`, `notice_category_code`)과 FK 구조에 맞췄다.
- `board/migrations/0001_initial.py`: 두 기존 테이블을 `SeparateDatabaseAndState`로 상태만
  등록한다(실제 DDL 없음).
- `board/migrations/0002_postmodel_deleted_at_commentmodel.py`:
  `board_posts.deleted_at` 컬럼 추가, `board_comments` 신규 테이블 생성.
- 적용 상태: `sqlmigrate`로 DDL을 먼저 공개하고 사용자 승인 후 공유 개발 DB
  (`erp_dev.public`)에 `migrate board`로 적용 완료(2026-10-01).
- `board_notice_categories`는 빈 테이블이다. 코드 4건의 시드 전까지 공지 작성은 FK 제약으로
  운영 DB에서 실패한다.

## 환경변수·인프라 영향

- 없음. 기존 세션 인증과 SSH 터널 경로를 그대로 사용한다.
- 프론트 확인은 `scripts/start-dev.ps1`(nginx 8080)로 띄워야 한다. Vite(5173)와 Django(8000)를
  따로 띄우면 cross-origin이 되어 로그인 시 CSRF Origin 검사에서 403이 난다.
