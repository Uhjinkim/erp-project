# Payroll 명세 구현 대응표

- Notion 비즈니스 규칙 원문: <https://app.notion.com/p/3d78eced448d81528023db7f8dd1b49a>
- Notion 기능 명세 원문: <https://app.notion.com/p/3d78eced448d8118bd7ce952069417ed>
- Notion 핵심 기능 상세 원문: <https://app.notion.com/p/3d78eced448d81018ff7c3cf39e01776>
- Notion 미확정 정책 원문: <https://app.notion.com/p/3d78eced448d81c0be0ff8f95b5ee9c3>
- 점검일: 2026-09-22

## 명세 확보 방법에 대한 참고

이 문서를 작성한 시점에는 Notion MCP 커넥터가 인증되지 않아 세션에서 Notion 원문을
직접 조회할 수 없었다. `PY-001`~`PY-009`, `FN-PY-001`~`FN-PY-007`의 상세 내용은 급여
모듈 담당자가 Notion 페이지에서 직접 내보내 전달한 파일을 근거로 반영했다. 정산일자
정책(아래 참고)은 Notion에 남아 있던 미확정 안건을 담당자가 이번 세션에서 확정해
전달한 결정이다. Notion 원문 자체는 팀이 커넥터 인증 후 별도로 갱신해야 한다.

## 현재 구현

- `payroll` Django app을 `domain/`, `application/`, `infrastructure/`, `presentation/`
  네 계층으로 분리했다. 루트 `models.py`/`admin.py`는 Django 자동 탐색용 re-export
  진입점이다(workforce/vacation과 동일한 패턴).
- 급여 정산은 `PayrollStatement`(사원×정산월 1건, `emp_no`+`period` UNIQUE)와
  `PayrollItem`(구성항목별 금액), `PayrollHistory`(전 이력) 세 테이블로 모델링했다.
  세 테이블 모두 공유 PostgreSQL에 아직 존재하지 않는 신규 테이블이라 legacy
  state-only 기법을 쓰지 않고 일반 `makemigrations`로 생성했다(`PY-002`,
  `HR-005`의 급여 데이터 보존 요구와 정합).
- 급여 구성항목은 `PayrollComponentType` 참조 테이블로 관리한다(`PY-003`). 초기
  데이터 migration으로 기본급/고정수당/초과근무수당(지급)과 국민연금/건강보험(장기요양보험
  포함)/고용보험(공제) 6종을 등록했다 — 담당자가 지정한 급여 구성항목 범위
  (기본급+고정수당, 변동수당, 4대보험 공제)를 반영한 것이며, 실제 금액은 급여담당자가
  `FN-PY-002`에 따라 건별로 직접 입력한다. 산재보험은 국내법상 원칙적으로 사업주 전액
  부담이라 근로자 공제 항목에서 제외했다; 소득세 등 세금 공제 항목은 담당자가 이번
  범위에서 선택하지 않아 제외했다.
- 상태는 `작성중`/`확정` 두 가지만 데이터로 저장한다. Notion의
  "작성/정산중 → 확정 → 확정취소 → 작성/정산중 → 재확정" 흐름 중 확정취소·재확정은
  별도 상태가 아니라 `PayrollHistory.action`으로 구분되는 이벤트로 구현했다(`생성`,
  `구성항목 수정`, `확정`, `확정취소`, `재확정`). 확정 후 재확정 여부는 이전 확정
  이력의 존재로 판정한다.
- `PY-004` 식별자 불변: `statement_id`는 `BigAutoField`이며 변경 API를 제공하지 않는다.
- `PY-005`~`PY-007`: 확정 상태에서는 `PayrollStatement.replace_items()`가
  `InvalidPayrollTransitionError`를 발생시켜 직접 수정을 막는다. 확정취소는 사유가
  필수이며, 생성·구성항목 수정·확정·확정취소·재확정 모두 `PayrollHistory`에 처리자·
  시각과 함께 기록한다(`모든 정정은 이력으로 남긴다`, 01번 문서).
- `PY-008`: `PayrollService.get()`/`history()`는 본인이거나 급여담당자가 아니면
  `PayrollPermissionError`를 발생시킨다.
- `PY-009` / `FN-PY-001` 반올림: 원 단위 미만 금액은 최종 지급액(`net_pay`) 계산
  단계에서만 올림 처리한다(`payroll/domain/policies.py`의 `round_up_to_won`,
  `ROUND_CEILING`). 구성항목별 금액 자체는 올림하지 않는다.
- **정산일자 정책(2026-09-22, 담당자 확정)**: 매월 25일이며, 25일이 토·일요일이거나
  `PublicHoliday` 참조 테이블에 등록된 공휴일이면 직전 평일로 당긴다
  (`resolve_payment_date`). 공휴일 데이터는 초기 시드 없이 빈 테이블로 시작하며,
  실제 국내 공휴일 목록을 신뢰성 있게 확보하지 못해 비워 두었다 — HR/급여 담당자가
  Django admin에서 직접 등록하거나 후속 작업으로 공휴일 API 연동이 필요하다.
- 급여담당자 권한은 workforce의 기존 `Role`/`EmployeeRole` 데이터 모델을 그대로
  재사용한다. `workforce/migrations/0003_payroll_manager_role.py`가
  `PAYROLL_MANAGER`("급여 담당자") 역할을 시드한다(기존 `HR_MANAGER`,
  `HR_LEAVE_APPROVER` 시드 migration과 동일한 패턴). 역할 부여/회수는 이미 있는
  `POST /api/workforce/employees/{emp_no}/roles/` API를 그대로 쓴다 — payroll
  앱에 별도 역할 관리 API를 추가하지 않았다.
- 인증·식별은 workforce/accounts가 이미 구축한 실제 세션 인증을 그대로 썼다(vacation
  모듈의 개발용 `X-Employee-No` 헤더 방식은 쓰지 않음). `IsPayrollManager` 권한과
  `request_employee_no()`는 workforce의 기존 구현을 재사용한다.
- 테스트는 domain(순수 함수·엔티티) → application(fake UnitOfWork/gateway) →
  presentation(APIClient + SQLite) 순서로 구성했고, `test_payroll_architecture.py`가
  workforce와 동일한 방식으로 domain/application의 바깥 계층 import를 차단한다.
- `payroll`은 `workforce.Employee`에 FK로 연결되는 신규 스키마이므로, 테스트에서는
  workforce와 마찬가지로 `MIGRATION_MODULES["payroll"] = None`으로 두어 SQLite
  테스트 DB가 모델을 직접 생성하게 했다. workforce가 테스트에서 migration 없이
  동작하는 상태에서, payroll의 실제 migration이 `workforce.0003_payroll_manager_role`을
  참조하면 Django migration 그래프가 깨지기 때문이다. 데이터 시드
  migration(구성항목, `PAYROLL_MANAGER` 역할)도 테스트에서는 적용되지 않으므로,
  테스트는 필요한 `PayrollComponentTypeModel`/`Role` 데이터를 직접 생성한다.

## 후속 구현

- 국내 공휴일 데이터 확보(수기 등록 또는 외부 API 연동)와 `PublicHoliday` 데이터
  운영 방침 확정
- 실제 4대보험 요율·소득세 등 법정 공제 자동계산이 필요해지면 별도 정책 확정 후
  `PayrollComponentType`에 계산식 기반 항목 추가 검토(현재는 급여담당자 수기 입력)
- 급여명세 PDF/출력, 급여 공지(`FN-BD-007`, `BD-008`) 연동 등 급여-게시판 경계 기능
- 공유 PostgreSQL에 실제 스키마를 적용하기 전 staging 리허설과 승인 절차
- Notion MCP 인증 완료 후 이번 세션에서 반영한 급여 상세 규칙과 정산일자 결정을
  Notion 원문과 교차 검증
