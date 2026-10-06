# 공용 문서 반영 후보

이 브랜치에서는 공용 문서를 직접 수정하지 않는다. 문서 담당자가 아래 후보를 검토해 `dev`에서
정본에 반영한다.

## Notion 원문

- 비즈니스 규칙(`BD-001`~`008`), 기능 명세(`FN-BD-001`~`007`) 페이지에 아래 상세가 반영되어
  있는지 확인
  - 비즈니스 규칙: <https://app.notion.com/p/3d78eced448d81528023db7f8dd1b49a>
  - 기능 명세: <https://app.notion.com/p/3d78eced448d8118bd7ce952069417ed>
- 댓글/대댓글은 원문 기능 명세에 없는 기능이므로 기능 ID 부여 여부 결정 필요

## 저장소 명세·README

- `docs/specs/notion/02-business-rules.md` "다른 모듈과의 경계" 아래 게시판 상세 규칙 추가
  - `BD-001` 게시글 유형 — `일반`과 `공지`로 구분
  - `BD-002` 일반글 작성 — 재직 사원 작성 가능
  - `BD-003` 공지 작성 권한 — 해당 분류의 작성 권한을 가진 역할만 작성
  - `BD-004` 공지 분류 — 경영·인사·급여·부서 등 업무 목적별 분류
  - `BD-005` 게시글 필수값 — 제목·내용 필수, 제목 100자 이하
  - `BD-006` 수정·삭제 권한 — 작성자 본인 또는 시스템관리자
  - `BD-007` 공지 열람 범위 — 모든 재직 사원 열람, `부서` 분류는 열람 제한이 아닌 작성자
    소속 표시
  - `BD-008` 공지 카테고리 자동 고정 — 작성 시점에 역할 기준으로 결정, 변경 불가
- `docs/specs/notion/03-feature-specification.md`에 `FN-BD-001`~`007` 표(기능·수행 주체·관련
  규칙) 추가
- `docs/specs/notion/04-detailed-features.md`에 "Board 상세 흐름" 추가(공지 분류 자동 결정,
  수정·삭제 권한, 소프트 삭제)
- `docs/specs/notion/06-api-specification.md`에 게시판 엔드포인트 5종 추가
  (`03-interface-and-data.md` 표 참고)
- `docs/specs/notion/08-table-specification.md` 게시판 섹션에 `board_posts.deleted_at`,
  `board_comments` 테이블 추가, "Django 모델 또는 생성 마이그레이션이 없다"는 설명 갱신
- `roles` 관련 문서에 신규 역할 코드 `MANAGEMENT_OFFICER`, `PAYROLL_MANAGER` 반영
