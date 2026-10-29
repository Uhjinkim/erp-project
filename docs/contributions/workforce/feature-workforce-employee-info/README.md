# workforce / feature/workforce-employee-info 기여 문서

- 대상 모듈: `workforce`
- 작업 브랜치: `feature/workforce-employee-info` (2026-10 이후 작업은 `jyoun` 브랜치에서 이어 진행)
- 기준 브랜치: `dev`
- 상태: 작성 중 (최종 갱신 2026-10-13)

## 기능 범위

- 구현 범위:
  - `FN-HR-001` 본인 인사 정보 조회 API(`GET /api/workforce/employees/me/`)
  - `HR-001`에 따른 사원 목록·상세 조회 권한 제한
  - 인사 정보 상세 응답(부서명, 직급명, 생년월일, 성별, 주소, 급여계좌 포함)
  - `HR-002`/`FN-HR-002` 본인 연락처·주소 직접 수정(`PATCH /api/workforce/employees/me/`)
  - `HR-003`/`FN-HR-003`~`FN-HR-005`, `FN-HR-011` 사내 이메일·급여계좌 승인형 변경 요청,
    인사관리자 승인·반려, 결과·이력 조회, 요청자 취소
  - `HR-007` 사원 수정 API에서 사번 변경 차단
  - 프론트엔드 "내 인사 정보" 카드, 개인정보 변경 화면, 인사관리자용 사원 상세·변경 승인 화면
  - (2026-10-13 추가, 백엔드만) `FN-HR-006` 신규 입사자 통합 등록
  - (2026-10-13 추가, 백엔드만) `FN-HR-007` 퇴사 처리, `FN-HR-008` 퇴사자 조회, `FN-HR-009` 재입사
  - (2026-10-13 추가, 백엔드만) `FN-HR-010` 인사이력 조회·발령 등록, 최근 이력 정정·발령 취소와
    변경 기록
- 제외 범위:
  - 인사이력(`emp_history`) 본인 조회: 본인 조회 범위에 포함하지 않기로 결정. 인사관리자용 조회는
    `FN-HR-010`으로 구현
  - 신규 입사·퇴사·재입사·인사이력 프론트엔드 화면
  - 휴직·복직 전용 처리, 예약 퇴사, 퇴사 취소
  - `HR-012` 변경 요청 보존기간(후순위, Notion 기간 값 확인 후 진행)
  - 급여계좌 암호화(`employees.account_no` 포함, 인프라·보안 결정 필요)
  - 개인정보 마스킹·암호화·조회 감사로그

## 설계 결정

- 관련 규칙·기능 ID: `HR-001`~`HR-011`, `FN-HR-001`~`FN-HR-011`
- 도메인·애플리케이션 결정:
  - 조회 범위: 사원은 본인 정보만, 타인 정보는 인사관리자(`HR_MANAGER`)만 조회한다.
    부서장 예외는 두지 않는다. superuser는 기존 관리자 권한과 동일하게 허용한다.
  - 판정 규칙은 `workforce.domain.policies.can_view_employee_info`(순수 함수)에 두고,
    `workforce.application.services.can_view_employee`가 gateway로 역할을 조회해 호출한다.
  - 퇴사자 접근 차단(`HR-004`)은 기존 `ActiveEmployeeSessionAuthentication`이 담당한다.
  - 상세 조회(`retrieve`)에는 목록용 `search`, `dept_no`, `tenure_status` 필터를 적용하지 않는다.
  - 급여계좌(`bank_code`, `account_no`)는 본인 조회와 인사관리자의 타 사원 조회 응답에 모두
    포함한다.
  - 개인정보 변경 권한 분리(`HR-002`): 직접 수정 허용 항목은 `phone`, `address`이며
    `workforce.domain.personal_info`가 판정한다. 그 외 항목은 `400`으로 거절한다.
  - 변경 요청(`HR-003`): 요청 시 변경 전 값·요청값·요청시각을 `대기`로 기록하고 실제 값은
    바꾸지 않는다. 승인 시에만 반영하며 처리자·처리시각(반려 시 사유)을 기록한다.
    상태 전이는 `PersonalInfoChangeRequest` 도메인 엔티티가 담당한다(`대기`만 처리 가능,
    취소는 요청자 본인만).
  - 이메일은 요청·승인 시점 모두 사원 이메일 중복을 검사한다. 급여계좌는 은행 코드와
    계좌번호를 함께 요청해야 한다.
  - 승인 시 요청 사원이 재직 상태가 아니면 반영하지 않고 `400`을 반환한다. 해당 요청은
    인사관리자가 반려로 정리한다.
  - 사번은 불변 PK이므로 `PATCH /api/workforce/employees/{emp_no}/`에서 다른 사번을 보내면
    `400`으로 거절한다(`HR-007`). 이전에는 새 사원 행이 생성되거나 `500`이 발생했다.
- 사양에 명시되지 않아 구현에서 정한 사항(제품 확인 필요):
  - "연락처"는 `phone`만으로 본다. 내선번호(`extension_no`)는 인사관리자 관리 항목이다.
  - 사원당 `대기` 요청은 1건만 허용한다. 동시 요청은 사원 행 잠금(`select_for_update`)으로 막는다.

### 신규 입사·퇴사·재입사·인사이력 (2026-10-13)

구조는 `domain/onboarding.py`·`lifecycle.py`·`history.py`, `application/onboarding.py`·
`lifecycle.py`·`history.py`, `infrastructure/onboarding.py`·`lifecycle.py`·`history.py`·
`accounts.py`로 나눴다. 계정 생성은 `AccountGateway` 포트와 `infrastructure/accounts.py`
gateway를 거치며 domain·application은 accounts ORM을 직접 쓰지 않는다. 여러 테이블에 걸친 쓰기는
모두 하나의 트랜잭션(Unit of Work)이고 실패하면 전부 롤백한다.

- `FN-HR-006` 신규 입사 (사용자 결정 2026-10-13):
  - 사번은 DB identity 시퀀스(`employees.emp_no`)로 자동 발급하고 요청에서 받지 않는다(`HR-007`).
    처음에는 "최대 사번+1"로 정했으나, 실제 DB의 `emp_no`가 identity 컬럼임을 확인해 시퀀스
    발급으로 바꿨다. 시퀀스가 기존 최대 사번보다 뒤처져 있으면 사번을 발급하지 않고 롤백한다.
  - 필수 항목: 이름, 생년월일, 성별(`M`/`F`), 사내 이메일, 입사일, 부서, 직급, 기본급(0 이상).
    재직 상태는 `재직`으로 고정한다.
  - 계정 생성은 선택이다. 요청에 `account.password`가 있으면 사내 이메일을 로그인 ID로 계정을 만들고
    사원과 연결한다. 초기 비밀번호는 인사관리자가 입력해 별도로 전달하며 응답에 포함하지 않는다.
  - 이메일 중복은 다른 사원 이메일과 다른 계정의 로그인 이메일을 모두 검사한다(`HR-008`).
  - 최초 인사이력은 항상 입사일부터 종료일 없이 기록한다(`FN-HR-010`, `HR-010`).
  - 역할은 선택해서 함께 배정한다. 부서장 지정은 하지 않는다(역할 배정과 부서장 지정은 별개).
- `FN-HR-007` 퇴사 처리 (사용자 결정):
  - 퇴사일은 입사일 이후이면서 오늘 또는 과거만 허용한다. 이미 퇴사한 사원은 거절한다.
  - 상태와 퇴사일만 바꾼다. 역할 배정, 부서장 지정, 인사이력, 대기 중 변경 요청은 자동 정리하지
    않고 보존한다(`HR-005`). 퇴사자는 인증 단계에서 차단되고, 휴가 승인자 결정과 변경 요청 처리는
    재직 여부를 확인하므로 남은 기록이 권한으로 작동하지 않는다.
  - 연결 계정은 기존 `post_save` signal이 비활성화한다(`HR-004`).
- `FN-HR-008` 퇴사자 조회: 인사관리자 전용(`HR-005`). 다른 목록 API처럼 페이지네이션은 두지 않는다.
- `FN-HR-009` 재입사 (사용자 결정):
  - 이전 고용이 모두 퇴사 상태이고 새 입사일이 마지막 퇴사일 이후여야 한다.
  - 기존 Person에 새 사번의 고용을 추가하고 이전 사번은 재사용하지 않는다(`HR-006`).
  - 새 이메일이 필요하고 계정은 선택해서 새로 만든다. 이전 고용·계정은 비활성 상태로 보존한다.
  - 이름·생년월일·성별은 요청에 값이 있을 때만 기존 Person을 갱신한다.
  - 같은 Person의 동시 재입사는 Person 행 잠금으로 막는다.
- `FN-HR-010` 인사이력 발령 (사용자 결정):
  - 이력 기간은 시작일·종료일을 모두 포함한다(DB `EXCLUDE ... daterange(start, end, '[]')`와 동일).
  - 발령일은 오늘 또는 과거만 허용한다. 진행 중 이력을 발령일 전날로 자동 마감하고 새 이력을
    추가하며, `employees`의 현재 부서·직급도 바꾼다.
  - 이력이 없는 사원의 첫 발령은 입사일~발령일 전날 기간을 현재 부서·직급으로 함께 기록한다. 이 기간
    기본급(`previous_base_salary`)을 요청에서 받는다.
  - 부서·직급이 바뀌는 발령만 등록한다(기본급만 바뀌는 등록은 거절). 기본급은 필수다.
  - 다른 부서로 발령되면 이전 부서의 부서장 지정을 자동 해제한다. 직급만 바뀌면 유지한다.
  - 퇴사자는 발령할 수 없다. 휴직자 발령은 막을 근거가 없어 허용했다.
- `FN-HR-010` 정정·취소 (사용자 결정):
  - 진행 중인 최근 이력만 정정·취소한다. 과거 이력은 고정해 과거 평가 판정에 영향을 주지 않는다.
  - 정정: 부서·직급·기본급·발령일. 발령일을 바꾸면 직전 이력 종료일을 함께 조정한다. 첫 이력(입사일
    시작)의 시작일은 바꾸지 않는다. 직전 이력과 부서·직급이 같아지면 취소를 쓰도록 거절한다.
  - 취소: 최근 이력을 삭제하고 직전 이력을 다시 진행 중으로 만들며 현재 소속을 되돌린다. 첫 이력은
    취소할 수 없다. 이 발령으로 해제한 부서장은 자리가 비어 있고 되돌아간 소속 부서이며 재직 중일
    때만 복원한다.
  - 발령·정정·취소를 모두 `emp_history_changes`에 기록한다(정정 전·후 값, 해제·복원 부서장, 사유,
    처리자, 시각). 정정·취소 사유는 필수, 발령 사유는 선택이다.
- 사양에 명시되지 않아 구현에서 정한 사항(제품 확인 필요):
  - 고유 제약 충돌(동시 등록의 이메일 경합, 수동 입력 사번과 시퀀스 값 충돌)만 최대 3회 다시 시도하고,
    계속 충돌하면 `409`. 그 밖의 DB 제약 오류는 재시도하지 않는다.
  - 신규 입사 계정에는 프로젝트 `AUTH_PASSWORD_VALIDATORS`를 적용한다. 기존 `/api/auth/accounts/`는
    8자 이상만 확인해 기준이 다르다.
  - 재입사 대상 Person이 없으면 `404`가 아니라 `400`(`field: person_id`)으로 응답한다.

## 인터페이스와 데이터 영향

- API·권한 변경:

  | 메서드 | 경로 | 권한 | 비고 |
  | --- | --- | --- | --- |
  | `GET` | `/api/workforce/employees/` | HR 관리자 | 기존 인증 사용자에서 변경 |
  | `GET` | `/api/workforce/employees/{emp_no}/` | 본인 또는 HR 관리자 | 상세 필드 |
  | `PATCH` | `/api/workforce/employees/{emp_no}/` | HR 관리자 | 사번·이메일 변경 시 `400` |
  | `GET` | `/api/workforce/employees/me/` | 인증 사용자(본인) | 신규 |
  | `PATCH` | `/api/workforce/employees/me/` | 인증 사용자(본인) | 신규, `phone`·`address`만 |
  | `GET` | `/api/workforce/personal-info-requests/` | 본인 요청 / HR 관리자 전체 | 신규, `?status=`, `?mine=true`(본인만), `?processable=true`(처리 가능 대기 요청만) |
  | `POST` | `/api/workforce/personal-info-requests/` | 재직 사원 | 신규 |
  | `GET` | `/api/workforce/personal-info-requests/{id}/` | 요청자 또는 HR 관리자 | 신규 |
  | `POST` | `/api/workforce/personal-info-requests/{id}/approve/` | HR 관리자 | 신규 |
  | `POST` | `/api/workforce/personal-info-requests/{id}/reject/` | HR 관리자 | 신규, `reason` 선택 |
  | `POST` | `/api/workforce/personal-info-requests/{id}/cancel/` | 요청자 | 신규 |
  | `POST` | `/api/workforce/new-hires/` | HR 관리자 | 신규(2026-10-13), `FN-HR-006` |
  | `POST` | `/api/workforce/employees/{emp_no}/terminate/` | HR 관리자 | 신규(2026-10-13), `FN-HR-007` |
  | `GET` | `/api/workforce/employees/terminated/` | HR 관리자 | 신규(2026-10-13), `FN-HR-008` |
  | `POST` | `/api/workforce/persons/{person_id}/rehire/` | HR 관리자 | 신규(2026-10-13), `FN-HR-009` |
  | `GET` | `/api/workforce/employees/{emp_no}/history/` | HR 관리자 | 신규(2026-10-13), `FN-HR-010` 조회 |
  | `POST` | `/api/workforce/employees/{emp_no}/history/` | HR 관리자 | 신규(2026-10-13), 발령 등록 |
  | `POST` | `/api/workforce/employees/{emp_no}/history/{history_id}/correct/` | HR 관리자 | 신규(2026-10-13), 최근 이력 정정 |
  | `POST` | `/api/workforce/employees/{emp_no}/history/{history_id}/cancel/` | HR 관리자 | 신규(2026-10-13), 최근 발령 취소 |
  | `GET` | `/api/workforce/employees/{emp_no}/history/changes/` | HR 관리자 | 신규(2026-10-13), 발령·정정·취소 기록 |

  - 상세·본인 응답 필드: `emp_no`, `person_id`, `name`, `birth_date`, `gender`, `dept_no`,
    `dept_name`, `position_code`, `position_name`, `tenure_status`, `email`, `phone`,
    `extension_no`, `address`, `bank_code`, `account_no`, `hire_date`, `term_date`
  - 업무 규칙 위반은 `400`과 `{"detail": "...", "field": "..."}`(`field`는 선택)
  - 기존 개별 API(`persons/`, `employees/` 생성·수정, `/api/auth/accounts/`, 역할 배정)는 그대로 유지한다.

- 신규 API 요청·응답 (2026-10-13):

  | API | 요청 본문 | 성공 응답 | 주요 오류 |
  | --- | --- | --- | --- |
  | `new-hires/` | 필수 `name`, `birth_date`, `gender`(`M`/`F`), `email`, `hire_date`, `dept_no`, `position_code`, `base_salary`(0 이상) / 선택 `phone`, `extension_no`, `address`, `role_codes[]`, `account: {password}` (8자 이상, 비밀번호 규칙 적용) / `emp_no`를 보내면 `400` | `201` `emp_no`, `person_id`, `history_id`, `name`, `email`, `dept_no`, `position_code`, `hire_date`, `tenure_status`, `account`(`{id, email}` 또는 `null`), `roles[]` | `400` 입력 오류·이메일 중복·없는 부서/직급/역할·계정 생성 실패(`field: account.password`)·역할 규칙 위반, `409` 충돌 재시도 소진, `500` 사번 시퀀스 뒤처짐 |
  | `employees/{emp_no}/terminate/` | `term_date` | `200` 사원 상세 | `400` 미래·입사일 이전·이미 퇴사, `404` 없는 사원 |
  | `employees/terminated/` | 쿼리 `name`, `dept_no`, `emp_no`, `term_date_from`, `term_date_to` | `200` 목록(`emp_no`, `person_id`, `name`, `dept_no`, `dept_name`, `position_code`, `position_name`, `email`, `hire_date`, `term_date`), 퇴사일 최신순, 급여계좌 제외 | `400` 잘못된 필터·역순 기간 |
  | `persons/{person_id}/rehire/` | 신규 입사와 같음. 단 `name`, `birth_date`, `gender`는 선택(값이 있으면 Person 갱신) | `201` 신규 입사와 같은 형식 | `400` 재직·휴직 중 고용 있음, 입사일이 마지막 퇴사일 이전, 이메일 중복, 없는 Person |
  | `employees/{emp_no}/history/` `GET` | — | `200` 이력 목록(`history_id`, `start_date`, `end_date`, `dept_no`, `dept_name`, `position_code`, `position_name`, `base_salary`), 시작일 최신순 | `404` 없는 사원 |
  | `employees/{emp_no}/history/` `POST` | `start_date`, `dept_no`, `position_code`, `base_salary`, 이력 없는 사원의 첫 발령은 `previous_base_salary`, 선택 `reason` | `201` `history[]`, `released_head_dept_nos[]`, `restored_head_dept_nos[]` | `400` 미래·현재 이력 시작일 이전·부서/직급 변동 없음·퇴사자·없는 부서/직급, `404` |
  | `.../history/{history_id}/correct/` | `start_date`, `dept_no`, `position_code`, `base_salary`, `reason`(필수) | `200` 발령과 같은 형식 | `400` 최근 이력 아님·변경 없음·직전과 동일·첫 이력 시작일 변경·사유 없음 |
  | `.../history/{history_id}/cancel/` | `reason`(필수) | `200` 발령과 같은 형식, `restored_head_dept_nos` 포함 | `400` 최근 이력 아님·첫 이력·사유 없음 |
  | `.../history/changes/` | — | `200` 기록 목록(`history_id`, `action`(`발령`/`정정`/`취소`), `before`, `after`, `reason`, `changed_by`, `changed_at`, `released_head_dept_nos`, `restored_head_dept_nos`), 최신순 | `404` |

- 스키마·migration 변경:
  - 신규 테이블 `personal_info_change_requests`
    (`workforce/migrations/0004_personal_info_change_request.py`, dev의 `0003_payroll_manager_role` 다음)
  - `0005_employee_no_identity` (2026-10-13): 컬럼 변경 없음. `Employee.employee_no`를 `AutoField`로
    바꾸는 state-only 변경과, PostgreSQL에서 `employees_emp_no_seq`를 현재 최대 사번으로 맞추는
    `setval`. 되돌려도 시퀀스 값은 복구되지 않는다.
  - `0006_employment_history_change` (2026-10-13): 신규 테이블 `emp_history_changes`
    (`change_id`, `emp_no` FK, `history_id`(FK 아님, 취소된 이력 추적용), `action`, `before_values`·
    `after_values`(jsonb), `released_head_dept_nos`·`restored_head_dept_nos`(jsonb), `reason`,
    `changed_by_emp_no` FK, `changed_at`, 인덱스 `(emp_no, history_id)`)
  - 공유 DB 적용 기록:
    - 2026-10-13 사용자 승인 후 `erp_dev`(SSH 터널, 사용자 `jykim`)에 `0004` → `0005` 순서로 적용.
      적용 후 확인: `personal_info_change_requests` 생성(0행), 사번 시퀀스 `last_value=910055`(적용
      시점 최대 사번과 일치, 사전 점검 때 910050이었던 최대 사번이 그사이 늘어 있었음).
    - 2026-10-13 사용자 승인 후 `erp_dev`에 `0006` 적용. 적용 후 확인: `emp_history_changes` 생성
      (11개 컬럼, 인덱스 4개, 0행), workforce `0001`~`0006` 적용, `makemigrations --check` 변경 없음.
- 환경변수·인프라 영향: 없음
- 프론트엔드 영향: 일반 사원은 사원 목록 API를 호출하지 않고 본인 정보, 개인정보 변경 화면,
  부서 목록을 표시한다. 인사관리자에게는 변경 승인 목록이 추가로 표시된다. 2026-10-13 추가 API는
  프론트엔드 화면이 아직 없다.

## 검증

- 실행한 테스트:
  - `uv run pytest`: 84 passed (`tests/test_workforce_employee_info.py`,
    `tests/test_workforce_personal_info.py` 포함)
  - `uv run ruff check .`, `uv run python manage.py check`: 통과
  - `bun run lint`, `bun run build`: 통과
  - 로컬 SQLite 데모 DB에서 일반 사원·HR 관리자 화면과 요청→승인 반영 흐름 수동 확인
- 2026-10-13 추가 검증:
  - `uv run pytest`: 443 passed (작업 전 272)
    - `tests/test_workforce_onboarding.py`: 신규 입사·재입사 도메인/애플리케이션(인메모리 fake)·API.
      권한, 정상 등록, 입력 오류, 이메일 중복(사원·로그인 계정), 없는 부서·직급·역할, 계정 생성 실패,
      중간 단계 실패 전체 롤백, 동시 등록 충돌 재시도, 사번 시퀀스 뒤처짐 차단
    - `tests/test_workforce_lifecycle.py`: 퇴사 처리·퇴사자 조회·재입사 API, 기록 보존, 퇴사 후 로그인
      차단, 퇴사→재입사 흐름
    - `tests/test_workforce_history.py`: 발령 규칙, 자동 마감, 첫 발령 이전 기간 생성, 부서장 해제,
      롤백, 신규 입사 후 발령, 평가 모듈의 기준일별 부서 판정 연동
    - `tests/test_workforce_history_correction.py`: 정정·취소 규칙, 직전 이력 종료일 조정, 부서장 복원과
      비복원, 사유 필수, 롤백, 변경 기록 조회
  - `uv run ruff check .`, `uv run python manage.py check`, `makemigrations --check --dry-run`: 통과
  - 공유 DB 읽기 전용 점검: 테이블 구조·제약(`employees`, `persons`, `emp_history`, `employee_roles`,
    `accounts_users`), identity 컬럼, 사번 시퀀스, 성별 코드(`M`/`F`), `emp_history` 0행
- 남은 검증:
  - SSH 터널을 통한 실제 공유 PostgreSQL 기준 E2E 확인. 동시 등록·재입사 잠금, 사번 시퀀스 발급,
    `emp_history` 배타 제약은 SQLite로만 확인했다. 실행하려면 `erp_dev`에 테스트용 사원 데이터를 쓰게
    되므로 테스트 데이터 생성·정리 방법 승인이 필요하다.

## 결정 사항

- 인사관리자도 `PATCH /employees/{emp_no}/`로 사원 이메일을 직접 바꿀 수 없다. 등록 이후
  사내 이메일은 변경 요청·승인 절차로만 변경한다(`HR-003`, 다른 값이면 `400`).
- 이메일 변경 승인 시 연결된 계정의 로그인 이메일(`accounts_users.email`)도 같은 값으로 바꿔 새
  이메일로 로그인한다. 반려·취소 시 로그인 이메일은 그대로다. 요청·승인 시 이메일 중복 검사는 다른
  사원 이메일과 다른 계정의 로그인 이메일을 모두 대상으로 한다.
- 급여계좌 최소 보관: 변경 요청 이력의 계좌번호는 뒤 4자리만 남기고 가린다(`******1234`, 구분 기호
  제거). 변경 전 계좌는 요청 시점부터 가려 저장하고, 요청 계좌는 `대기` 동안만 원문을 보관하다가
  승인·반려·취소 시 가린다. 응답에서 요청 계좌 원문은 그 대기 요청을 처리할 수 있는 사용자에게만
  보여 준다. 사원 정보(`employees.account_no`)의 현재 계좌는 그대로다.
- 변경 요청 처리자(`FN-HR-004`)는 요청 시점이 아니라 승인·반려 시점의 조직 정보로 결정한다.
  superuser는 언제나 처리할 수 있다.

  | 요청자 | 처리자 |
  | --- | --- |
  | 일반 사원 | 인사관리자 |
  | 인사관리자(소속 부서장 아님) | 소속 부서장(상급자, 인사관리자인 경우) |
  | 인사관리자이면서 소속 부서장 | 본인 |
  | 인사관리자, 재직 중인 소속 부서장이 없거나 부서장이 인사관리자가 아님 | superuser |

  요청을 볼 수 없는 사용자(요청자·인사관리자·처리자가 아님)의 조회·처리·취소는 존재 여부를 숨기기 위해 `404`,
  볼 수는 있지만 처리 권한이 없으면 `403`. 응답의 `can_process`로 현재 사용자의 처리 가능 여부를 알려 주며,
  `GET /api/workforce/personal-info-requests/?processable=true`는 처리 가능한 대기 요청만 반환한다.
- 2026-10-13 사용자 결정: 위 "신규 입사·퇴사·재입사·인사이력" 절의 사번 identity 발급, 필수 항목,
  기본급 필수(0 이상), 계정 선택·초기 비밀번호 인사관리자 입력, 최초 인사이력 입사일 기준, 퇴사일
  오늘 이전, 퇴사 시 기록 보존, 재입사 조건과 새 이메일·새 계정, 인적사항 선택 갱신, 발령 자동 마감·
  현재 소속 갱신·오늘 이전, 첫 발령 이전 기간 자동 생성, 부서·직급 변경만 발령, 발령 시 부서장 자동
  해제, 최근 이력만 정정·취소, 정정·취소 기록과 사유 필수, 취소 시 비어 있는 부서장 자동 복원.

## 미결정 사항

- 사원 목록 API(`GET /api/workforce/employees/`) 인사관리자 전용 제한(`HR-001`)과 dev 병합 후의 평가·급여
  화면 충돌: 평가(부서장)와 급여(`PAYROLL_MANAGER`) 화면이 전체 사원 목록을 불러오므로 인사관리자가 아니면
  `403`으로 동작하지 않는다. 권한 확대, 공개용 간단 목록 분리, 모듈별 API 중 방향 결정 필요.
- 상급자가 없을 때의 "임시 팀장" 처리자: 현재 데이터에 임시 팀장을 표현할 역할·필드가 없어
  superuser만 처리하도록 구현했다. 표현 방식(역할 코드 또는 부서 필드) 결정 필요.
- 운영 원칙: 인사팀장에게 `HR_MANAGER` 역할을 부여한다. 역할이 없는 부서장은 처리자가 되지 않아
  급여계좌가 노출되지 않지만, 그 경우 인사관리자 요청은 superuser가 처리해야 한다.
- (2026-10-13) 변경 요청 테이블 중복: `erp_dev`에 명세상 `employee_change_requests`(필드당 한 행, 0행)와
  `0004`로 만든 `personal_info_change_requests`(요청당 한 행, 0행)가 함께 있다. 확정된 `HR-003` 규칙(은행
  코드·계좌번호 동시 요청·승인, 요청 단위 대기 1건)은 기존 구조로 스키마 변경 없이 표현하기 어려워
  `personal_info_change_requests`로 통합하고 기존 테이블을 삭제하는 방향을 제안한다. 정본 결정 후 삭제
  migration(`RunSQL`, 0행 확인 조건)을 만든다.
- (2026-10-13) 사번 직접 입력 공존: 기존 `POST /api/workforce/employees/`는 사번을 직접 입력받는다. 직접
  입력하면 시퀀스가 따라 올라가지 않아 신규 입사·재입사가 사번 시퀀스 뒤처짐으로 실패한다(`500`).
  직접 입력을 막을지, 유지하면서 시퀀스를 다시 맞출지 결정 필요.
- (2026-10-13) 수정 API의 상태 변경: `PATCH /api/workforce/employees/{emp_no}/`로 `퇴사`를 직접 넣으면
  퇴사 API의 "오늘 이전" 검사를 거치지 않고, 부서·직급을 바꾸면 인사이력이 남지 않는다. 막을지 결정 필요.
- (2026-10-13) 퇴사자의 남은 기록: 부서장 지정·대기 변경 요청·진행 중 인사이력·활성 역할이 퇴사 후에도
  남는다(`HR-005` 보존). 자동 정리 여부 또는 운영 절차 결정 필요.
- (2026-10-13) 신규 입사: 미래 입사일(입사 예정자)도 즉시 `재직`·로그인 가능, 생년월일·입사일 관계 미검사,
  첫 로그인 비밀번호 변경 강제 없음, 비밀번호 규칙이 기존 계정 API와 다름.
- (2026-10-13) 휴가 승인 인사담당자 1명 규칙: 동시 배정 시 깨질 수 있다(기존 역할 API도 동일).
- (2026-10-13) 모델과 실제 DB 차이: DB는 NOT NULL인데 모델은 null 허용인 컬럼이 있다(`employees.dept_no`,
  `position_code`, `email`, `persons.birth_date`, `emp_history.base_salary`). 기존 사원·인적사항 API에 null을
  보내면 `400`이 아니라 DB 오류(`500`)가 난다. 모델을 DB에 맞추는 state-only migration을 제안한다.
- (2026-10-13) 시간대: `employee_roles.assigned_at` 등 일부 컬럼이 `timestamp without time zone`이다.
  Django 시간대 처리와의 정합성 확인 필요.
- (2026-10-13) 인사이력 미보유 사원: `erp_dev` 사원 55명 모두 이력이 없다. 첫 발령 때 이전 기간이 생성되지만,
  발령이 없는 사원은 평가에서 계속 현재 소속으로 판정된다. 일괄 적재 여부 결정 필요.
- (2026-10-13) 퇴사자 목록 페이지네이션, 퇴사 사유 저장, 퇴사 취소, 휴직·복직 처리 필요 여부.

## 모듈 의제 대응 (2026-10-13)

[2026-10-12 모듈 담당자 검토 의제](../../../reports/2026-10-12_module-review-agenda.md)와
[통합 검토 결과](./integration-review.md)에 대한 담당자 조사·작업 기록이다. 정책 확정이나 해결 완료를
뜻하지 않으며, 공용 반영 여부는 문서 담당자가 판단한다.

### HR-01 · 개인정보 변경 요청 테이블의 이중 구조

- 상태: 제품 결정 필요
- 주 담당 모듈: workforce / 협업: DB·문서 담당
- 유형: 명세–구현 불일치
- 관련 규칙·기능 ID: `HR-003`, `HR-011`, `FN-HR-003`~`FN-HR-005`, `FN-HR-011`
- 확정 기준: `docs/specs/notion/08-table-specification.md`의 `employee_change_requests`(확인일 2026-10-13)
- 현재 동작·근거 (2026-10-13 `erp_dev` 읽기 전용 확인, 실제 값은 기록하지 않음):
  - `employee_change_requests`: 존재, 0행. 컬럼 `request_id`, `emp_no`, `field_code`(NOT NULL),
    `before_value`, `requested_value`(NOT NULL), `status`(기본 `대기`, CHECK 4개 값), `requested_at`
    (`timestamp`, 기본 현재 시각), `processed_by`, `processed_at`, `reject_reason`, FK 2개, `emp_no` 인덱스.
    저장소 코드(backend·frontend)에서 참조하는 곳이 없다.
  - `personal_info_change_requests`: 2026-10-13 사용자 승인 후 `0004`로 생성, 0행. 코드는 이 테이블만 쓴다.
  - 두 테이블 모두 0행이라 현재 이력 분리·유실은 없다.
- 영향: 확정된 `HR-003` 운영 결정(은행 코드·계좌번호 동시 요청·승인, 요청 단위 대기 1건, 이메일·계좌를
  한 요청으로)은 필드당 한 행 구조에서 묶음 컬럼 추가나 값 결합 없이 표현하기 어렵다.
- 작업 항목·제안: `personal_info_change_requests`를 정본으로 하고 `employee_change_requests`를 삭제한다.
  정본 결정 후 0행 확인 조건을 둔 `RunSQL` 삭제 migration을 만든다(아직 만들지 않음).
  기존 구조를 정본으로 유지하기로 하면 요청 묶음 컬럼 추가와 저장소 계층 재작성이 필요하다.
- 결정 요청: 정본 테이블과 요청 단위, 기존 테이블 삭제 여부.
- 공유 인프라 영향: DDL(`0004` 테이블 생성, 2026-10-13 적용 완료). 삭제는 별도 승인 후.
- 결정·작업 결과: 미결정. 의제가 "조사 필요" 상태일 때 `0004`를 적용했으므로 문서 담당자 확인이 필요하다.

### OPS-01 · 현재 공유 DB 적용 여부와 배포 준비 (workforce 부분)

- 상태: 조사 완료(workforce 범위), 일부 적용
- 확인 환경: `erp_dev`(SSH 터널, 2026-10-13), 읽기 전용 조회와 사용자 승인 migration 적용
- migration 정의와 실제 적용:

  | migration | 내용 | `erp_dev` 적용 |
  | --- | --- | --- |
  | `0001`~`0003` | 기존 테이블 state 등록, 필수 역할 시드 | 적용됨(기존) |
  | `0004_personal_info_change_request` | 변경 요청 테이블 생성 | 2026-10-13 적용 |
  | `0005_employee_no_identity` | `emp_no` state 변경, 사번 시퀀스 맞춤 | 2026-10-13 적용(`last_value=910055`) |
  | `0006_employment_history_change` | `emp_history_changes` 생성 | 2026-10-13 적용 |

- 스키마 확인: `employees.emp_no`·`persons.person_id`·`emp_history.history_id`·`employee_roles`·
  `accounts_users.id`는 `GENERATED BY DEFAULT AS IDENTITY`. `emp_history`에 기간 배타 제약
  (`EXCLUDE USING gist (emp_no WITH =, daterange(start_date, end_date, '[]') WITH &&)`), `base_salary`
  NOT NULL 기본값 0과 0 이상 CHECK. `employees.dept_no`·`position_code`·`email`, `persons.birth_date`는
  NOT NULL인데 Django 모델은 null 허용이다(미결정 사항 참고).
- 데이터 준비(집계): 사원 55명, `emp_history` 0행, 성별 코드 `F`·`M`. 역할 마스터는
  `HR_LEAVE_APPROVER`, `HR_MANAGER`, `MANAGEMENT_OFFICER`, `PAYROLL_MANAGER`. `MANAGEMENT_OFFICER`는
  workforce migration(`0002`·`0003`)에 시드가 없어 migration 밖에서 공급된 것으로 보인다.
- 배포 주의:
  - 사번을 직접 넣는 경로(기존 `POST /api/workforce/employees/`, dev의
    `scripts/sql/create_50_test_employee_accounts.sql` 테스트 사원 910001~910050)를 `0005` 이후에 실행하면
    시퀀스가 다시 뒤처져 신규 입사·재입사가 실패한다. 실행 후 `setval`로 시퀀스를 맞춰야 한다.
  - `0006`이 없는 환경에서는 인사이력 발령·정정·취소 API가 실패한다. 배포 시 `0004`→`0005`→`0006` 순서로 적용한다.
- 결정 요청: 사번 직접 입력 경로 유지 여부, 역할 마스터 공급 책임, 다른 환경 배포 순서.
- 미검증 범위: 다른 모듈 migration 적용 상태, 평가 데이터 호환성(evaluation 담당).

### INT-01 · HR-02 · HR-03

- 상태: 변동 없음. 이번 작업(신규 입사·퇴사·재입사·인사이력)에서 다루지 않았다.
- 참고: 이번 작업의 신규 API는 모두 인사관리자 전용이라 INT-01의 비HR 조회 문제를 늘리지 않는다.
  신규 입사·재입사 계정 생성은 사내 이메일을 로그인 ID로 쓰므로 HR-03의 "사내 이메일과 로그인 ID 관계"
  결정에 함께 포함되어야 한다. 퇴사자 목록은 급여계좌를 응답하지 않는다(HR-02 관련).

## 공용 문서 반영 후보

- Notion 원문:
  - `HR-001` 예외 범위: 부서장 예외 없음, 인사관리자만 타인 정보 조회로 확정
  - `FN-HR-001` 조회 항목: 급여계좌 포함, 인사이력 제외
  - `HR-002` "연락처" 범위와 사원당 대기 요청 1건 제한
  - (2026-10-13) `FN-HR-006`~`FN-HR-010` 상세 흐름: 위 "신규 입사·퇴사·재입사·인사이력" 절의 사용자
    결정 사항
  - (2026-10-13) 테이블 결정안·명세: `employee_change_requests` → `personal_info_change_requests` 통합
    제안, 신규 `emp_history_changes`, `employees.emp_no` identity 발급 방식
- 저장소 명세·README:
  - `docs/specs/notion/06-api-specification.md` 5.2 사원 표: 목록·상세 권한 변경, `me` 조회·수정,
    상세 응답 필드, 개인정보 변경 요청 API 추가
  - (2026-10-13) `06-api-specification.md`: 위 표의 신규 API 9개와 요청·응답·오류
  - (2026-10-13) `07-table-design-decisions.md`, `08-table-specification.md`: `personal_info_change_requests`,
    `emp_history_changes` 추가, `employee_change_requests` 처리, `emp_no` identity 시퀀스 운영 주의
  - `docs/specs/notion/workforce-implementation-map.md`: `FN-HR-001`~`FN-HR-005`, `FN-HR-011`
    구현 완료 표시와 `FN-HR-001` 급여계좌 포함 여부 정리
    - (2026-10-13) `FN-HR-006`~`FN-HR-010`을 "후속 구현"에서 "현재 구현"으로 옮기고,
      "Person/Employee 생성과 Account 연결을 묶는 transaction use case"를 구현 완료로 표시
    - 이전에 이 브랜치에서 직접 추가했다가 기여 문서로 옮긴 제안(2026-09-22 작성):
      `FN-HR-001` 본인 정보 조회는 로그인한 사원 본인의 인사정보(부서·직급·연락처·주소·급여계좌·
      입퇴사일 포함)를 반환하고 다른 사원 조회는 막는다. 조회 로직은 `accounts`가 아니라 `workforce`에
      둔다: `domain.policies.EmployeeProfile` → `application.services.get_employee_profile` →
      `infrastructure.gateways.DjangoWorkforceQueryGateway.employee_profile`. `accounts/serializers.py`는
      이 유스케이스만 호출한다. 점검일을 2026-09-22로 갱신.
  - `docs/prompts/02-퇴사자-조회.md`: 구현 완료(`GET /api/workforce/employees/terminated/`)로 상태 갱신
  - 작업 보고서: 이 브랜치의 `2026-09-22_사원_본인정보_조회_모듈화_작업_보고서.md`(이 폴더)를 문서
    담당자가 검토해 `docs/reports/`로 옮길지 결정
