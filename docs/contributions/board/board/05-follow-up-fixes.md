# 후속 수정 내역

## 댓글 수정 기능이 동작하지 않음

- 증상: 댓글·답글의 "수정" 버튼을 눌러도 아무 변화가 없었다.
- 원인: 프론트가 `window.prompt()`로 수정 내용을 받았다. 임베디드 브라우저·웹뷰 등
  `prompt()`를 지원하지 않거나 막는 환경에서는 `null`이 반환되어 요청 없이 종료됐다. 백엔드
  `PATCH /api/board/comments/<id>/`는 테스트상 정상이었다.
- 해결: `window.prompt` 의존을 제거하고 게시글 수정과 같은 인라인 입력 폼(저장/취소)으로
  교체했다. 댓글과 답글 모두 적용했다(`frontend/src/components/BoardPanel.tsx`).

## 공지 작성 권한이 없는 사원에게 유형·분류 선택창이 노출됨

- 요구: 공지 작성 권한이 없으면 게시글 유형·공지 분류 선택창을 아예 보여주지 않고 일반
  글쓰기 폼만 노출한다.
- 해결:
  - Backend: `GET /api/board/notice-categories/eligible/`를 추가했다. 기존
    `WorkforceGateway.eligible_notice_categories`를 그대로 사용해 권한 규칙을 중복 구현하지
    않는다(`backend/board/presentation/views.py`, `urls.py`).
  - Frontend: 로그인 사원의 작성 가능 분류를 조회해 목록이 비어 있으면 선택창을 숨기고
    게시글 유형을 `일반`으로 고정한다. 공지 분류 선택지도 전체 4종이 아니라 작성 가능한
    분류만 보여준다(`frontend/src/api/board.ts`, `BoardPanel.tsx`).
  - 테스트: 역할 배정 여부에 따른 응답을 검증하는 API 테스트를 추가했다.
