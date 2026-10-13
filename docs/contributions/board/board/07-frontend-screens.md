# 프론트 화면 (안내서 F5 게시판)

- 기준 문서: [프론트엔드 모듈 배정 안내서](../../../guides/frontend-module-delivery.md),
  [공통 토대 사용 계약](../../../guides/frontend-foundation-contracts.md)
- 시작 기준: `dev` 2c11c9c(공통 디자인시스템 병합 후)
- 디자인: Graphite 와이어프레임 화면 ID `board-list`, `board-detail`, `board-write`,
  `notice-write`를 참고했다. 확정 시안 버전과의 픽셀 대조는 하지 않았다.
- 업무 근거: `FN-BD-001`~`007`, `BD-001`~`008`. `BD-01`(공지 분류·복수 역할), `BD-02`(댓글
  범위)는 결정 대기.

## 메뉴와 주소 (2026-10-13 사용자 결정)

게시판 메뉴는 두 개만 둔다. 시안의 `board-detail`·`notice-write`는 별도 메뉴로 만들지 않는다.

| 메뉴 | 주소 | 내용 |
| --- | --- | --- |
| 게시판·공지 목록 (`board-list`) | `#/board/board-list` | 제목·작성자 검색, 목록 표(구분·제목·댓글 수·작성자·작성일), 게시글 작성 링크 |
| (같은 화면의 글 보기 상태) | `#/board/board-list?postId=<id>` | 목록에서 제목을 누르면 열림. 본문, 본인 글이면 그 자리에서 수정, 삭제 확인 창, 댓글·답글 |
| 게시글 작성 (`board-write`) | `#/board/board-write` | 제목·내용 작성. 공지 작성 권한이 있으면 게시글 유형(일반글/공지)과 공지 분류 선택칸 추가 |

- 글 보기는 목록 화면의 상태라 메뉴에는 나오지 않지만, 주소가 있어 새로고침·뒤로가기·직접 URL이
  동작한다. 안내서 4장의 "확인 창·drawer는 별도 URL 없이 구성할 수 있다", "39장을 39개 독립 페이지로
  만들 필요는 없다"에 근거한다.
- `postId`는 양의 정수만 허용한다. 잘못되면 "주소가 올바르지 않습니다" 안내를 보인다.
- 등록 후에는 새 글 보기로, 삭제 후에는 목록으로 이동한다.

## 파일 구성

- `features/board/BoardScreen.tsx`: 공개 진입점. `board-list`(`postId` 유무로 목록/글 보기),
  `board-write`를 선택
- `features/board/screens/`: `BoardListScreen`, `BoardDetailScreen`(글 보기·인라인 수정),
  `PostWriteScreen`(일반글·공지 작성 공용 폼)
- `features/board/components/CommentThread.tsx`: 상세 화면 전용 댓글·답글
- `features/board/boardModel.ts`: 분류 라벨, 화면 주소, `postId` 해석, 검색 필터
- `features/board/board.module.css`: CSS Modules, 공통 토큰만 사용
- 공용 UI 사용: `Card`, `Table`, `Badge`, `Button`, `Select`, `TextInput`, `Textarea`, `Alert`,
  `Spinner`, `EmptyState`, `ErrorState`, `DetailList`, `ConfirmDialog`
- 기존 `components/BoardPanel.tsx`는 위 화면으로 대체해 삭제했다.

## 권한·외부 계약

- 수정·삭제 버튼은 응답의 `can_edit`·`can_delete`로만 노출한다. 역할 문자열이나
  `is_superuser`를 프론트에서 해석하지 않는다(안내서 9장 5항).
- 게시글 작성의 유형·분류 선택칸은 `GET /api/board/notice-categories/eligible/`이 비어 있지 않을
  때만 보인다. 비어 있으면 일반글로만 작성된다.
- 수정은 글 보기에서 `can_edit`일 때 그 자리에서 제목·내용만 바꾼다(유형·분류는 변경 불가).
- 목록 API는 배열 전체를 반환한다. 검색은 클라이언트 필터이며 서버 페이지네이션은 없다.

## UI 상태

- loading: `Spinner`
- empty: 게시글 없음 / 검색 결과 없음 / 댓글 없음을 구분
- error: `ErrorState`와 다시 시도
- not-found: 삭제·잘못된 게시글(404)
- 권한별 노출: 수정·삭제 버튼, 게시글 유형·공지 분류 선택칸
- pending: 저장·삭제 버튼 `pending`, 처리 중 중복 요청 차단
- 필드 오류: 서버 `fieldErrors`의 `title`·`content`·`notice_category`를 각 입력칸에 연결
- 서버 연결 전: "서버 연결 후 …" 안내

## 공용(F0) 변경 요청

- `app/ModuleScreen.tsx`: 게시판 화면(`board-list`, `board-write`)을 `implemented`에 두고,
  게시판을 `legacy-module` 래퍼 밖에서 `BoardScreen`으로 연결했다. 이 파일은 F0 소유라 F0 검토가
  필요하다.
- `tests/routing.test.ts`: 게시판 등록 화면이 4개에서 2개로 줄어 전체 화면 수 기대값을 37에서 35로
  바꿨다. F0 소유 테스트라 F0 검토가 필요하다.
- 시안 화면 ID `board-detail`·`notice-write`를 별도 화면으로 등록하지 않았다. 안내서 4장의 화면
  수 검산(39장)과 차이가 생기므로 F0·팀 리드에게 공유한다.
- `styles/legacy.css`: 게시판 전환이 끝나 `.board-list-item`, `.board-reply`,
  `.board-comment-count` 선택자가 더 이상 쓰이지 않는다. 삭제를 F0에 요청한다(이번 변경에서
  직접 지우지 않음).

## 이번에 구현하지 않은 것

- 읽음 표시, 첨부파일, 조회수(API 없음)
- 서버 페이지네이션(현재 배열 응답)
- 공지 분류의 복수 역할 선택 규칙 확정(`BD-01` 결정 대기, 현재는 작성 가능 분류 중 선택)
