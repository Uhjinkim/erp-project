# 검증

## 실행한 테스트

- Backend(`backend/`)
  - `uv run pytest`: 전체 312개 통과(게시판 domain/service/api 43개 포함, 2026-10-13)
  - `uv run ruff check .`: 통과
  - `uv run python manage.py check`: 이상 없음
  - `uv run python manage.py makemigrations --check --dry-run`: 변경 없음
- Frontend(`frontend/`)
  - `bun run test`: 12개 통과(게시판 `tests/board.test.ts` 4개 포함)
  - `bun run lint`: 통과
  - `bun run build`: 통과
- 공유 개발 DB
  - `migrate board` 적용 후 `showmigrations board`에서 `0001`~`0003` 모두 `[X]`
  - `information_schema` 읽기 전용 조회로 `board_posts.deleted_at`, `public.board_comments`
    존재 확인

## 주요 테스트 대상

- `tests/test_board_domain.py`: 제목 100자·필수값, 작성자/관리자 수정·삭제 권한, 댓글 길이,
  답글 깊이 제한
- `tests/test_board_service.py`: 공지 자격 검증, 소프트 삭제 후 목록·상세 미노출, 댓글·답글
  생성과 권한, 삭제 게시글에 댓글 불가
- `tests/test_board_api.py`: 게시글 CRUD 흐름, 공지 권한 403, 댓글·답글·중첩 답글 400,
  `notice-categories/eligible/`이 역할 배정에 따라 `[]` / `["PAYROLL"]`을 반환, 게시글별
  `comment_count`, 경영담당자의 타인 글·댓글 삭제 204와 수정 403, 작성자·타인·경영담당자별
  `can_edit`·`can_delete`(목록·상세·댓글)
- `frontend/tests/board.test.ts`: 게시판 메뉴가 목록·작성 두 화면뿐인지, 글 보기 주소
  (`board-list?postId=`)가 목록 화면으로 해석되는지, `postId`는 양의 정수만 허용하는지,
  제목·작성자 검색 필터

## 남은 검증

- 브라우저에서 게시판 화면을 직접 확인하지 않았다. 목록→글 보기→인라인 수정→삭제, 게시글 작성의
  일반글/공지 선택, 댓글·답글,
  직접 URL·새로고침·뒤로가기, 권한별 버튼 노출, 로딩·오류·권한 없음 상태를 수동 검수해야 한다.
- 공유 개발 DB에서 실제 화면으로 공지 작성 동작 확인(분류 시드 적용 완료)
- 일반 사원·경영담당자·인사관리자·급여담당자·시스템관리자별 합성 응답 검증(안내서 10장)
- 프론트 컴포넌트·화면 자동화 테스트는 없다(현재 테스트는 순수 로직만 대상)
