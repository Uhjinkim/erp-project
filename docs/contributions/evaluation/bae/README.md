# evaluation / bae 기여 문서

- 대상 모듈: `evaluation`
- 작업 브랜치: `bae`
- 기준 브랜치: `dev`
- 상태: 작성 중

## 기능 범위

- 구현 범위: 인사평가 작성(부서장), 작성중 평가 수정(작성자), 확정(인사관리자), 상세·목록 조회
  백엔드 API와 `evaluations` 테이블의 Django 모델 상태 등록
- 제외 범위: 프론트엔드 화면, 평가 확정 취소·정정 이력, 평가 기간(오픈/마감) 관리

## 설계 결정

- 관련 규칙·기능 ID: `EV-001`~`EV-005`, `FN-EV-001`~`FN-EV-004`, `HR-004`~`HR-005`.
  저장소 스냅샷에는 EV 규칙이 요약(부서장 평가, 자기평가 금지, 점수별 등급, HR 확정)으로만 있어
  개별 ID와 동작의 1:1 대응은 Notion 원문으로 확인이 필요하다. 코드·테스트에서는 아래 대응을
  가정했다: EV-001 부서장 평가, EV-002 자기평가 금지, EV-003 점수별 등급, EV-004 HR 확정.
- 등급 기준(사용자 확인, 2026-10-06): 100점 만점 기준 S 90점 이상, A 80점 이상, B 70점 이상,
  C 70점 미만. `evaluation/domain/value_objects.py`의 `GRADE_THRESHOLDS` 한 곳에서 관리한다.
- 도메인·애플리케이션 결정:
  - 상태는 `작성중 → 확정` 단방향이다. 확정된 평가는 수정·재확정할 수 없다(409).
  - 평가자는 작성 시점에 대상자 소속 부서의 부서장(`departments.head_emp_no`)이어야 한다.
    대상자가 소속 부서의 부서장이면 상위 부서(`parent_dept_no`)의 부서장이 평가한다
    (사용자 확인, 2026-10-06). 상위 부서장이 하위 부서원을 건너뛰어 평가할 수는 없다.
    평가자가 본인이 되는 경우는 자기평가로 거절한다.
  - **미정**: 부서장이 없는 부서의 사원, 상위 부서(또는 상위 부서장)가 없는 최상위 부서장은
    현재 평가할 수 없다(403). 대체 평가자 정책 확인이 필요하다.
  - 작성 시점의 대상자 부서·직급을 `snapshot_dept_no`, `snapshot_pos_code`에 보존한다.
  - 등급은 점수로부터 서버가 계산해 저장하며 클라이언트가 지정할 수 없다.
  - 점수는 0.00~100.00, 소수점 둘째 자리까지(`numeric(5,2)`).
  - 재직 사원만 평가 대상이 되며, 평가자·확정자·조회자도 재직 사원이어야 한다.
  - **잠정 결정(확인 필요)**: 사원·연도당 평가 1건만 허용한다. 공유 DB에 대응 고유 제약이 있는지
    확인되지 않아 애플리케이션 검사만 수행하므로 동시 요청 시 중복이 생길 수 있다.
  - **잠정 결정(확인 필요)**: 조회 범위 — 인사관리자는 전체, 평가 작성자는 본인이 작성한 평가,
    평가 대상자는 확정된 본인 평가만 조회한다. 권한 밖 평가는 존재 여부를 숨기기 위해 404로 응답한다.
  - 수정은 최초 작성자만 가능하다. 작성 후 부서장이 바뀐 경우의 처리 방식은 미정이다.
  - 확정과 수정은 저장 시 `eval_status = '작성중'` 조건부 UPDATE로 처리해 동시 확정 후 덮어쓰기를
    막는다.
  - 작성 요청은 평가 권한을 대상자 존재·재직 여부보다 먼저 확인한다. 권한이 없으면 대상자가
    없는 사번·퇴사자·부서장·일반 사원 모두 같은 403 `permission_denied` 응답을 받아 타인의
    재직 상태나 역할을 추정할 수 없다(HR-001).
  - Django admin의 평가 화면은 읽기 전용이다. 등급·상태 규칙을 우회하지 않도록 쓰기는 API로만 한다.

## 인터페이스와 데이터 영향

- API·권한 변경 (모두 로그인 필요, 사원번호 연결 계정만 사용):

  | 메서드 | 경로 | 설명 | 권한 |
  | --- | --- | --- | --- |
  | `GET` | `/api/evaluations/?year=YYYY` | 평가 목록 | 조회 범위 규칙 적용 |
  | `POST` | `/api/evaluations/` | 평가 작성 `{emp_no, eval_year, score, comments?}` | 대상자 소속 부서장(부서장이 대상이면 상위 부서장) |
  | `GET` | `/api/evaluations/<eval_id>/` | 평가 상세 | 조회 범위 규칙 적용 |
  | `PATCH` | `/api/evaluations/<eval_id>/` | 작성중 평가 수정 `{score, comments?}`; `comments` 생략 시 기존 의견 유지, `""`는 삭제 | 평가 작성자 |
  | `POST` | `/api/evaluations/<eval_id>/confirm/` | 평가 확정 | 인사관리자(`HR_MANAGER`) |

  응답 필드: `eval_id`, `emp_no`, `employee_name`, `eval_year`, `snapshot_dept_no`,
  `snapshot_pos_code`, `evaluator_no`, `evaluator_name`, `score`(문자열, 소수 2자리), `grade`,
  `comments`, `eval_status`, `confirmed_by`, `confirmed_at`, `updated_at`.
  오류는 `{code, detail}` 형식이며 400(입력), 403(권한·자기평가·비재직), 404(없음·조회 권한 없음),
  409(중복·확정 후 변경)를 사용한다.
- 스키마·migration 변경: `evaluation/migrations/0001_initial.py`는 공유 DB에 이미 존재하는
  `evaluations` 테이블을 등록하는 **state-only** 마이그레이션이다(`database_operations=[]`).
  ERD에 NULL 허용 여부가 없어 `snapshot_dept_no`, `snapshot_pos_code`, `comments`,
  `confirmed_by`, `confirmed_at`은 nullable로 선언했다. 배포 전 실제 DB의 `pg_constraint`,
  `information_schema`와 대조해야 한다. 공유 DB에 migrate를 실행하지 않았다.
- 환경변수·인프라 영향: 없음. `config/settings/base.py`의 `INSTALLED_APPS`, `config/urls.py`,
  `config/settings/test.py`의 `MIGRATION_MODULES`에 `evaluation`을 추가했다.

## 검증

- 실행한 테스트 (`backend/`):
  - `uv run pytest` — 127 passed (신규 `test_evaluation_domain.py`, `test_evaluation_service.py`,
    `test_evaluation_api.py` 63건 포함, 계층 의존성 검사 포함)
  - `uv run ruff check .` — 통과
  - `uv run python manage.py check` — 이상 없음
  - `uv run python manage.py makemigrations --check --dry-run` — No changes detected
- 남은 검증: 실제 공유 DB `evaluations` 스키마(PK·FK·NULL·고유 제약, `eval_status` 값) 읽기 전용
  대조, 프론트엔드 연동, `docs-workflow check`.

## 공용 문서 반영 후보

- Notion 원문: 등급 기준(S≥90, A≥80, B≥70, C<70)을 EV-003에, 부서장은 상위 부서장이
  평가한다는 규칙을 EV-001에 명시. 최상위 부서장·부서장 공석 시 대체 평가자 정책 확정 요청. 사원·연도당
  1건 제한, 평가 대상자의 작성중 평가 비공개, 부서장 교체 시 수정 권한 정책 확정 요청.
  `FN-EV-001`~`FN-EV-004` 개별 기능 정의 확인.
- 저장소 명세·README: `06-api-specification.md`에 위 평가 API 추가, `08-table-specification.md`
  평가 절의 "Django 모델 없음" 문구 갱신, `evaluation-implementation-map.md`(규칙 ID ↔ 코드·테스트
  대응표) 신설 검토.
