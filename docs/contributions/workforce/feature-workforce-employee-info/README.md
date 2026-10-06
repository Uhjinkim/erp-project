# workforce / feature/workforce-employee-info 기여 문서

- 대상 모듈: `workforce`
- 작업 브랜치: `feature/workforce-employee-info`
- 기준 브랜치: `dev`
- 상태: 작성 중

## 기능 범위

- 구현 범위:
  - `FN-HR-001` 본인 인사 정보 조회 API(`GET /api/workforce/employees/me/`)
  - `HR-001`에 따른 사원 목록·상세 조회 권한 제한
  - 인사 정보 상세 응답(부서명, 직급명, 생년월일, 성별, 주소 포함)
  - 프론트엔드 "내 인사 정보" 카드와 인사관리자용 사원 선택 상세 보기
- 제외 범위:
  - 급여계좌(`bank_code`, `account_no`) 조회: 응답에 포함하지 않기로 결정
  - 인사이력(`emp_history`) 조회: 본인 조회 범위에 포함하지 않기로 결정, API 미구현
  - 연락처·주소 직접 변경(`FN-HR-002`), 승인형 변경 요청(`FN-HR-003`~`FN-HR-005`, `FN-HR-011`)
  - 개인정보 마스킹·암호화·조회 감사로그

## 설계 결정

- 관련 규칙·기능 ID: `HR-001`, `HR-004`, `FN-HR-001`
- 도메인·애플리케이션 결정:
  - 조회 범위: 사원은 본인 정보만, 타인 정보는 인사관리자(`HR_MANAGER`)만 조회한다.
    부서장 예외는 두지 않는다. superuser는 기존 관리자 권한과 동일하게 허용한다.
  - 판정 규칙은 `workforce.domain.policies.can_view_employee_info`(순수 함수)에 두고,
    `workforce.application.services.can_view_employee`가 gateway로 역할을 조회해 호출한다.
  - 퇴사자 접근 차단(`HR-004`)은 기존 `ActiveEmployeeSessionAuthentication`이 담당하므로
    추가 검사를 두지 않았다.
  - 상세 조회(`retrieve`)에는 목록용 `search`, `dept_no`, `tenure_status` 필터를 적용하지 않는다.
    이전에는 상세 URL에 쿼리 파라미터가 붙으면 404가 날 수 있었다.

## 인터페이스와 데이터 영향

- API·권한 변경:

  | 메서드 | 경로 | 변경 전 | 변경 후 |
  | --- | --- | --- | --- |
  | `GET` | `/api/workforce/employees/` | 인증 사용자 | HR 관리자 |
  | `GET` | `/api/workforce/employees/{emp_no}/` | 인증 사용자, 목록과 같은 필드 | 본인 또는 HR 관리자, 상세 필드 |
  | `GET` | `/api/workforce/employees/me/` | 없음 | 인증 사용자(본인) — 신규 |

  - 상세·본인 응답 필드: `emp_no`, `person_id`, `name`, `birth_date`, `gender`, `dept_no`,
    `dept_name`, `position_code`, `position_name`, `tenure_status`, `email`, `phone`,
    `extension_no`, `address`, `hire_date`, `term_date` (모두 읽기 전용)
  - 계정에 연결된 사원이 없으면 `me`는 `404`와 `{"detail": "계정에 연결된 사원 정보가 없습니다."}`
  - 타인 상세 조회 시 일반 사원은 `403`
  - 생성·수정·삭제 권한과 요청 형식은 변경 없음(HR 관리자, 기존 `EmployeeSerializer`)
- 스키마·migration 변경: 없음
- 환경변수·인프라 영향: 없음
- 프론트엔드 영향: 일반 사원은 사원 목록 API를 호출하지 않고 본인 정보와 부서 목록만 표시한다.

## 검증

- 실행한 테스트:
  - `uv run pytest`: 39 passed (신규 `tests/test_workforce_employee_info.py` 포함)
  - `uv run ruff check .`, `uv run python manage.py check`: 통과
  - `uv run python manage.py makemigrations --check --dry-run`: No changes detected
    (SSH 터널 미연결로 migration 이력 일관성 확인 경고만 출력)
- 남은 검증:
  - `bun run lint`, `bun run build`: 작업 환경에 Bun/Node가 없어 미실행
  - 세션 로그인 상태에서 일반 사원·HR 관리자 화면 수동 확인

## 공용 문서 반영 후보

- Notion 원문:
  - `HR-001` 예외 범위: 부서장 예외 없음, 인사관리자만 타인 정보 조회로 확정
  - `FN-HR-001` 조회 항목: 급여계좌·인사이력 제외로 확정
- 저장소 명세·README:
  - `docs/specs/notion/06-api-specification.md` 5.2 사원 표: 목록·상세 권한 변경과 `me` 엔드포인트,
    상세 응답 필드 추가
  - `docs/specs/notion/workforce-implementation-map.md`: 후속 구현 목록에서 `FN-HR-001` 조회 부분 완료 표시
