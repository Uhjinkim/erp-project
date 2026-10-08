# evaluation / bae 기여 문서

- 대상 모듈: `evaluation`
- 작업 브랜치: `bae`
- 기준 브랜치: `dev`
- 상태: 작성 중

## 기능 범위

- 구현 범위: 인사평가 작성·수정·제출(평가자), 반려·평가자 재배정·평가 제외·제외 취소·확정·
  확정 취소(인사관리자), 상세·목록·이력 조회 백엔드 API와 프론트엔드
  인사평가 화면(`EvaluationPanel`). `evaluations` 테이블 모델 등록과 평가 워크플로용
  스키마 변경 마이그레이션.
- 제외 범위: 평가 회차, 근무 기간에 따른 점수 보정,
  평가 기간(시작·종료일) 기록.

## 설계 결정

- 관련 규칙·기능 ID: `EV-001`~`EV-005`, `FN-EV-001`~`FN-EV-004`, `HR-001`, `HR-004`~`HR-005`.
  저장소 스냅샷에는 EV 규칙이 요약(부서장 평가, 자기평가 금지, 점수별 등급, HR 확정)으로만 있어
  개별 ID와 동작의 1:1 대응은 Notion 원문으로 확인이 필요하다. 코드·테스트에서는 아래 대응을
  가정했다: EV-001 부서장 평가, EV-002 자기평가 금지, EV-003 점수별 등급, EV-004 HR 확정.
  EV-005는 "확정 평가 공개 — 사원은 본인의 확정된 평가만 조회한다"이다(사용자 확인, 2026-10-07).
  `FN-EV-001`은 "소속 사원 평가 작성·수정 — 부서장 — EV-001~EV-003"이다(사용자 확인, 2026-10-07).
- 등급 기준(사용자 확인, 2026-10-06): 100점 만점 기준 S 90점 이상, A 80점 이상, B 70점 이상,
  C 70점 미만. `evaluation/domain/value_objects.py`의 `GRADE_THRESHOLDS` 한 곳에서 관리한다.
  점수는 0.00~100.00, 소수점 둘째 자리까지이며 등급은 서버가 계산한다.
- 평가 운영 정책(사용자 확인, 2026-10-07)을 아래와 같이 구현했다.

### 상태 흐름

```text
작성중 ─제출→ 제출 ─확정→ 확정
  ↑            │              │
  └─ 반려 ←─반려┘ ←─확정 취소(사유)┘   (반려 상태에서 수정 후 다시 제출)
작성중·제출·반려 ─제외(사유)→ 제외 ─제외 취소→ 제외 직전 상태
```

- 평가자는 `작성중`·`반려` 상태에서만 수정·제출한다. 제출된 평가를 고치려면 인사관리자가 반려한다.
- 확정된 평가는 직접 수정·반려·재배정·제외할 수 없다. 정정이 필요하면 인사관리자가 사유를 남겨
  확정을 취소하고(사용자 확인, 2026-10-07), 평가는 `반려` 상태로 현재 평가자에게 돌아간다.
  평가자가 수정·제출하면 인사관리자가 다시 확정하며, 작성자·확정자 분리 규칙이 그대로 적용된다.
  확정 취소 시 `confirmed_by`·`confirmed_at`은 비우고 이전 확정 정보는 이력에 남는다.
  확정이 취소된 평가는 다시 확정될 때까지 대상자에게 보이지 않는다.
- 평가 제외는 점수 0점과 구분되는 별도 상태이며 점수·의견은 보존된다. 확정 전 평가만 제외할 수 있다.

### 평가자와 권한

- 최초 평가자: 대상자 소속 부서의 부서장. 대상자가 부서장이면 상위 부서의 부서장(사용자 확인,
  2026-10-06). 상위 부서장이 하위 부서원을 건너뛰어 평가할 수는 없고, 자기평가는 거절한다.
- 최초 작성자(`created_by`)와 현재 평가자(`evaluator_no`)를 구분한다. 수정·제출 권한은 현재
  평가자에게만 있다.
- 부서장 교체나 대상자 부서 이동이 있어도 평가자는 자동으로 바뀌지 않는다. 인사관리자만 확정 전
  평가의 평가자를 재배정하며 사유가 필수다. 재배정 이력에 이전·새 평가자와 사유를 남긴다.
- 재배정된 이전 평가자는 열람·수정 권한을 잃는다(404). 제출 상태에서 재배정하면 `작성중`으로
  돌아가 새 평가자가 이어받은 초안을 확인한 뒤 다시 제출한다. `반려` 상태는 그대로 유지한다.
- 평가자가 퇴사·휴직하거나 계정이 비활성화되면 인증 단계와 서비스 단계에서 접근이 차단되며,
  인사관리자가 재배정해야 진행된다. 재배정 대상은 재직 사원이어야 한다.
- 점수·의견은 현재 평가자만 수정한다. 인사관리자는 재배정·반려·제외·제외 취소·확정·확정 취소만
  수행한다.
- FN-EV-001에 따라 **평가자는 항상 현재 부서장이며 인사관리자는 평가자가 될 수 없다**
  (사용자 확인, 2026-10-07). 재배정은 인사관리자만 하며 화면에서 후보를 골라 실행한다.
  - 재배정: 새 평가자는 재직 중이고, 현재 어느 부서든 부서장이며, 인사관리자가 아니어야 한다.
    부서장이 아니면 `evaluator_must_be_department_head`, 인사관리자면 `hr_manager_cannot_evaluate`
    (모두 403). 후보 목록은 `GET /api/evaluations/evaluator-candidates/`(인사관리자 전용)로 제공한다.
  - 작성: 인사관리자 역할이 있는 부서장은 평가를 새로 작성할 수 없다.
  - 수정·제출: 현재 평가자가 부서장 보직을 잃었거나 인사관리자 역할을 받았다면 재배정 전까지
    수정·제출할 수 없다. 매 저장 시 다시 확인한다.
  - 이에 따라 과거 실적을 평가할 이전 부서장도 **현재 부서장**이어야 지정할 수 있다. 보직이 끝난
    이전 부서장은 평가자가 될 수 없다.
  - 재배정 대상 검사(재직 여부, 인사관리자 여부)는 호출자가 인사관리자로 확인된 뒤에 수행해,
    권한 없는 사원이 다른 사원의 상태를 알아낼 수 없게 한다.
- 확정 불가: 평가 대상자 본인, 현재 평가자, 이력상 작성·수정·제출을 한 이전 평가자. 이 경우
  `confirmation_not_allowed`(403)로 거절되고 평가는 `제출` 상태로 남아 다른 인사관리자가 처리한다.
- **구현 중 추가한 제한(검토 필요)**: 평가 대상자 본인은 인사관리자라도 자신의 평가를
  반려·재배정·제외·제외 취소·확정 취소할 수 없다. 정책에는 확정만 명시되어 있으나 자기평가 금지 취지에 맞춰
  적용했다.

### 대상자·연도

- 휴직자도 평가 대상이다. 퇴사자는 새 평가를 만들 수 없고, 진행 중이던 평가는 인사관리자가
  확정하거나 제외한다. 기존 평가는 보존한다(`RESTRICT` FK).
- 새 평가는 현재 연도(서버 기준 `Asia/Seoul`)와 직전 연도만 생성할 수 있다. 연도가 바뀌어도 기존
  미완료 평가의 수정·제출·확정은 가능하다.
- 평가 기준 부서·직급은 **연말 기준**이다(사용자 확인, 2026-10-07). 기준일은 해당 연도
  12월 31일이며, 연말이 오지 않은 현재 연도는 생성일이다. 기준일의 부서·직급을 인사이력
  (`emp_history`)에서 찾아 평가자 판정과 `snapshot_dept_no`, `snapshot_pos_code` 기록에 쓴다.
  예: 1월 1일 부서를 옮긴 사원의 직전 연도 평가는 이전 부서의 부서장이 작성하고 기준 부서도
  이전 부서로 기록된다. 기록된 값은 이후 조직 이동으로 바뀌지 않는다.
  - 기준일을 덮는 인사이력이 없으면 현재 소속 부서·직급으로 대체한다. 현재 앱이 `emp_history`를
    기록하지 않으므로 이력 데이터가 채워지기 전에는 사실상 현재 부서 기준으로 동작한다.
  - 부서장은 이력이 없어 기준일 부서의 **현재** 부서장이 평가자가 된다. 연말 이후 부서장이
    바뀌었다면 인사관리자가 재배정한다.
- 사원·연도당 평가는 1건이다. 애플리케이션 검사와 DB 고유 제약
  `uq_evaluations_emp_no_eval_year`를 함께 사용하며, 동시 생성으로 제약에 걸리면 409로 응답한다.

### 열람과 동시 작업

- 확정 전(`작성중`·`제출`·`반려`·`제외`) 평가는 현재 평가자와 인사관리자만 열람한다.
- EV-005: 평가 대상자는 확정된 본인 평가만 열람한다. 대상자가 인사관리자여도 같다(확정 전 본인
  평가는 상세 404, 목록 제외). 이력(반려·제외 사유 포함)은 현재 평가자와 인사관리자만 조회할 수
  있으며 평가 대상자 본인은 확정 후에도 조회할 수 없다.
- 권한 밖 평가는 존재 여부를 숨기기 위해 404로 응답한다. 인사관리자 전용 동작(반려·재배정·
  제외·확정 등)도 대상자 본인에게 보이지 않는 평가는 404로 응답해, 인사관리자인 대상자가 확정 전
  본인 평가의 존재를 알아낼 수 없다(EV-005). 평가 작성 요청은 평가 권한을 대상자
  존재·재직 여부보다 먼저 확인해, 권한 없는 사원에게 대상자 상태·역할을 드러내지 않는다(HR-001).
- 모든 상태 변경은 요청 시점에 권한과 상태를 다시 확인한다. 저장은 불러온 시점의 상태·평가자가
  그대로일 때만 반영하고, 그사이 다른 사용자가 상태를 바꾸거나 재배정했으면 409
  `evaluation_conflict`("새로고침 후 다시 시도")로 응답한다. 확정·재배정된 평가를 덮어쓰지 않기
  위한 확인이다.
- 같은 평가의 점수·의견 동시 수정은 비교하지 않고 **마지막에 저장된 내용**을 반영한다(사용자 확인,
  2026-10-07). 화면이 받은 `updated_at`을 보내 오래된 화면의 덮어쓰기를 막는 방식은 쓰지 않는다.
- 평가 변경과 이력 기록은 한 트랜잭션(`DjangoEvaluationUnitOfWork`)으로 처리한다.
- Django admin의 평가·이력 화면은 읽기 전용이다.

### 미정 항목 (결정 필요)

- 평가를 생성할 평가자가 없는 경우: 최상위 부서장, 부서장이 공석인 부서의 사원, 그리고
  **부서장이 인사관리자인 부서의 사원**(FN-EV-001 적용으로 새로 생김)은 평가를 생성할 수 없다
  (403). 인사관리자가 인사관리자가 아닌 평가자를 지정해 생성할 수 있게 할지 결정 필요.
- 평가 생성 전 제외 처리(점수 없는 제외 평가) 허용 여부. 허용하면 `score`·`grade` NULL 허용이 필요하다.
- 평가 기간(시작·종료일) 산정 방식. 정해지면 컬럼을 추가한다.
- 내부 검토 의견을 평가 의견과 분리할지, 대상자 공개 범위.
- 제외 취소는 현재 제외 직전 상태로 복원한다. 정책 확정 필요.

## 인터페이스와 데이터 영향

- API (모두 로그인 필요, 사원번호 연결 계정만 사용):

  | 메서드 | 경로 | 설명 | 권한 |
  | --- | --- | --- | --- |
  | `GET` | `/api/evaluations/?year=YYYY` | 평가 목록 | 열람 규칙 적용 |
  | `POST` | `/api/evaluations/` | 평가 작성 `{emp_no, eval_year, score, comments?}` | 지정 평가자(부서장/상위 부서장, 인사관리자 제외) |
  | `GET` | `/api/evaluations/<eval_id>/` | 평가 상세 | 열람 규칙 적용 |
  | `PATCH` | `/api/evaluations/<eval_id>/` | 수정 `{score, comments?}`; `comments` 생략 시 유지, `""`는 삭제 | 현재 평가자 |
  | `POST` | `/api/evaluations/<eval_id>/submit/` | 제출 | 현재 평가자 |
  | `GET` | `/api/evaluations/<eval_id>/history/` | 이력 | 현재 평가자, 인사관리자 |
  | `POST` | `/api/evaluations/<eval_id>/return/` | 반려 `{reason}` | 인사관리자 |
  | `GET` | `/api/evaluations/evaluator-candidates/` | 재배정 후보(재직 중인 현재 부서장, 인사관리자 제외) `[{emp_no, name, dept_no, dept_name}]` | 인사관리자 |
  | `POST` | `/api/evaluations/<eval_id>/reassign/` | 평가자 재배정 `{evaluator_no, reason}`; 새 평가자는 재직 중인 현재 부서장이고 인사관리자가 아니어야 함 | 인사관리자 |
  | `POST` | `/api/evaluations/<eval_id>/confirm/` | 확정 | 인사관리자(작성 관여자 제외) |
  | `POST` | `/api/evaluations/<eval_id>/cancel-confirmation/` | 확정 취소 `{reason}` → `반려` | 인사관리자 |
  | `POST` | `/api/evaluations/<eval_id>/exclude/` | 평가 제외 `{reason}` | 인사관리자 |
  | `POST` | `/api/evaluations/<eval_id>/cancel-exclusion/` | 제외 취소 `{reason?}` | 인사관리자 |

  평가 응답 필드: `eval_id`, `emp_no`, `employee_name`, `eval_year`, `snapshot_dept_no`,
  `snapshot_pos_code`, `evaluator_no`, `evaluator_name`, `created_by`, `score`(문자열, 소수 2자리),
  `grade`, `comments`, `eval_status`(`작성중`/`제출`/`반려`/`확정`/`제외`), `confirmed_by`,
  `confirmed_at`, `updated_at`.
  이력 응답 필드: `history_id`, `eval_id`, `action`(`CREATE`/`REVISE`/`SUBMIT`/`RETURN`/
  `REASSIGN`/`CONFIRM`/`CANCEL_CONFIRMATION`/`EXCLUDE`/`CANCEL_EXCLUSION`), `from_status`,
  `to_status`, `actor_no`, `actor_name`, `from_evaluator_no`, `to_evaluator_no`, `score`, `reason`, `changed_at`.
  오류는 `{code, detail}` 형식이며 400(입력·`eval_year_not_allowed`), 403(`permission_denied`,
  `self_evaluation_not_allowed`, `hr_manager_cannot_evaluate`, `evaluator_must_be_department_head`,
  `confirmation_not_allowed`,
  `inactive_employee`), 404(없음·열람
  권한 없음), 409(`duplicate_evaluation`, `invalid_evaluation_state`, `evaluation_conflict`).
- 스키마·migration 변경:
  - `0001_initial.py`: 공유 DB에 이미 존재하는 `evaluations` 테이블을 등록하는 **state-only**
    마이그레이션(`database_operations=[]`). ERD에 NULL 정보가 없어 `snapshot_dept_no`,
    `snapshot_pos_code`, `comments`, `confirmed_by`, `confirmed_at`은 nullable로 선언했다.
  - `0002_evaluation_workflow.py`: **실제 DB를 변경한다.** 기능 브랜치 병합 시 적용 예정
    (사용자 확인, 2026-10-07). 이 브랜치에서는 공유 DB에 migrate를 실행하지 않았다.
    - `evaluations.created_by integer NULL` FK → `employees.emp_no` (기존 행은 NULL)
    - 고유 제약 `uq_evaluations_emp_no_eval_year (emp_no, eval_year)`
    - 신규 테이블 `evaluation_history`: `history_id bigint PK`, `eval_id` FK → `evaluations`,
      `action varchar(20)`, `from_status varchar(20) NULL`, `to_status varchar(20)`,
      `actor_emp_no` FK, `from_evaluator_no` FK NULL, `to_evaluator_no` FK NULL,
      `score numeric(5,2) NULL`, `reason varchar(255)`, `changed_at timestamp`
    - `eval_status` 허용 값 확장(`작성중`/`제출`/`반려`/`확정`/`제외`, CHECK 제약은 만들지 않음)
  - 적용 전 확인(읽기 전용): `evaluations`에 `(emp_no, eval_year)` 중복 행이 없는지, 기존 행의
    `eval_status`·`grade`·`score` 값이 위 도메인 값에 맞는지. 맞지 않는 행이 있으면 목록 조회가 실패한다.
- 프론트엔드: `frontend/src/components/EvaluationPanel.tsx`, `src/api/evaluation.ts`,
  `src/types/evaluation.ts`를 추가하고 `App.tsx` 업무 모듈 탭에 "인사평가"를 추가했다(세션 인증
  모드). 부서장은 평가 작성·수정·제출, 인사관리자는 반려·확정·확정 취소·제외·제외 취소와 후보
  목록에서 부서장을 골라 사유와 함께 재배정한다. 처리 이력을 상세 화면에 표시한다. 버튼 노출은
  안내용이며 권한·상태 판단은 백엔드가 한다. 작성 대상 목록은 사원·부서 API로 계산한 소속 부서원과
  하위 부서장이다.
- 환경변수·인프라 영향: 없음. `config/settings/base.py`의 `INSTALLED_APPS`, `config/urls.py`,
  `config/settings/test.py`의 `MIGRATION_MODULES`에 `evaluation`을 추가했다.

## 검증

- 실행한 테스트 (`backend/`):
  - `uv run pytest` — 191 passed (`test_evaluation_domain.py` 59건, `test_evaluation_service.py`
    42건, `test_evaluation_api.py` 26건, 계층 의존성 검사 포함)
  - `uv run ruff check .` — 통과
  - `uv run python manage.py check` — 이상 없음
  - `uv run python manage.py makemigrations --check --dry-run` — No changes detected
- 실행한 검증 (`frontend/`): `bun run lint`, `bun run build` — 통과
- 남은 검증: 실제 공유 DB `evaluations` 스키마·데이터 읽기 전용 대조, 병합 시 `0002` 적용 결과,
  브라우저에서의 화면 동작 확인. 화면은 DB·Redis가 모두 연결되어야 활성화되는데 로컬에 대체
  환경이 없고 공유 DB에 테스트 데이터를 쓸 수 없어 이번 작업에서는 브라우저로 확인하지 않았다.

## 공용 문서 반영 후보

- Notion 원문: 등급 기준(EV-003), 부서장은 상위 부서장이 평가(EV-001), 연말 기준 부서,
  EV-005 문구(확정 평가 공개)·FN-EV-001 문구 대조, 인사관리자는 평가자가 될 수 없다는 규칙,
  평가 운영 정책
  (상태 흐름, 평가자 재배정, 작성자·확정자 분리, 확정 취소를 통한 정정, 휴직자·퇴사자 처리, 생성 연도 제한, 열람 범위)
  반영. 위 미정 항목 결정 요청. `FN-EV-001`~`FN-EV-004` 개별 기능 정의 확인.
- 저장소 명세·README: `01-overview-actors-states.md` 인사평가 상태 갱신, `06-api-specification.md`에
  평가 API 추가, `07-table-design-decisions.md`·`08-table-specification.md`에 `evaluation_history`,
  `created_by`, 고유 제약 반영, `evaluation-implementation-map.md`(규칙 ID ↔ 코드·테스트 대응표)
  신설 검토.
