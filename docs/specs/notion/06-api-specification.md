# 06. API 명세

- Notion 원문: <https://app.notion.com/p/3e58eced448d81f4ade6c86fc337bd26>
- 원문 최종 수정: 2026-10-12
- 저장소 코드 확인: 2026-10-29 (인증 메뉴 안내 필드 추가; Notion 재조회 없음)
- 기준 구현: Django REST Framework 백엔드의 현재 라우트, 뷰, 직렬화 코드
- 개발 직접 호출 기본 URL: `http://localhost:8000`
- nginx 통합 개발환경 기본 URL: `http://localhost:8080`

이 문서는 현재 저장소에 구현된 API의 동작을 코드 기준으로 정리한 명세다.
2026-10-12 기여 문서 부분 통합으로 인사·게시판·평가·급여의 기본 라우트를 보완했다.
추가 정책·구현 차이는 [모듈 검토 의제](../../reports/2026-10-12_module-review-agenda.md)에
분리했으며, 아래 현재 동작 기록이 제품 정책 승인이나 공유 DB 적용 확인을 뜻하지 않는다. 별도 OpenAPI 또는
Swagger 엔드포인트는 현재 구현되어 있지 않다. 모든 API 경로는 후행 슬래시(`/`)를 사용한다.

## 1. 공통 규칙

### 1.1 요청과 응답

- 요청과 응답 본문은 JSON을 사용한다.
- 날짜는 `YYYY-MM-DD`, 일시는 ISO 8601 형식을 사용한다.
- 목록 API는 현재 페이지네이션 없이 JSON 배열을 반환한다.
- `DELETE` 성공 응답은 `204 No Content`이며 본문이 없다.
- Django REST Framework의 일반 입력 오류는 필드별 오류 배열로 반환된다.

```json
{
  "email": ["이 필드는 필수 항목입니다."]
}
```

### 1.2 세션 인증과 CSRF

일반 API는 Django 서버 세션으로 인증한다. 브라우저 클라이언트의 기본 흐름은 다음과 같다.

1. `GET /api/auth/csrf/`를 호출해 `csrftoken` 쿠키를 받는다.
2. `POST /api/auth/login/`에 쿠키 값과 같은 `X-CSRFToken` 헤더를 보낸다.
3. 로그인 성공 시 발급되는 HttpOnly `sessionid` 쿠키를 이후 요청에 포함한다.
4. 세션 인증 상태에서 `POST`, `PUT`, `PATCH`, `DELETE` 요청을 보낼 때 `X-CSRFToken` 헤더를 포함한다.

세션 만료 시간은 로그인 시점부터 8시간이다. 인증되지 않은 요청, 권한이 없는 요청, CSRF 검증에
실패한 요청은 주로 `403 Forbidden`으로 반환된다. 계정에 연결된 사원이 더 이상 재직 상태가
아니면 기존 세션으로도 서비스를 사용할 수 없다.

### 1.3 권한 구분

| 권한 | 설명 |
| --- | --- |
| 공개 | 로그인 없이 호출 가능 |
| 인증 사용자 | 유효한 세션이 필요 |
| HR 관리자 | 슈퍼유저 또는 활성 `HR_MANAGER` 역할이 필요 |
| 본인/승인자 | 휴가 신청의 신청자 또는 현재 승인자 조건을 도메인 규칙으로 검사 |

`HR_MANAGER`와 `HR_LEAVE_APPROVER`는 서로 다른 역할이다. 전자는 인사 데이터 관리 권한이며,
후자는 부서장으로 승인자를 정할 수 없을 때 사용하는 휴가 승인 담당자다.

### 1.4 휴가 API의 사용자 식별 방식

휴가 API는 설정에 따라 요청 사원을 다르게 식별한다.

| `VACATION_INTEGRATION_MODE` | 식별 방식 |
| --- | --- |
| `development` | 요청 헤더 `X-Employee-No: {사번}` 사용 |
| `database` | 인증 세션에 연결된 사원의 사번 사용 |

`development` 모드에서 헤더가 없거나 정수가 아니면 `403`을 반환한다. `database` 모드에서는
`X-Employee-No` 헤더를 신뢰하지 않는다. `DEVELOPMENT_OFFLINE_MODE=true`이거나 사원 연동이
준비되지 않은 경우 모든 휴가 API가 `503 Service Unavailable`을 반환한다.

## 2. 엔드포인트 요약

### 2.1 상태 및 인증

| 메서드 | 경로 | 권한 | 설명 |
| --- | --- | --- | --- |
| `GET` | `/api/health/` | 공개 | 시스템과 외부 서비스 연결 상태 조회 |
| `GET` | `/api/auth/csrf/` | 공개 | CSRF 쿠키 발급 |
| `POST` | `/api/auth/login/` | 공개 + CSRF | 이메일 로그인과 세션 발급 |
| `POST` | `/api/auth/logout/` | 인증 사용자 | 현재 세션 폐기 |
| `GET` | `/api/auth/me/` | 인증 사용자 | 현재 계정, 사원, 역할 조회 |

### 2.2 계정 관리

| 메서드 | 경로 | 권한 | 설명 |
| --- | --- | --- | --- |
| `GET` | `/api/auth/` | 인증 사용자 | 계정 API 탐색 루트 |
| `GET`, `POST` | `/api/auth/accounts/` | HR 관리자 | 계정 목록 조회, 생성 |
| `GET`, `PUT`, `PATCH`, `DELETE` | `/api/auth/accounts/{id}/` | HR 관리자 | 계정 상세 조회, 수정, 삭제 |

### 2.3 사원 및 조직

| 메서드 | 경로 | 권한 | 설명 |
| --- | --- | --- | --- |
| `GET` | `/api/workforce/` | 인증 사용자 | 사원·조직 API 탐색 루트 |
| `GET`, `POST` | `/api/workforce/persons/` | HR 관리자 | 인적사항 목록 조회, 생성 |
| `GET`, `PUT`, `PATCH`, `DELETE` | `/api/workforce/persons/{person_id}/` | HR 관리자 | 인적사항 상세 관리 |
| `GET` | `/api/workforce/employees/` | HR 관리자 | 사원 목록 조회와 검색; 평가·급여는 전용 대상 API 사용(INT-01) |
| `POST` | `/api/workforce/employees/` | HR 관리자 | 사원 생성 |
| `GET` | `/api/workforce/employees/{emp_no}/` | 본인 또는 HR 관리자 | 사원 상세 조회 |
| `PUT`, `PATCH`, `DELETE` | `/api/workforce/employees/{emp_no}/` | HR 관리자 | 사원 수정, 삭제 |
| `GET` | `/api/workforce/employees/{emp_no}/roles/` | HR 관리자 | 사원의 역할 배정 이력 조회 |
| `POST` | `/api/workforce/employees/{emp_no}/roles/` | HR 관리자 | 역할 부여 |
| `POST` | `/api/workforce/employees/{emp_no}/roles/{assignment_id}/revoke/` | HR 관리자 | 역할 회수 |
| `GET`, `POST` | `/api/workforce/departments/` | 조회: 인증 사용자, 생성: HR 관리자 | 부서 목록 조회, 생성 |
| `GET`, `PUT`, `PATCH`, `DELETE` | `/api/workforce/departments/{dept_no}/` | 조회: 인증 사용자, 변경: HR 관리자 | 부서 상세 관리 |
| `GET`, `POST` | `/api/workforce/positions/` | 조회: 인증 사용자, 생성: HR 관리자 | 직급 목록 조회, 생성 |
| `GET`, `PUT`, `PATCH`, `DELETE` | `/api/workforce/positions/{position_code}/` | 조회: 인증 사용자, 변경: HR 관리자 | 직급 상세 관리 |
| `GET` | `/api/workforce/roles/` | 인증 사용자 | 역할 목록 조회 |
| `GET` | `/api/workforce/roles/{role_code}/` | 인증 사용자 | 역할 상세 조회 |

두 탐색 루트는 Django REST Framework 라우터가 자동 생성하며, 하위 목록 API의 URL을 JSON으로
반환한다. 업무 데이터 조회용 엔드포인트는 아니다.

### 2.4 휴가

| 메서드 | 경로 | 권한/행위자 | 설명 |
| --- | --- | --- | --- |
| `GET` | `/api/vacations/types/` | 식별된 재직 사원 | 등록된 휴가 유형 조회 |
| `GET` | `/api/vacations/requests/` | 식별된 재직 사원 | 내 휴가 신청 목록 조회 |
| `POST` | `/api/vacations/requests/` | 식별된 재직 사원 | 휴가 신청 |
| `GET` | `/api/vacations/approvals/` | 식별된 재직 사원 | 내가 처리할 승인 목록 조회 |
| `POST` | `/api/vacations/requests/{request_id}/cancel/` | 신청자 본인 | 대기 신청 취소 |
| `POST` | `/api/vacations/requests/{request_id}/approve/` | 현재 승인자 | 대기 신청 승인 |
| `POST` | `/api/vacations/requests/{request_id}/reject/` | 현재 승인자 | 대기 신청 반려 |
| `POST` | `/api/vacations/requests/{request_id}/recall/` | 기존 승인자 | 승인 신청 회수 |
| `PUT` | `/api/vacations/requests/{request_id}/resubmit/` | 신청자 본인 | 회수 신청 수정·재신청 |
| `GET` | `/api/vacations/requests/{request_id}/history/` | 신청자, 승인자, HR 관리자 | 상태 변경 이력 조회 |

## 3. 상태 확인 API

### 3.1 시스템 상태 조회

`GET /api/health/`

항상 HTTP `200`으로 각 서비스의 상태를 보고한다. 외부 서비스 연결 실패는 HTTP 오류 대신 응답
본문의 상태로 표현된다.

```json
{
  "status": "online",
  "environment": "development",
  "services": {
    "backend": {"status": "connected"},
    "database": {"status": "connected"},
    "redis": {"status": "connected"},
    "workforce": {"status": "connected"}
  },
  "end_to_end": {"status": "connected"}
}
```

| 필드 | 가능한 값 |
| --- | --- |
| 최상위 `status` | `online`, `degraded`, `offline` |
| 서비스 `status` | `connected`, `disconnected`, `not_configured`, `offline_simulation`, `development_simulation` |
| `end_to_end.status` | `connected`, `disconnected` |

연결 실패 시 서비스 객체에 `detail`이 추가될 수 있다. `DEBUG=false`에서는 예외 클래스명만
노출하고, 개발 디버그 모드에서는 예외 메시지도 포함한다.

## 4. 인증 및 계정 API

### 4.1 CSRF 쿠키 발급

`GET /api/auth/csrf/`

성공: `200 OK`

```json
{
  "detail": "CSRF 쿠키가 설정되었습니다."
}
```

응답에 `csrftoken` 쿠키가 함께 설정된다.

### 4.2 로그인

`POST /api/auth/login/`

요청 필드:

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `email` | email 문자열 | 예 | 앞뒤 공백 제거 후 소문자로 인증 |
| `password` | 문자열 | 예 | 공백을 원문 그대로 사용 |

```json
{
  "email": "employee@example.com",
  "password": "password"
}
```

성공: `200 OK`. 응답 형식은 현재 사용자 조회와 같다.

```json
{
  "id": 1,
  "email": "employee@example.com",
  "is_staff": false,
  "is_superuser": false,
  "is_department_head": false,
  "employee": {
    "emp_no": 1001,
    "name": "홍길동",
    "dept_no": 10,
    "dept_name": "개발팀",
    "position_code": "STAFF",
    "position_name": "사원",
    "tenure_status": "재직"
  },
  "roles": ["HR_MANAGER"]
}
```

계정에 연결된 사원이 없으면 `employee`는 `null`, `roles`는 빈 배열이다. 이메일 또는 비밀번호가
틀리거나 비활성 계정 또는 비재직 사원인 경우 `400 Bad Request`를 반환한다.

```json
{
  "non_field_errors": ["이메일 또는 비밀번호가 올바르지 않습니다."]
}
```

### 4.3 로그아웃

`POST /api/auth/logout/`

성공: `204 No Content`. 현재 서버 세션을 폐기한다.

### 4.4 현재 사용자 조회

`GET /api/auth/me/`

성공: `200 OK`. 응답 형식은 로그인 성공 응답과 같다. `roles`에는 조회 시점에 유효한 역할만
역할 코드 오름차순으로 포함된다. 미래에 시작하는 역할과 이미 회수된 역할은 제외된다.
로그인·현재 사용자 응답의 읽기 전용 `is_department_head`는 현재 어느 부서에든 부서장으로
지정된 사원인지 나타낸다. 미연결 계정은 false다. 프론트 메뉴 안내용이며 평가·휴가 권한을
추가 부여하지 않는다. 기존 DB 스키마·인증 실패·CSRF 계약은 유지한다.

### 4.5 계정 관리

계정 객체:

| 필드 | 타입 | 쓰기 | 설명 |
| --- | --- | --- | --- |
| `id` | 정수 | 읽기 전용 | 계정 ID |
| `email` | email 문자열 | 필수 | 고유 이메일, 소문자로 저장 |
| `password` | 문자열 | 생성 시 필수 | 최소 8자, 응답에서 제외 |
| `emp_no` | 정수 또는 `null` | 선택 | 연결할 사번, 사원당 계정 하나 |
| `is_active` | boolean | 선택 | 계정 활성 여부 |
| `is_hr_manager` | boolean | 읽기 전용 | 현재 활성 HR 관리자 역할 여부 |

목록은 이메일 오름차순의 배열이다. `PUT`은 전체 필드를, `PATCH`는 전달한 필드만 갱신한다.
비밀번호가 수정 요청에 포함되면 평문 저장이 아니라 비밀번호 해시 갱신을 수행한다.

## 5. 사원 및 조직 API

### 5.1 인적사항

인적사항 객체:

| 필드 | 타입 | 필수/허용값 |
| --- | --- | --- |
| `person_id` | 정수 | 생성 시 자동 발급, 수정 가능 필드 아님 |
| `name` | 문자열 | 필수, 최대 50자 |
| `birth_date` | 날짜 또는 `null` | 선택 |
| `gender` | 문자열 또는 `null` | 선택, 최대 1자 |

목록은 `person_id` 오름차순이다. 인적사항 API 전체는 HR 관리자 전용이다.

### 5.2 사원

사원 객체:

| 필드 | 타입 | 필수/설명 |
| --- | --- | --- |
| `emp_no` | 정수 | 필수, 사번 겸 리소스 식별자 |
| `person_id` | 정수 | 필수, 기존 인적사항 ID |
| `name` | 문자열 | 읽기 전용, 연결된 인적사항의 이름 |
| `dept_no` | 정수 또는 `null` | 선택, 기존 부서 번호 |
| `position_code` | 문자열 또는 `null` | 선택, 기존 직급 코드 |
| `tenure_status` | 문자열 | 필수, `재직`, `휴직`, `퇴사` 중 하나 |
| `email` | email 문자열 또는 `null` | 선택, 고유하며 소문자로 정규화 |
| `phone` | 문자열 또는 `null` | 선택, 최대 20자 |
| `extension_no` | 문자열 또는 `null` | 선택, 최대 20자 |
| `hire_date` | 날짜 | 필수 |
| `term_date` | 날짜 또는 `null` | 선택 |

사원 목록 조회는 다음 쿼리 파라미터를 지원하며 함께 사용할 수 있다.

| 파라미터 | 설명 |
| --- | --- |
| `search` | 이름과 이메일 부분 일치 검색. 숫자만 입력하면 사번 완전 일치도 함께 검색 |
| `dept_no` | 부서 번호 완전 일치 |
| `tenure_status` | 재직 상태 완전 일치 |

예: `GET /api/workforce/employees/?search=홍&dept_no=10&tenure_status=재직`

목록은 사번 오름차순이다. 퇴사일 규칙은 다음과 같다.

- `term_date`는 `hire_date`보다 빠를 수 없다.
- `tenure_status=퇴사`이면 `term_date`가 필수다.
- `퇴사`가 아닌 사원에게는 `term_date`를 지정할 수 없다.

### 5.3 부서

부서 객체:

| 필드 | 타입 | 필수/설명 |
| --- | --- | --- |
| `dept_no` | 정수 | 필수, 부서 번호 겸 리소스 식별자 |
| `dept_name` | 문자열 | 필수, 최대 100자 |
| `parent_dept_no` | 정수 또는 `null` | 선택, 상위 부서 번호 |
| `head_emp_no` | 정수 또는 `null` | 선택, 부서장 사번 |

부서 계층은 순환할 수 없다. 부서장은 재직 중이면서 해당 부서에 소속된 사원이어야 한다. 목록은
부서 번호 오름차순이다.

### 5.4 직급

직급 객체:

| 필드 | 타입 | 필수/설명 |
| --- | --- | --- |
| `position_code` | 문자열 | 필수, 최대 20자, 리소스 식별자 |
| `position_name` | 문자열 | 필수, 최대 50자 |
| `sort_order` | 정수 | 선택, 기본값 `0` |

목록은 `sort_order`, `position_code` 순으로 정렬된다.

### 5.5 역할 조회와 사원 역할 관리

역할 객체:

```json
{
  "role_code": "HR_MANAGER",
  "role_name": "인사 관리자"
}
```

역할 목록은 역할 코드 오름차순이다. 역할 자체는 API에서 생성, 수정, 삭제할 수 없다.

역할 배정 객체:

| 필드 | 타입 | 쓰기 | 설명 |
| --- | --- | --- | --- |
| `employee_role_id` | 정수 | 읽기 전용 | 역할 배정 ID |
| `emp_no` | 정수 | 경로 값으로 자동 설정 | 사번 |
| `role_code` | 문자열 | 역할 부여 시 필수 | 기존 역할 코드 |
| `assigned_at` | 일시 | 읽기 전용 | 부여 일시 |
| `revoked_at` | 일시 또는 `null` | 읽기 전용 | 회수 일시 |

역할 부여 요청:

```json
{
  "role_code": "HR_MANAGER"
}
```

성공 시 `201 Created`와 역할 배정 객체를 반환한다. 다음 규칙을 위반하면 `400 Bad Request`다.

- 재직 중인 사원에게만 역할을 부여할 수 있다.
- 같은 역할의 활성 배정을 중복 생성할 수 없다.
- 활성 `HR_LEAVE_APPROVER`는 전체에서 한 명만 존재할 수 있다.

역할 회수 성공 시 `200 OK`와 `revoked_at`이 기록된 역할 배정 객체를 반환한다. 경로의 배정 ID가
해당 사원의 활성 역할이 아니면 `404 Not Found`를 반환한다.

## 6. 휴가 API

### 6.1 휴가 유형 조회

`GET /api/vacations/types/`

성공: `200 OK`

```json
[
  {
    "type_id": "ANNUAL",
    "type_name": "연차",
    "is_paid": true,
    "deduct_days": 1.0
  }
]
```

등록된 휴가 유형을 `type_id` 오름차순으로 반환한다. 현재 데이터 모델에는 활성 여부 필드가 없다.

2026-10-29 구현 확장: 신청·재신청 화면은 `?include_balance=true`로 같은 응답의 각 유형에
`remaining_days`를 함께 받는다. 값은 소수 문자열(예: `"3.50"`, `"0"`) 또는 잔여 검사 제한이
없는 경우 `null`이다. 옵션 생략/`false`는 기존 응답을 유지하며, 이외의 값은 400이다.
인증으로 식별한 재직 사원 본인의 잔여만 반환하며 별도 사번 query는 사용하지 않는다.
DB 모드의 차감형 잔여 행 누락은 0, 비차감형은 `null`이다. 개발 설정 모드는 신청 검증과
동일하게 설정 없는 유형의 제한을 생략한다. 전체 유형의 잔여는 일괄 조회하며 대기 신청은
차감하지 않는다. 조회 후 다른 승인으로 변경될 수 있으므로 신청·승인의 기존 재검증을 유지한다.
이는 저장소 구현 계약이며 Notion 원문 검증·갱신을 의미하지 않는다.

2026-10-29 사용자 확정에 따라 유형 응답의 `balance_type_id`는 잔여를 사용하는 유형 코드다.
`HALF`의 `balance_type_id`는 `ANNUAL`이며, 잔여 포함 응답에서 두 유형은 같은 연차 잔여를
반환한다. 반차 잔여 행이 없어도 연차 잔여로 검증·차감·복원한다. `deduct_days=0.5`는 화면의
기본 사용 일수 안내이며 실제 차감은 제출한 `use_days`를 사용하고 다시 0.5를 곱하지 않는다.

### 6.2 휴가 신청 객체

```json
{
  "request_id": 15,
  "employee_no": 1001,
  "type_id": "ANNUAL",
  "start_datetime": "2026-10-01T09:00:00+09:00",
  "end_datetime": "2026-10-01T18:00:00+09:00",
  "use_days": 1.0,
  "status": "대기",
  "approver_no": 2001,
  "approved_at": null,
  "reject_reason": null,
  "request_reason": "개인 사유"
}
```

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `request_id` | 정수 | 휴가 신청 ID |
| `employee_no` | 정수 | 신청자 사번 |
| `type_id` | 문자열 | 휴가 유형 ID |
| `start_datetime` | 일시 | 시작 일시 |
| `end_datetime` | 일시 | 종료 일시 |
| `use_days` | 숫자 | 차감 일수 |
| `status` | 문자열 | `대기`, `승인`, `반려`, `취소`, `회수` |
| `approver_no` | 정수 | 현재 또는 기존 승인자 사번 |
| `approved_at` | 일시 또는 `null` | 승인 일시 |
| `reject_reason` | 문자열 또는 `null` | 반려 사유 |
| `request_reason` | 문자열 또는 `null` | 신청 사유 |

### 6.3 내 신청 목록

`GET /api/vacations/requests/`

성공: `200 OK`. 요청 사원이 신청한 휴가를 최신 신청 ID 순으로 반환한다.

### 6.4 휴가 신청

`POST /api/vacations/requests/`

요청 필드:

| 필드 | 타입 | 필수/제약 |
| --- | --- | --- |
| `type_id` | 문자열 | 필수, 최대 20자, 존재하는 휴가 유형 |
| `start_datetime` | ISO 8601 일시 | 필수 |
| `end_datetime` | ISO 8601 일시 | 필수, 시작보다 빠를 수 없음 |
| `use_days` | decimal | 필수, `0.01` 이상, 최대 정수 1자리·소수 2자리 |
| `reason` | 문자열 또는 `null` | 선택, 최대 255자, 빈 문자열은 `null`로 처리 |

```json
{
  "type_id": "ANNUAL",
  "start_datetime": "2026-10-01T09:00:00+09:00",
  "end_datetime": "2026-10-01T18:00:00+09:00",
  "use_days": "1.00",
  "reason": "개인 사유"
}
```

성공: `201 Created`. 생성된 휴가 신청 객체를 반환한다. 승인자는 다음 순서로 자동 결정된다.

1. 신청자와 다른 재직 중 부서장이 있으면 해당 부서장을 사용한다.
2. 신청자가 소속 부서장이면 직계 상위 부서의 재직 중 부서장을 사용한다.
3. 사용할 부서장이 없으면 활성 `HR_LEAVE_APPROVER`가 정확히 한 명일 때 그 사원을 사용한다.
4. 승인자를 결정할 수 없으면 신청을 거절한다.

DB 모드에서는 차감형 유형의 잔여일수 행이 없으면 0일로 처리하고, `deduct_days=0`인
유형은 잔여 검사를 생략한다. 개발 모드는 설정된 유형별 일수에서 이번 구현으로 승인된
사용량을 빼며, 설정에 잔여일수가 없는 유형은 제한을 생략한다.

신청·재신청에서 잔여일수를 검사하되 대기 신청은 잔여일수를 예약하지 않는다. 승인 시
잔여일수를 다시 검사하고 차감하며, 회수 시 이번 구현에서 차감한 일수만 복원한다.
잔여 변경·상태 변경·이력 저장은 같은 트랜잭션에서 처리한다. 승인 시 부족하면
400 `insufficient_leave_days`로 거절하고 대기 상태를 유지한다.

### 6.5 승인 목록

`GET /api/vacations/approvals/`

성공: `200 OK`. 현재 구현은 역할과 관계없이 `approver_no`가 요청 사번과 일치하는 신청만
최신 신청 ID 순으로 반환한다.

### 6.6 상태 변경

본문 없이 호출하는 API:

- `POST /api/vacations/requests/{request_id}/cancel/`
- `POST /api/vacations/requests/{request_id}/approve/`

사유가 필요한 API:

- `POST /api/vacations/requests/{request_id}/reject/`
- `POST /api/vacations/requests/{request_id}/recall/`

```json
{
  "reason": "처리 사유"
}
```

`reason`은 공백일 수 없고 최대 255자다. 성공 시 모두 `200 OK`와 변경된 휴가 신청 객체를
반환한다.

지원하는 상태 전이는 다음과 같다.

| 작업 | 행위자 | 이전 상태 | 다음 상태 |
| --- | --- | --- | --- |
| 취소 | 신청자 | `대기` | `취소` |
| 승인 | 현재 승인자 | `대기` | `승인` |
| 반려 | 현재 승인자 | `대기` | `반려` |
| 회수 | 기존 승인자 | `승인` | `회수` |
| 재신청 | 신청자 | `회수` | `대기` |

현재 구현에는 `반려` 또는 `취소` 상태에서의 재신청 전이가 없다.

### 6.7 수정·재신청

`PUT /api/vacations/requests/{request_id}/resubmit/`

요청 본문은 휴가 신청과 동일하다. 신청자 본인의 `회수` 상태 신청만 재신청할 수 있다. 재신청
시점의 조직과 역할을 기준으로 승인자를 다시 결정하고 잔여일수를 다시 검사한다. 성공 시
`200 OK`와 `대기` 상태의 신청 객체를 반환한다.

### 6.8 변경 이력

`GET /api/vacations/requests/{request_id}/history/`

성공: `200 OK`

```json
[
  {
    "history_id": 21,
    "request_id": 15,
    "from_status": null,
    "to_status": "대기",
    "actor_employee_no": 1001,
    "reason": "개인 사유",
    "changed_at": "2026-09-25T10:00:00+09:00"
  },
  {
    "history_id": 22,
    "request_id": 15,
    "from_status": "대기",
    "to_status": "승인",
    "actor_employee_no": 2001,
    "reason": null,
    "changed_at": "2026-09-25T10:10:00+09:00"
  }
]
```

이력 응답에는 `before_values`, `after_values` 스냅샷이 추가된다. 유형, 시작·종료 일시,
사용일수(정밀도 보존 문자열), 승인자, 신청 사유, 승인 시각, 반려 사유, 차감 여부를 포함한다.
최초 신청의 `before_values`와 기존 이력의 스냅샷은 `null`이다. 기존 이력에서 유실된
변경 내용은 자동 복구하지 않는다.

이력은 변경 일시와 이력 ID 오름차순이다. 신청자, 해당 신청의 승인자, HR 관리자만 조회할 수
있다.

2026-10-13 변경은 vacation migration 0003을 필요로 한다. 사용자 대상 확인 후 공유 개발 DB
`erp_dev.public`에 적용하고 스키마·적용 기록을 확인했다. 운영 환경 적용은 수행하지 않았으며,
[수정 보고서](../../reports/2026-10-13_vacation-fixes.md)에 검증·배포 제한을 기록했다.

### 6.9 휴가 오류 응답

휴가 도메인 오류는 다음 형식을 사용한다.

```json
{
  "code": "invalid_status_transition",
  "detail": "대기 상태의 신청만 처리할 수 있습니다. 현재 상태: 승인"
}
```

| HTTP 상태 | 코드 | 발생 조건 |
| --- | --- | --- |
| `400` | `invalid_period` | 종료일시가 시작일시보다 빠름 |
| `400` | `invalid_use_days` | 차감일수 도메인 규칙 위반 |
| `400` | `invalid_status_transition` | 허용되지 않은 상태 전이 |
| `400` | `insufficient_leave_days` | 신청일수가 잔여일수 초과 |
| `400` | `inactive_employee` | 재직 사원이 아님 |
| `400` | `approver_not_found` | 승인자를 결정할 수 없음 |
| `403` | `permission_denied` | 사용자 식별 실패 또는 행위자 권한 없음 |
| `404` | `request_not_found` | 휴가 신청이 없음 |
| `404` | `type_not_found` | 휴가 유형이 없음 |

입력 직렬화 단계에서 발생한 오류는 위 `code/detail` 형식이 아니라 일반 필드별 오류 형식이다.
연동 비활성화 오류는 `503`과 `detail`만 반환한다.

```json
{
  "detail": "사원·인증 연동이 아직 구성되지 않았습니다."
}
```

## 7. 기여 문서 부분 통합 API

- 코드 확인일: 2026-10-14. 세션 인증·CSRF·사원번호 연결이 필요하다.
- 아래는 기존 제품 기능에 대응하는 기본 경로와 현재 transport 동작이다.
- 댓글과 평가 추가 워크플로 API는 이번 정본 통합에서 제외했다. 해당 경로가 코드에서 제거된 것은 아니다.
- 현재 구현의 보류 제한은 의제에 연결한다. 모듈 전체의 명세 준수 완료를 선언하지 않는다.

### 7.1 본인 인사정보와 개인정보 수정 요청

| 메서드 | 경로 | 현재 동작 |
| --- | --- | --- |
| GET | `/api/workforce/employees/me/` | 연결된 사원 본인의 상세 조회; 본인 직접 수정 PATCH는 405 |
| GET, POST | `/api/workforce/personal-info-requests/` | 본인 요청 또는 HR 전체 조회 / 본인 요청 생성 |
| GET | `/api/workforce/personal-info-requests/{id}/` | 요청자·HR의 조회 |
| POST | `/api/workforce/personal-info-requests/{id}/approve/` | 대기 요청 승인 |
| POST | `/api/workforce/personal-info-requests/{id}/reject/` | 대기 요청 반려; `reason` 선택 |
| POST | `/api/workforce/personal-info-requests/{id}/cancel/` | 요청자가 본인의 대기 요청 취소 |

본인·상세 응답에는 사번, 이름, 부서·직급 코드와 이름, 생년월일·성별, 재직 상태,
이메일·연락처·내선·주소, 은행 코드·계좌번호, 입퇴사일이 포함된다.
연결된 사원이 없으면 본인 조회는 404다. 상세 조회는 본인 또는 HR만 허용한다.
사원 수정에서 사번 변경과 등록 이후 이메일 직접 변경은 400으로 거절한다.

수정 요청 본문은 바꿀 `phone`, `address`, `email`, `bank_code`, `account_no`를 사용한다.
연락처·주소를 포함해 승인 전에는 현재 정보에 반영하지 않는다. 생략·`null`은 수정하지 않음,
연락처·주소의 빈 문자열은 미등록으로 지움이다. 이메일·은행 코드·계좌번호는 비울 수 없으며,
계좌 변경에는 은행 코드·계좌번호를 함께 보낸다. `previous`·`requested`에도 연락처·주소가 포함된다.
화면은 내 정보의 수정 모드에서 바뀐 항목만 제출한다. workforce 0007을 코드 전환 전에 적용해야 한다.
목록은 `status`, `mine=true`, `processable=true` 필터를 지원한다.
승인은 실제 값을 반영하고 반려·취소는 유지한다. 도메인 오류는 400과 `detail`, 선택 `field`로 반환한다.
보이지 않는 요청은 404, 열람 가능하지만 처리할 수 없는 요청은 403이다.
현재 구현에는 HR 요청자의 특별 처리자 판정·대기 1건 제한·로그인 이메일 동기화가 있다.
이는 확정 제품 정책으로 채택하지 않았으며 HR-03에서 다룬다. 계좌 보호·테이블 차이는 HR-01·HR-02 대상이다.

### 7.1.1 사원 등록·고용 생애주기·인사이력의 현재 API

아래는 FN-HR-006~010의 현재 transport 계약이다. 구체 운영 조건과 남은 일반 CRUD 우회·정본 문제는
[최신 의제 HR-01·HR-03·OPS-01](../../reports/2026-10-14_module-review-agenda.md)에서 구분한다.
모든 경로는 HR 관리자(superuser 포함) 전용이다.

| 메서드 | `/api/workforce/` 상대 경로 | 요청·성공 응답 |
| --- | --- | --- |
| POST | `new-hires/` | 통합 등록, 201 등록 결과 |
| POST | `employees/{emp_no}/terminate/` | `term_date` → 200 사원 상세 |
| GET | `employees/terminated/` | `name`, `emp_no`, `dept_no`, `term_date_from`, `term_date_to` → 200 퇴사일 최신순 배열 |
| POST | `persons/{person_id}/rehire/` | 신규 고용 입력 → 201 새 사번 등록 결과 |
| GET | `employees/{emp_no}/history/` | 200 인사이력 배열, 시작일 최신순 |
| POST | `employees/{emp_no}/history/` | `start_date`, `dept_no`, `position_code`, `base_salary`, 선택 `previous_base_salary`, `reason` → 201 발령 결과 |
| POST | `employees/{emp_no}/history/{history_id}/correct/` | `start_date`, `dept_no`, `position_code`, `base_salary`, 필수 `reason` → 200 정정 결과 |
| POST | `employees/{emp_no}/history/{history_id}/cancel/` | 필수 `reason` → 200 취소 결과 |
| GET | `employees/{emp_no}/history/changes/` | 200 발령·정정·취소 기록 배열, 최신순 |

등록 필수 입력: `name`, `birth_date`, `gender`(M/F), `email`, `hire_date`, `dept_no`,
`position_code`, `base_salary`(0 이상, 소수 2자리). 선택 입력: `phone`, `extension_no`,
`address`, `role_codes[]`, `account: {password}`. 사번 `emp_no` 입력은 400으로 거절한다.
재입사는 `name`·`birth_date`·`gender`가 선택이며 보내면 기존 Person 정보를 갱신한다.
등록 결과는 `emp_no`, `person_id`, `history_id`, `name`, `email`, `dept_no`, `position_code`,
`hire_date`, `tenure_status`, `account`(id/email 또는 null), `roles[]`이며 비밀번호는 응답하지 않는다.
등록·계정·역할·최초 인사이력은 한 트랜잭션으로 처리한다.

현재 구현의 퇴사일은 입사일 이상·오늘 이하이며, 재입사는 모든 이전 고용이 퇴사 상태이고
마지막 퇴사일 이후 새 입사일이어야 한다. 발령은 오늘 이하·부서/직급 변동이어야 하며
기존 진행 이력을 전날로 마감한다. 이력이 없는 사원의 첫 발령은 이전 기간 기본급을 추가로 받는다.
최근 진행 이력만 정정·취소한다. 첫 이력 취소는 거절한다. 정정·취소 사유는 최대 500자다.

이력 항목: `history_id`, `start_date`, `end_date`, `dept_no`, `dept_name`, `position_code`,
`position_name`, `base_salary`. 발령·정정·취소 결과: `history[]`, `released_head_dept_nos[]`,
`restored_head_dept_nos[]`. 변경 기록: `history_id`, `action`(발령/정정/취소), `before`, `after`,
`reason`, `changed_by`, `changed_at`, 해제·복원 부서번호 배열. API 응답에는 DB의 `change_id`를
노출하지 않는다. 삭제한 최근 이력도 기록의 history_id로 추적한다.

DRF 입력 오류는 필드 배열, 업무 오류는 400 `detail`·선택 `field` 형식이다.
일반적으로 없는 사원은 404, 없는 재입사 Person은 현재 구현에서 400이다.
고유 충돌 재시도 소진은 409, 사번 시퀀스 뒤처짐은 500이다. 기존 직접 사번 입력 API와
일반 PATCH의 상태·소속 변경 경로는 여전히 있어 전용 처리와의 정책 통합이 남았다.

### 7.2 게시글 기본 기능

| 메서드 | 경로 | 기존 기능 / 현재 동작 |
| --- | --- | --- |
| GET, POST | `/api/board/posts/` | 목록 / 일반·공지 작성 |
| GET | `/api/board/posts/{id}/` | 상세 조회 |
| PATCH | `/api/board/posts/{id}/` | 작성자 또는 superuser가 제목·내용 수정 |
| DELETE | `/api/board/posts/{id}/` | 작성자·superuser 또는 경영담당자 삭제; 204. 추가 경영담당자 권한은 BD-03 보류 |
| GET | `/api/board/notice-categories/eligible/` | 현재 사원의 작성 가능 분류 `{categories: [...]}` |

작성 입력은 `post_type`(`일반`/`공지`), `title`(최대 100자), `content`다.
일반글은 분류를 가지지 않는다. 공지 입력 `notice_category`는 현재 코드가 전달값의 자격을 검사한다.
분류 범위와 BD-008 자동 부여의 차이는 BD-01 의제로 보류한다.
수정 입력은 `title`, `content`이며 분류 변경은 받지 않는다. 삭제는 `deleted_at`을 기록하고
목록·상세에서 숨기는 현재 구현 방식이다. 삭제 방식은 별도 새 비즈니스 규칙으로 추가하지 않는다.
게시글 응답은 `writer_name`, `comment_count`, `can_edit`, `can_delete`를 포함한다.
권한 필드는 동일한 서버 수정/삭제 검사로 계산하며 프론트는 역할 문자열 대신 이 값을 소비한다.
comment_count는 삭제되지 않은 댓글·답글 수를 조회 시 계산하고 저장 컬럼은 없다.
공지 자격은 MANAGEMENT/HR/PAYROLL의 부분집합이며 빈 배열이면 일반글 작성만 안내한다.
댓글 GET/POST `/api/board/posts/{id}/comments/`, PATCH/DELETE `/api/board/comments/{id}/`는
현재 코드에 있지만 기존 FN-BD 정의에 없는 BD-02 보류 기능이며 정본 기능으로 추가하지 않는다. 권한 오류 403, 없는/삭제된 글 404,
그 밖의 도메인 오류 400과 `code`, `detail`을 사용한다.

### 7.3 평가 기본 기능의 현재 경로

| 메서드 | 경로 | 기존 기능 |
| --- | --- | --- |
| GET, POST | `/api/evaluations/` | 허용 범위 목록 / 평가 작성 |
| GET | `/api/evaluations/targets/?year=YYYY` | 현재 사용자가 새 평가를 작성할 수 있는 최소 대상 목록 |
| GET, PATCH | `/api/evaluations/{id}/` | 상세 / 점수·의견 수정 |
| POST | `/api/evaluations/{id}/confirm/` | HR 확정 |

작성 본문은 `emp_no`, `eval_year`, `score`, 선택 `comments`다. 목록은 `year` 필터를 지원한다.
등급은 서버가 계산하고 대상자는 확정된 본인 평가만 조회한다. 권한 밖 평가는 404로 숨긴다.
현재 코드는 HR 부서장 작성 금지, 제출 후 확정, 생성 연도·조직 기준일 등 추가 제한을 적용한다.
targets의 필수 year는 4자리이며 현재 생성 연도 제한을 적용한다. 응답은 `emp_no`, `name`,
`dept_no`, `pos_code` 배열이다. 지정 평가자·재직·근속 설정에 맞는 대상 중 자기 자신과
이미 해당 연도 평가가 있는 사원을 제외한다. 개인 연락처·계좌를 반환하지 않는다.
2026-10-27 구현은 사원·인사이력·부서·기존 평가 여부를 일괄 조회하도록 개선했다.
팀 크기가 늘어도 질의 수가 증가하지 않는 회귀 테스트(15회 이하)를 둔다. 권한·응답 계약은 같다.
프론트 작성 대상은 이 API, 본인 결과는 평가 목록만 호출한다. HR 전용 사원 목록 의존은
INT-01에서 구현 해결했다. 추가 정책의 전체 준수 판단은 EV-01·EV-02 결정 후 수행한다.
추가 제출·반려·재배정·제외·확정취소·이력 경로를 기존 FN-EV 기능으로 승격하지 않는다.

### 7.4 급여 기본 기능

모든 경로는 `/api/payroll/` 아래에 있다.

| 메서드 | 상대 경로 | 기존 기능 / 현재 입력 |
| --- | --- | --- |
| GET | `components/` | 활성 지급·공제 마스터 조회 |
| GET | `employees/` | 급여담당자 전용 최소 업무 대상 목록 |
| GET | `statements/` | 본인 목록; `emp_no` 또는 `all=true` 관리 조회는 급여담당자 |
| POST | `statements/` | 생성: `emp_no`, `year`, `month`, 선택 `items`, `payment_date` |
| GET | `statements/{id}/` | 본인 또는 급여담당자 상세 |
| PUT | `statements/{id}/items/` | 작성중 항목 교체: `items`, 선택 `payment_date` |
| GET | `statements/{id}/excel/` | 확정 명세서 xlsx, 본인 또는 급여담당자. 작성중은 400 |
| POST | `statements/{id}/confirm/` | 확정 또는 이력에 따른 재확정 |
| POST | `statements/{id}/cancel-confirmation/` | 확정취소: 공백이 아닌 `reason`(최대 255자) |
| GET | `statements/{id}/history/` | 허용 범위 변경 이력 |

employees 응답은 `emp_no`, `name`, `dept_no`, `dept_name`, `position_name`, `is_active` 배열이다.
연락처·계좌를 포함하지 않고 비담당자는 403이다. INT-01의 HR 전체 목록 충돌은 이 경로로 해결했다.
생성 시 지급일 생략은 현재 구현의 자동 산정, 지정 시 입력 날짜를 사용한다. 작성중에만 변경하며
변경을 수정 이력에 기록한다. 정산일 정책의 제품 확정은 PY-02에 남는다.
xlsx는 서버 openpyxl로 생성하며 PDF는 프론트의 브라우저 인쇄 저장이다. PDF API는 없다.

항목은 `component_code`, `amount`(현재 소수 둘째 자리까지, 0 이상)를 사용한다.
항목 수정은 최소 1건, 확정은 항목이 있는 작성중 급여만 허용한다.
응답에는 `statement_id`, `employee_no`, `year`, `month`, `payment_date`, `status`, `items`,
`total_earnings`, `total_deductions`, `net_pay`, `confirmed_by`, `confirmed_at` 및
`employee` 요약(`emp_no`, `name`, `position_name`)이 있다.

현재 코드는 일반 사원에게 확정 건만 공개하고 급여담당자의 본인 처리를 금지한다.
이력의 공통 식별 필드 `history_id`, `statement_id`, `action`, `changed_at`에 더해,
급여담당자는 `actor_employee_no`, `actor_name`, `reason`을 받는다.
이 공개·처리 제한과 지급일은 PY-02에서 검토하며 확정 제품 규칙으로 채택하지 않는다.
PY-009의 최종 올림은 현재 계산과 다르므로 PY-01 해결 전 준수 완료로 표시하지 않는다.

## 8. 구현 기준 파일

- 전체 라우팅: `backend/config/urls.py`
- 인증·계정: `backend/accounts/urls.py`, `backend/accounts/views.py`, `backend/accounts/serializers.py`
- 사원·조직: `backend/workforce/presentation/urls.py`, `views.py`, `serializers.py`
- 휴가: `backend/vacation/presentation/urls.py`, `views.py`, `serializers.py`
- 휴가 응답 DTO와 업무 규칙: `backend/vacation/application/dto.py`, `service.py`

API 구현이 변경되면 이 문서의 기준일, 엔드포인트 표, 요청·응답 예시와 오류 코드를 함께 갱신한다.

Notion에는 2026-10-12 기본 경로·기존 모델 매핑·오래된 설명 정정만 반영했다.
이 저장소 문서의 보류 정책·상세 의제 기록은 Notion 확정 규칙으로 승격하지 않았다.


## 2026-10-29 조회 성능 보완

응답·권한·CSRF·업무 상태 계약은 유지한다. 인증 요청의 재직 검사·본인 프로필·부서장 표시 정보를
요청 안에서 묶어 재사용하고, 공지 분류 자격은 활성 역할을 한 번에 조회한다. 개인정보 목록의
can_process는 요청자·부서장·활성 HR 역할을 일괄 조회해 기존 정책으로 계산한다. 승인·반려 명령은
목록용 판정을 재사용하지 않고 트랜잭션 안에서 최신 조직을 다시 확인한다. 저장소 코드·격리 테스트
결과는 [성능 보완 보고서](../../reports/2026-10-29_database-query-improvements.md)에 기록했다.
Notion 재조회·수정·공유 PostgreSQL 스키마 변경은 수행하지 않았다.


## 2026-10-29 기준 목록 캐시

API 경로·응답 형식·인증·권한 계약은 유지한다. 쿼리 문자열 없는 부서·직급·역할 목록과
휴가 유형 목록의 공통 메타데이터만 Redis/Valkey에 기본 180초 캐시한다. 사원별 휴가 잔여와
재직 확인은 매 요청 조회하고 신청·승인 검증용 유형 단건 조회는 DB를 사용한다.
저장·삭제 커밋 후 목록 세대를 교체한다. 외부 SQL/bulk 수정 또는 캐시 무효화 실패 시
목록 표시는 TTL까지 지연될 수 있다. 캐시 장애는 DB 조회로 대체한다.
[구현·검증 기록](../../reports/2026-10-29_reference-cache.md)을 참고한다.
Notion 원문 조회·갱신, 스키마 변경은 수행하지 않았다.
