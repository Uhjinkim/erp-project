# workforce / feature/workforce-employee-info 기여 문서

- 대상 모듈: `workforce`
- 작업 브랜치: `feature/workforce-employee-info`
- 기준 브랜치: `dev`
- 상태: 작성 중

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
- 제외 범위:
  - 인사이력(`emp_history`) 조회: 본인 조회 범위에 포함하지 않기로 결정, API 미구현
  - `HR-012` 변경 요청 보존기간
  - 개인정보 마스킹·암호화·조회 감사로그

## 설계 결정

- 관련 규칙·기능 ID: `HR-001`~`HR-004`, `HR-007`, `HR-011`, `FN-HR-001`~`FN-HR-005`, `FN-HR-011`
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

  - 상세·본인 응답 필드: `emp_no`, `person_id`, `name`, `birth_date`, `gender`, `dept_no`,
    `dept_name`, `position_code`, `position_name`, `tenure_status`, `email`, `phone`,
    `extension_no`, `address`, `bank_code`, `account_no`, `hire_date`, `term_date`
  - 업무 규칙 위반은 `400`과 `{"detail": "...", "field": "..."}`(`field`는 선택)
- 스키마·migration 변경:
  - 신규 테이블 `personal_info_change_requests`
    (`workforce/migrations/0003_personal_info_change_request.py`)
  - 공유 DB에는 적용하지 않았다. 배포 전 Notion 테이블 정의와 테이블명·컬럼을 대조해야 한다.
- 환경변수·인프라 영향: 없음
- 프론트엔드 영향: 일반 사원은 사원 목록 API를 호출하지 않고 본인 정보, 개인정보 변경 화면,
  부서 목록을 표시한다. 인사관리자에게는 변경 승인 목록이 추가로 표시된다.

## 검증

- 실행한 테스트:
  - `uv run pytest`: 71 passed (`tests/test_workforce_employee_info.py`,
    `tests/test_workforce_personal_info.py` 포함)
  - `uv run ruff check .`, `uv run python manage.py check`: 통과
  - `bun run lint`, `bun run build`: 통과
  - 로컬 SQLite 데모 DB에서 일반 사원·HR 관리자 화면과 요청→승인 반영 흐름 수동 확인
- 남은 검증:
  - SSH 터널을 통한 실제 공유 PostgreSQL 기준 E2E 확인(접속 정보 발급 후)

## 결정 사항

- 인사관리자도 `PATCH /employees/{emp_no}/`로 사원 이메일을 직접 바꿀 수 없다. 등록 이후
  사내 이메일은 변경 요청·승인 절차로만 변경한다(`HR-003`, 다른 값이면 `400`).
- 이메일 변경 승인 시 로그인 이메일(`accounts_users.email`)은 동기화하지 않고 별개로 유지한다.
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

## 미결정 사항

- 상급자가 없을 때의 "임시 팀장" 처리자: 현재 데이터에 임시 팀장을 표현할 역할·필드가 없어
  superuser만 처리하도록 구현했다. 표현 방식(역할 코드 또는 부서 필드) 결정 필요.
- 운영 원칙: 인사팀장에게 `HR_MANAGER` 역할을 부여한다. 역할이 없는 부서장은 처리자가 되지 않아
  급여계좌가 노출되지 않지만, 그 경우 인사관리자 요청은 superuser가 처리해야 한다.

## 공용 문서 반영 후보

- Notion 원문:
  - `HR-001` 예외 범위: 부서장 예외 없음, 인사관리자만 타인 정보 조회로 확정
  - `FN-HR-001` 조회 항목: 급여계좌 포함, 인사이력 제외
  - `HR-002` "연락처" 범위와 사원당 대기 요청 1건 제한
- 저장소 명세·README:
  - `docs/specs/notion/06-api-specification.md` 5.2 사원 표: 목록·상세 권한 변경, `me` 조회·수정,
    상세 응답 필드, 개인정보 변경 요청 API 추가
  - `docs/specs/notion/workforce-implementation-map.md`: `FN-HR-001`~`FN-HR-005`, `FN-HR-011`
    구현 완료 표시와 `FN-HR-001` 급여계좌 포함 여부 정리
