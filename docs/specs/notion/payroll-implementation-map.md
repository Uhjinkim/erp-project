# Payroll 명세 구현 대응표

- Notion 비즈니스 규칙 원문: <https://app.notion.com/p/3d78eced448d81528023db7f8dd1b49a>
- Notion 기능 명세 원문: <https://app.notion.com/p/3d78eced448d8118bd7ce952069417ed>
- Notion 핵심 기능 상세 원문: <https://app.notion.com/p/3d78eced448d81018ff7c3cf39e01776>
- Notion 미확정 정책 원문: <https://app.notion.com/p/3d78eced448d81c0be0ff8f95b5ee9c3>
- 점검일: 2026-09-23

## 명세 확보 방법에 대한 참고

Notion MCP 커넥터는 이 환경에서 인증이 불가능하며 앞으로도 계속 불가능할 것으로 안내받았다.
따라서 Notion 원문이 필요할 때는 MCP 인증을 기다리지 않고, 급여 모듈 담당자에게 직접
질문해 확인한다. `PY-001`~`PY-009`, `FN-PY-001`~`FN-PY-007`의 상세 내용은 담당자가 Notion
페이지에서 직접 내보내 전달한 파일을 근거로 반영했다. 정산일자 정책과, 아래에서 다루는
`payroll_items`/`payroll_history`의 상태값 3종(모두 실제 DB에서 읽었을 때 인코딩이 깨져
있었다)은 담당자가 이번 세션에서 직접 확인해 전달한 값이다. Notion 원문 자체는 팀이 별도
경로로 갱신해야 한다.

## 중요: 급여 테이블은 이미 존재하는 legacy 테이블이다

**2026-09-22 최초 구현에서는 이 사실을 놓쳤다.** 급여 관련 legacy 테이블은 저장소 루트의
`erp_dev.md`(2026-09-20 작성) ERD에 이미 문서화되어 있었지만, 급여 모듈을 처음 설계할 때
이 문서를 확인하지 않고 `payroll_statements`, `payroll_component_types` 등 새 이름의
테이블을 만드는 일반 migration으로 구현했다. 그 결과 실제 공유 PostgreSQL에는 해당
테이블이 없어 급여 관련 API 호출이 모두 500 에러로 실패했다(2026-09-23 사용자 보고로
발견, 상세 경위는 `docs/reports/2026-09-23_급여_레거시_스키마_불일치_수정_보고서.md`
참고).

**공유 PostgreSQL에 이미 존재하는 실제 급여 테이블 4개** (모두 읽기 전용으로 확인):

- `payrolls`: `payroll_id`(PK), `emp_no`(FK→employees), `pay_yyyymm`(varchar(6),
  `^[0-9]{6}$` CHECK), `pay_date`, `total_pay`, `total_deduct`, `net_pay`(CHECK
  `net_pay = total_pay - total_deduct` 및 3개 필드 모두 0 이상), `status`(CHECK
  `작성중`/`확정`), `confirmed_by`(FK→employees, nullable), `confirmed_at`.
  `UNIQUE(emp_no, pay_yyyymm)`.
- `payroll_details`: `detail_id`(PK), `payroll_id`(FK→payrolls, `ON DELETE RESTRICT`),
  `item_code`(FK→payroll_items), `amount`(CHECK 0 이상). `UNIQUE(payroll_id, item_code)`.
- `payroll_items` (구성항목 마스터): `item_code`(PK), `item_name`, `item_type`(CHECK
  `지급`/`공제`), `is_active`.
- `payroll_history`: `history_id`(PK), `payroll_id`(FK→payrolls), `action`(CHECK
  `확정`/`확정취소`/`재확정`/`수정` — **`생성`은 허용값에 없다**), `actor_emp_no`
  (FK→employees), `reason`(varchar(255), nullable), `changed_at`.

이 문서를 처음 작성했을 때 `pg_get_constraintdef`로 읽은 CHECK 제약의 한글 값이 터미널에
깨져 보여 담당자에게 직접 확인받았다(작성중/확정, 지급/공제, 확정/확정취소/재확정/수정).
실제로는 DB에 저장된 값 자체는 정상(UTF-8)이었고, 셸 출력 과정에서만 깨져 보인 것으로
추정된다 — 파일로 저장해 다시 읽었을 때는 정상 표시됐다.

## 현재 구현 (2026-09-23 수정 반영)

- `payroll` Django app을 `domain/`, `application/`, `infrastructure/`, `presentation/`
  네 계층으로 분리했다. 루트 `models.py`/`admin.py`는 Django 자동 탐색용 re-export
  진입점이다(workforce/vacation과 동일한 패턴).
- `PayrollStatementModel`(`payrolls`), `PayrollDetailModel`(`payroll_details`),
  `PayrollComponentTypeModel`(`payroll_items`), `PayrollHistoryModel`(`payroll_history`)
  모두 workforce/vacation과 동일하게 **state-only migration**(`SeparateDatabaseAndState`,
  `database_operations=[]`)으로 등록한다. `payroll/migrations/0001_initial.py`가 이
  네 모델의 상태만 등록하며 실제 DDL은 실행하지 않는다. 컬럼 단위로 Django 모델과 실제
  DB를 대조해 불일치 0건을 확인했다.
- `payroll_public_holidays`만 legacy에 대응하는 테이블이 없는 **완전히 새 테이블**이라
  `payroll/migrations/0002_public_holiday.py`가 일반 `CreateModel`로 생성한다.
- 급여 구성항목은 기존 `payroll_items` 테이블을 그대로 참조한다(`PY-003`). `item_type`
  컬럼이 지급/공제 구분을 담당하므로 `PayrollItem`(도메인 엔티티)의 `category`는
  `payroll_details`가 아니라 `payroll_items`와의 join으로 얻는다 — `payroll_details`
  자체에는 category 컬럼이 없다. `payroll/migrations/0003_seed_components.py`가
  기본급/고정수당/초과근무수당(지급)과 국민연금/건강보험(장기요양보험 포함)/고용보험(공제)
  6종을 `get_or_create`로 시드한다(최초 0건이던 것 확인 후 시드, 담당자가 지정한 구성항목
  범위 반영). 실제 금액은 급여담당자가 `FN-PY-002`에 따라 건별로 직접 입력한다.
  산재보험은 국내법상 원칙적으로 사업주 전액 부담이라 근로자 공제 항목에서 제외했다;
  소득세 등 세금 공제 항목은 담당자가 이번 범위에서 선택하지 않아 제외했다.
- 상태는 `작성중`/`확정` 두 가지만 데이터로 저장한다. Notion의
  "작성/정산중 → 확정 → 확정취소 → 작성/정산중 → 재확정" 흐름 중 확정취소·재확정은
  별도 상태가 아니라 `PayrollHistory.action`으로 구분되는 이벤트로 구현했다. **실제
  `payroll_history` 테이블의 CHECK 제약에는 `생성`이 없으므로, 급여 생성 시점에는
  이력을 남기지 않는다** — 기록되는 action은 `확정`, `확정취소`, `재확정`, `수정`(구성항목
  변경) 4가지뿐이다. 확정 후 재확정 여부는 이전 확정 이력의 존재로 판정한다.
- `PY-004` 식별자 불변: `statement_id`(`payroll_id`)는 `BigAutoField`이며 변경 API를
  제공하지 않는다.
- (2026-09-23 추가) `FN-PY-001`/`FN-PY-002`: `POST /api/payroll/statements/`가
  `items`를 선택적으로 함께 받아 급여 생성과 구성항목 입력을 한 번에 처리할 수 있다.
  프론트엔드는 활성 구성항목 전체를 입력 필드로 보여주고(드롭다운으로 하나씩 고르는
  방식 아님), 값을 비운 항목은 저장하지 않는다. 기본급/고정수당/초과근무수당/
  국민연금/건강보험/고용보험 6종에 "상여"(`BONUS`, 지급)를 추가해 총 7종이다
  (`payroll/migrations/0004_seed_bonus_component.py`).
- (2026-09-23 추가) 급여 조회 API 응답에 `employee: {emp_no, name, position_name}`
  요약 정보를 포함한다(workforce의 `Employee`/`Person`/`Position`을 조회 전용으로
  join). 프론트엔드가 급여명세서 형식(지급내역/공제내역 2단 표, 지급총액·공제액 계·
  차인지급액)으로 표시하는 데 사용한다. 주민등록번호는 시스템에 저장하지 않으므로
  표시하지 않는다.
- `PY-005`~`PY-007`: 확정 상태에서는 `PayrollStatement.replace_items()`가
  `InvalidPayrollTransitionError`를 발생시켜 직접 수정을 막는다. 확정취소는 사유가
  필수이며, 구성항목 수정·확정·확정취소·재확정 모두 `PayrollHistory`에 처리자·시각과
  함께 기록한다. `change_summary`라는 별도 컬럼은 실제 테이블에 없으므로, 구성항목
  변경 요약은 `reason` 컬럼(varchar(255), 초과 시 잘라서 저장)에 담는다.
- `PY-008`: `PayrollService.get()`/`history()`는 본인이거나 급여담당자가 아니면
  `PayrollPermissionError`를 발생시킨다.
- `PY-009` / `FN-PY-001` 반올림: **`net_pay`에는 더 이상 별도 올림 처리를 적용하지
  않는다.** 실제 `payrolls` 테이블이 `net_pay = total_pay - total_deduct`를 정확히
  일치하도록 CHECK 제약으로 강제하기 때문이다. 원 단위 미만 금액 올림이 필요한 해외
  화폐 환산 케이스는 현재 입력 경로에서 지원하지 않으며, 필요해지면 금액을 입력하는
  시점에 올림을 적용해야 한다(계산 결과 단계에서 임의로 조정할 수 없다).
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
  workforce와 동일한 방식으로 domain/application의 바깥 계층 import를 차단한다. **다만
  테스트는 SQLite에 모델을 직접 생성하는 방식이라(`MIGRATION_MODULES["payroll"]=None`),
  이번처럼 Django 모델이 실제 legacy 테이블과 어긋나는 문제는 테스트만으로는 잡히지
  않는다.** 새 legacy 매핑을 만들 때는 배포 전 반드시 `information_schema`로 실제
  컬럼과 Django 모델 상태를 대조해야 한다(workforce-implementation-map.md와 동일한
  원칙).
- `payroll`은 `workforce.Employee`에 FK로 연결되므로, 테스트에서는 workforce와
  마찬가지로 `MIGRATION_MODULES["payroll"] = None`으로 두어 SQLite 테스트 DB가
  모델을 직접 생성하게 했다. `payroll.0001_initial`이 `workforce.0001_initial`에
  의존하므로(Employee 모델 생성 시점), workforce가 테스트에서 migration 없이 동작하는
  상태에서도 그래프 충돌이 없다. 데이터 시드 migration(구성항목, `PAYROLL_MANAGER`
  역할)도 테스트에서는 적용되지 않으므로, 테스트는 필요한
  `PayrollComponentTypeModel`/`Role` 데이터를 직접 생성한다.
- 공유 개발 DB(`erp_dev`)에는 2026-09-23에 사용자 승인을 받아 `payroll_public_holidays`
  테이블 생성과 `payroll_items` 6건 시드, `roles`에 `PAYROLL_MANAGER` 시드를 적용했다.
  기존 `payrolls`/`payroll_details`/`payroll_history`는 이번 적용 전후 모두 0건이며,
  실제 DDL 변경 없이 Django 모델 상태만 등록됐다.

## 후속 구현

- 국내 공휴일 데이터 확보(수기 등록 또는 외부 API 연동)와 `PublicHoliday` 데이터
  운영 방침 확정
- 실제 4대보험 요율·소득세 등 법정 공제 자동계산이 필요해지면 별도 정책 확정 후
  `PayrollComponentType`에 계산식 기반 항목 추가 검토(현재는 급여담당자 수기 입력)
- 급여명세 PDF/출력, 급여 공지(`FN-BD-007`, `BD-008`) 연동 등 급여-게시판 경계 기능
- Notion 원문과의 교차 검증: MCP 인증이 불가능하므로, 이번 세션에서 확정한 정산일자
  정책과 `payroll_history.action`/`payroll_items.item_type`/`payrolls.status` 값은
  급여 모듈 담당자가 Notion 페이지를 직접 열어 다시 한 번 대조해 주는 방식으로만
  검증할 수 있다.
