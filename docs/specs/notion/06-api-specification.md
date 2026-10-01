# 06. API 명세

- Notion 원문: <https://app.notion.com/p/3e58eced448d81f4ade6c86fc337bd26>
- 원문 최종 수정: 2026-09-25
- 저장소 확인: 2026-09-25
- 기준 구현: Django REST Framework 백엔드의 현재 라우트, 뷰, 직렬화 코드
- 개발 직접 호출 기본 URL: `http://localhost:8000`
- nginx 통합 개발환경 기본 URL: `http://localhost:8080`

이 문서는 현재 저장소에 구현된 API의 동작을 코드 기준으로 정리한 명세다. 별도 OpenAPI 또는
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
| `GET` | `/api/workforce/employees/` | 인증 사용자 | 사원 목록 조회와 검색 |
| `POST` | `/api/workforce/employees/` | HR 관리자 | 사원 생성 |
| `GET` | `/api/workforce/employees/{emp_no}/` | 인증 사용자 | 사원 상세 조회 |
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
| `reason` | 문자열 또는 `null` | 선택, 빈 문자열은 `null`로 처리 |

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
2. 사용할 부서장이 없으면 활성 `HR_LEAVE_APPROVER`가 정확히 한 명일 때 그 사원을 사용한다.
3. 승인자를 결정할 수 없으면 신청을 거절한다.

잔여일수 정보가 존재하고 신청일수가 잔여일수를 초과하면 신청할 수 없다. 잔여일수 정보 자체가
없으면 현재 구현은 초과 검사를 생략한다.

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

이력은 변경 일시와 이력 ID 오름차순이다. 신청자, 해당 신청의 승인자, HR 관리자만 조회할 수
있다.

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

## 7. 구현 기준 파일

- 전체 라우팅: `backend/config/urls.py`
- 인증·계정: `backend/accounts/urls.py`, `backend/accounts/views.py`, `backend/accounts/serializers.py`
- 사원·조직: `backend/workforce/presentation/urls.py`, `views.py`, `serializers.py`
- 휴가: `backend/vacation/presentation/urls.py`, `views.py`, `serializers.py`
- 휴가 응답 DTO와 업무 규칙: `backend/vacation/application/dto.py`, `service.py`

API 구현이 변경되면 이 문서의 기준일, 엔드포인트 표, 요청·응답 예시와 오류 코드를 함께 갱신한다.
