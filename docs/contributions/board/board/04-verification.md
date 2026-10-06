# 검증

## 실행한 테스트

- Backend(`backend/`)
  - `uv run pytest`: 전체 65개 통과(게시판 domain/service/api 포함)
  - `uv run ruff check .`: 통과
  - `uv run python manage.py check`: 이상 없음
  - `uv run python manage.py makemigrations --check --dry-run`: 변경 없음
- Frontend(`frontend/`)
  - `bun run lint`: 통과
  - `bun run build`: 통과
- 공유 개발 DB
  - `migrate board` 적용 후 `showmigrations board`에서 `0001`, `0002` 모두 `[X]`
  - `information_schema` 읽기 전용 조회로 `board_posts.deleted_at`, `public.board_comments`
    존재 확인

## 주요 테스트 대상

- `tests/test_board_domain.py`: 제목 100자·필수값, 작성자/관리자 수정·삭제 권한, 댓글 길이,
  답글 깊이 제한
- `tests/test_board_service.py`: 공지 자격 검증, 소프트 삭제 후 목록·상세 미노출, 댓글·답글
  생성과 권한, 삭제 게시글에 댓글 불가
- `tests/test_board_api.py`: 게시글 CRUD 흐름, 공지 권한 403, 댓글·답글·중첩 답글 400,
  `notice-categories/eligible/`이 역할 배정에 따라 `[]` / `["PAYROLL"]`을 반환

## 남은 검증

- `board_notice_categories` 시드 후 운영 DB에서 공지 작성 동작 확인
- 프론트 게시판 화면 자동화 E2E 테스트(현재 수동 확인만 수행)
