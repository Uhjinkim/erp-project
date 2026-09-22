# Board 명세 구현 대응표

- Notion 원문(비즈니스 규칙): <https://app.notion.com/p/3d78eced448d81528023db7f8dd1b49a>
- 점검일: 2026-09-22

## 현재 구현

- 게시글은 `일반`/`공지` 두 유형으로 구분하며(`BD-001`), 공지만 업무 분류(`경영`/`인사`/
  `급여`/`부서`)를 가진다.
- 재직 사원 여부는 `workforce.infrastructure.gateways.DjangoWorkforceQueryGateway`를 재사용해
  판정한다(vacation 모듈과 동일한 연동 방식).
- 공지 작성 자격은 다음과 같이 workforce 역할/구조에 매핑한다.
  - 경영 — `MANAGEMENT_OFFICER_ROLE`("MANAGEMENT_OFFICER") 활성 보유
  - 인사 — 기존 `HR_MANAGER_ROLE`("HR_MANAGER") 활성 보유
  - 급여 — `PAYROLL_MANAGER_ROLE`("PAYROLL_MANAGER") 활성 보유
  - 부서 — `Department.head`가 본인인 경우(부서장), 별도 Role 레코드 없음
- 시스템관리자 권한(`BD-006`)은 새 workforce Role을 만들지 않고 `workforce/presentation/permissions.py`의
  `IsHRManager`가 이미 쓰는 `request.user.is_superuser` 관례를 재사용한다.
- 수정·삭제는 작성자 본인 또는 `is_superuser`만 가능하며, 삭제는 소프트 삭제(`deleted_at`)로
  처리해 레코드를 보존한다.
- 공지 분류는 생성 시점에 고정되며 수정 API는 title/content만 받는다.

## 구현 가정(노션에 명시되지 않음)

- 한 사원이 공지 자격 역할을 두 개 이상 보유한 경우(예: 부서장이면서 인사관리자), 시스템은
  "자동 결정"을 작성 시점 강제 단일 선택으로 구현한다 — 클라이언트가 `notice_category`를
  지정하면 서버는 그 값이 작성자가 보유한 자격 집합에 속하는지만 검증한다. 자격이 하나뿐이면
  선택의 여지가 없어 사실상 자동 고정과 동일하다. 이 우선순위/선택 로직 자체는 `BD-008`
  원문에 없는 구현 디테일이므로, 실제 다중 역할 사례가 나오면 제품 결정을 다시 확인해야 한다.

## 후속 구현

- 댓글, 첨부파일, 조회수 등은 이번 MVP 범위에서 제외했다(사용자 확정).
- 실제 PostgreSQL 스키마 적용 전에는 별도 staging에서 migration을 리허설하고 승인받는다.
