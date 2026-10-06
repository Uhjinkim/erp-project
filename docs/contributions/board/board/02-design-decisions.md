# 설계 결정

## 관련 규칙·기능 ID

- 비즈니스 규칙: `BD-001`~`BD-008`
- 기능 명세: `FN-BD-001`~`FN-BD-007`

## 도메인·애플리케이션 결정

- 게시글 유형은 `일반`/`공지`로 구분하고(`BD-001`), 공지만 업무 분류를 가진다.
- 공지 분류는 작성자의 workforce 역할/조직 구조로 판정한다(`BD-003`, `BD-004`, `BD-008`).
  - 경영 → `MANAGEMENT_OFFICER_ROLE`("MANAGEMENT_OFFICER")
  - 인사 → 기존 `HR_MANAGER_ROLE`("HR_MANAGER")
  - 급여 → `PAYROLL_MANAGER_ROLE`("PAYROLL_MANAGER")
  - 부서 → `Department.head`가 본인인 경우(별도 Role 레코드 없음)
- 공지 분류 코드는 `MANAGEMENT`/`HR`/`PAYROLL`/`DEPARTMENT`로 정했다. workforce의
  `Role.role_code`처럼 영문 코드와 한글 표시명을 분리하는 관례를 따랐다.
- 한 사원이 공지 자격 역할을 여러 개 보유하면, 클라이언트가 보낸 분류가 보유 자격 집합에
  속하는지만 검증한다(자격이 하나면 사실상 자동 고정). 이 선택 로직은 `BD-008` 원문에 없는
  구현 디테일이므로 다중 역할 실사례가 나오면 제품 결정을 재확인해야 한다.
- 공지 작성 가능 여부의 판단은 백엔드 한 곳(`WorkforceGateway.eligible_notice_categories`)에만
  둔다. 프론트는 이 결과를 조회해 화면 분기에만 사용하고, 권한 규칙을 다시 구현하지 않는다.
- 수정·삭제는 작성자 본인 또는 시스템관리자만 가능하다(`BD-006`). 시스템관리자는 새
  workforce Role을 만들지 않고 기존 `request.user.is_superuser` 관례를 재사용한다.
- 공지 분류는 생성 시점에 고정되며 수정 API는 title/content만 받는다.
- 게시글 삭제는 소프트 삭제다. 실제 DB 스키마 확인 직후 하드 삭제로 임시 전환했다가 사용자
  지시로 `deleted_at` 컬럼을 추가해 소프트 삭제로 되돌렸다.
- 댓글은 `parent_comment_id`로 1단계 답글만 허용한다(답글에 답글 금지,
  `NestedReplyNotAllowedError`). 댓글도 소프트 삭제로 처리한다.
