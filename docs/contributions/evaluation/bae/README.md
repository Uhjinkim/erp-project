# evaluation / bae 기여 문서

- 대상 모듈: `evaluation`
- 작업 브랜치: `bae`
- 기준 브랜치: `dev`
- 상태: 작성 중

## 기능 범위

- 구현 범위: 인사평가 작성·수정·제출(평가자), 반려·평가자 재배정·평가 제외·제외 취소·확정·
  확정 취소(인사관리자), 상세·목록·이력 조회 백엔드 API. `evaluations` 테이블 모델 등록과 평가 워크플로용
  스키마 변경 마이그레이션.
- 제외 범위: 프론트엔드 화면, 평가 회차, 근무 기간에 따른 점수 보정,
  평가 기간(시작·종료일) 기록.

## 설계 결정

- 관련 규칙·기능 ID: `EV-001`~`EV-005`, `FN-EV-001`~`FN-EV-004`, `HR-001`, `HR-004`~`HR-005`.
  저장소 스냅샷에는 EV 규칙이 요약(부서장 평가, 자기평가 금지, 점수별 등급, HR 확정)으로만 있어
  개별 ID와 동작의 1:1 대응은 Notion 원문으로 확인이 필요하다. 코드·테스트에서는 아래 대응을
  가정했다: EV-001 부서장 평가, EV-002 자기평가 금지, EV-003 점수별 등급, EV-004 HR 확정.
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
- 평가 기준 부서·직급은 생성 시점에 `snapshot_dept_no`, `snapshot_pos_code`로 기록하며 이후 조직
  이동으로 바뀌지 않는다.
- 사원·연도당 평가는 1건이다. 애플리케이션 검사와 DB 고유 제약
  `uq_evaluations_emp_no_eval_year`를 함께 사용하며, 동시 생성으로 제약에 걸리면 409로 응답한다.

### 열람과 동시 작업

- 확정 전(`작성중`·`제출`·`반려`·`제외`) 평가는 현재 평가자와 인사관리자만 열람한다.
- 평가 대상자는 확정된 본인 평가만 열람한다. 이력(반려·제외 사유 포함)은 현재 평가자와
  인사관리자만 조회할 수 있다.
- 권한 밖 평가는 존재 여부를 숨기기 위해 404로 응답한다. 평가 작성 요청은 평가 권한을 대상자
  존재·재직 여부보다 먼저 확인해, 권한 없는 사원에게 대상자 상태·역할을 드러내지 않는다(HR-001).
- 모든 상태 변경은 요청 시점에 권한과 상태를 다시 확인한다. 저장은 불러온 시점의 상태·평가자·
  `updated_at`이 그대로일 때만 반영하고, 그사이 다른 사용자가 변경했으면 409
  `evaluation_conflict`("새로고침 후 다시 시도")로 응답한다. 평가 변경과 이력 기록은 한
  트랜잭션(`DjangoEvaluationUnitOfWork`)으로 처리한다.
- Django admin의 평가·이력 화면은 읽기 전용이다.

### 미정 항목 (결정 필요)

- 최상위 부서장, 부서장이 공석인 부서의 사원: 평가를 생성할 평가자가 없다(403). 인사관리자가
  평가자를 지정해 생성할 수 있게 할지 결정 필요.
- 평가 생성 전 제외 처리(점수 없는 제외 평가) 허용 여부. 허용하면 `score`·`grade` NULL 허용이 필요하다.
- 평가 기간(시작·종료일) 산정 방식. 정해지면 컬럼을 추가한다.
- 내부 검토 의견을 평가 의견과 분리할지, 대상자 공개 범위.
- 제외 취소는 현재 제외 직전 상태로 복원한다. 정책 확정 필요.

## 인터페이스와 데이터 영향

- API (모두 로그인 필요, 사원번호 연결 계정만 사용):

  | 메서드 | 경로 | 설명 | 권한 |
  | --- | --- | --- | --- |
  | `GET` | `/api/evaluations/?year=YYYY` | 평가 목록 | 열람 규칙 적용 |
  | `POST` | `/api/evaluations/` | 평가 작성 `{emp_no, eval_year, score, comments?}` | 지정 평가자(부서장/상위 부서장) |
  | `GET` | `/api/evaluations/<eval_id>/` | 평가 상세 | 열람 규칙 적용 |
  | `PATCH` | `/api/evaluations/<eval_id>/` | 수정 `{score, comments?}`; `comments` 생략 시 유지, `""`는 삭제 | 현재 평가자 |
  | `POST` | `/api/evaluations/<eval_id>/submit/` | 제출 | 현재 평가자 |
  | `GET` | `/api/evaluations/<eval_id>/history/` | 이력 | 현재 평가자, 인사관리자 |
  | `POST` | `/api/evaluations/<eval_id>/return/` | 반려 `{reason}` | 인사관리자 |
  | `POST` | `/api/evaluations/<eval_id>/reassign/` | 평가자 재배정 `{evaluator_no, reason}` | 인사관리자 |
  | `POST` | `/api/evaluations/<eval_id>/confirm/` | 확정 | 인사관리자(작성 관여자 제외) |
  | `POST` | `/api/evaluations/<eval_id>/cancel-confirmation/` | 확정 취소 `{reason}` → `반려` | 인사관리자 |
  | `POST` | `/api/evaluations/<eval_id>/exclude/` | 평가 제외 `{reason}` | 인사관리자 |
  | `POST` | `/api/evaluations/<eval_id>/cancel-exclusion/` | 제외 취소 `{reason?}` | 인사관리자 |

  평가 응답 필드: `eval_id`, `emp_no`, `employee_name`, `eval_year`, `snapshot_dept_no`,
  `snapshot_pos_code`, `evaluator_no`, `evaluator_name`, `created_by`, `score`(문자열, 소수 2자리),
  `grade`, `comments`, `eval_status`(`작성중`/`제출`/`반려`/`확정`/`제외`), `confirmed_by`,
  `confirmed_at`, `updated_at`.
  이력 응답 필드: `history_id`, `eval_id`, `action`(`CREATE`/`REVISE`/`SUBMIT`/`RETURN`/
  `REASSIGN`/`CONFIRM`/`CANCEL_CONFIRMATION`/`EXCLUDE`/`CANCEL_EXCLUSION`), `from_status`, `to_status`, `actor_no`,
  `actor_name`, `from_evaluator_no`, `to_evaluator_no`, `score`, `reason`, `changed_at`.
  오류는 `{code, detail}` 형식이며 400(입력·`eval_year_not_allowed`), 403(`permission_denied`,
  `self_evaluation_not_allowed`, `confirmation_not_allowed`, `inactive_employee`), 404(없음·열람
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
- 환경변수·인프라 영향: 없음. `config/settings/base.py`의 `INSTALLED_APPS`, `config/urls.py`,
  `config/settings/test.py`의 `MIGRATION_MODULES`에 `evaluation`을 추가했다.

## 검증

- 실행한 테스트 (`backend/`):
  - `uv run pytest` — 171 passed (`test_evaluation_domain.py` 57건, `test_evaluation_service.py`
    29건, `test_evaluation_api.py` 21건, 계층 의존성 검사 포함)
  - `uv run ruff check .` — 통과
  - `uv run python manage.py check` — 이상 없음
  - `uv run python manage.py makemigrations --check --dry-run` — No changes detected
- 남은 검증: 실제 공유 DB `evaluations` 스키마·데이터 읽기 전용 대조, 병합 시 `0002` 적용 결과,
  프론트엔드 연동.

## 공용 문서 반영 후보

- Notion 원문: 등급 기준(EV-003), 부서장은 상위 부서장이 평가(EV-001), 평가 운영 정책
  (상태 흐름, 평가자 재배정, 작성자·확정자 분리, 확정 취소를 통한 정정, 휴직자·퇴사자 처리, 생성 연도 제한, 열람 범위)
  반영. 위 미정 항목 결정 요청. `FN-EV-001`~`FN-EV-004` 개별 기능 정의 확인.
- 저장소 명세·README: `01-overview-actors-states.md` 인사평가 상태 갱신, `06-api-specification.md`에
  평가 API 추가, `07-table-design-decisions.md`·`08-table-specification.md`에 `evaluation_history`,
  `created_by`, 고유 제약 반영, `evaluation-implementation-map.md`(규칙 ID ↔ 코드·테스트 대응표)
  신설 검토.
