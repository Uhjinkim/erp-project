# 08. 테이블 명세

- Notion 원문: <https://app.notion.com/p/3d78eced448d8124b3b4d00cd2c0b5f3>
- 원문 최종 수정: 2026-09-25
- 저장소 확인: 2026-09-25
- 대상: 공유 개발 PostgreSQL `erp_dev.public`의 ERD 29개 테이블
- 기준 자료: [ERP 개발 DB 스키마](../../../erp_dev.md), `backend/accounts`, `backend/workforce`, `backend/vacation` 모델과 마이그레이션
- 용도: ERD의 테이블·컬럼·관계를 구현 관점에서 찾아보기 위한 문서

## 표기와 확인 범위

`PK`는 기본키, `FK`는 참조키, `UK`는 고유키를 뜻한다. `→` 오른쪽은 참조 대상이다. ERD에
표시된 화살표를 FK 관계로 정리했으며, 실제 DB 제약의 존재·이름·삭제 규칙을 모두 검증했다는
뜻은 아니다. 일반 업무 테이블 중 Django 모델이 없는 게시판·평가·급여·변경 요청 테이블의
키와 설명은 ERD의 컬럼명 및 관계를 기준으로 해석했다.

ERD에는 대부분의 컬럼에 대한 NULL 허용 여부, 기본값, CHECK 제약, 인덱스가 없다. 따라서
아래에는 이를 임의로 채우지 않았다. 타입의 `timestamp`는 시간대 정보가 없는 값이고,
`timestamptz`는 시간대 정보가 있는 값이다. 계좌번호·생년월일·연락처 등 개인정보의 실제
값은 이 문서에 포함하지 않는다.

## 테이블 목록

| 영역 | 테이블 | 용도 | 식별 컬럼 |
| --- | --- | --- | --- |
| 계정·Django | `accounts_users` | 로그인 계정 | `id` |
| 계정·Django | `accounts_users_groups` | 계정과 그룹 연결 | `id` |
| 계정·Django | `accounts_users_user_permissions` | 계정과 권한 연결 | `id` |
| 계정·Django | `auth_group` | Django 권한 그룹 | `id` |
| 계정·Django | `auth_group_permissions` | 그룹과 권한 연결 | `id` |
| 계정·Django | `auth_permission` | Django 모델 권한 | `id` |
| 계정·Django | `django_admin_log` | 관리자 작업 기록 | `id` |
| 계정·Django | `django_content_type` | Django 모델 식별 | `id` |
| 계정·Django | `django_migrations` | 마이그레이션 적용 기록 | `id` |
| 계정·Django | `django_session` | 서버 세션 | `session_key` |
| 인사·조직 | `persons` | 사람의 기본 인적사항 | `person_id` |
| 인사·조직 | `employees` | 고용·재직 정보 | `emp_no` |
| 인사·조직 | `departments` | 부서 계층과 부서장 | `dept_no` |
| 인사·조직 | `positions` | 직급 코드 | `position_code` |
| 인사·조직 | `emp_history` | 고용·발령 이력 | `history_id` |
| 인사·조직 | `employee_change_requests` | 사원 정보 변경 요청 | `request_id` |
| 인사·조직 | `roles` | 업무 역할 코드 | `role_code` |
| 인사·조직 | `employee_roles` | 사원별 역할 부여·회수 | `employee_role_id` |
| 휴가 | `leave_types` | 휴가 유형 | `type_id` |
| 휴가 | `leave_balances` | 사원별 유형별 잔여일수 | `balance_id` |
| 휴가 | `leave_requests` | 휴가 신청·승인 | `request_id` |
| 휴가 | `leave_request_history` | 휴가 상태 변경 이력 | `history_id` |
| 게시판 | `board_notice_categories` | 공지 분류 | `notice_category_code` |
| 게시판 | `board_posts` | 일반 글·공지 | `post_id` |
| 평가 | `evaluations` | 사원 평가 | `eval_id` |
| 급여 | `payroll_items` | 급여 항목 코드 | `item_code` |
| 급여 | `payrolls` | 사원별 월 급여 | `payroll_id` |
| 급여 | `payroll_details` | 급여 항목별 금액 | `detail_id` |
| 급여 | `payroll_history` | 급여 작업·정정 이력 | `history_id` |

## 계정·Django

### `accounts_users` — 로그인 계정

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `id` | `bigint` | PK | 계정 ID |
| `password` | `varchar(128)` |  | Django 비밀번호 해시 |
| `last_login` | `timestamptz` |  | 마지막 로그인 시각 |
| `is_superuser` | `boolean` |  | Django 전체 권한 여부 |
| `first_name` | `varchar(150)` |  | 이름 |
| `last_name` | `varchar(150)` |  | 성 |
| `is_staff` | `boolean` |  | Django 관리자 화면 접근 여부 |
| `is_active` | `boolean` |  | 계정 활성 여부 |
| `date_joined` | `timestamptz` |  | 계정 생성 시각 |
| `email` | `varchar(254)` | UK | 로그인 이메일 |
| `emp_no` | `integer` | FK → `employees.emp_no`, UK | 연결된 사번; 계정당 최대 한 명의 사원 |

이메일은 원문 고유 제약 외에 소문자 변환값 고유 제약도 Django 모델에 정의되어 있다.
`emp_no`는 계정 생성 시 선택적으로 연결할 수 있다.

### `accounts_users_groups` — 계정·그룹 연결

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `id` | `bigint` | PK | 연결 ID |
| `user_id` | `bigint` | FK → `accounts_users.id` | 계정 ID |
| `group_id` | `integer` | FK → `auth_group.id` | 그룹 ID |

`(user_id, group_id)` 조합은 고유하다.

### `accounts_users_user_permissions` — 계정별 개별 권한

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `id` | `bigint` | PK | 연결 ID |
| `user_id` | `bigint` | FK → `accounts_users.id` | 계정 ID |
| `permission_id` | `integer` | FK → `auth_permission.id` | 권한 ID |

`(user_id, permission_id)` 조합은 고유하다.

### `auth_group` — Django 권한 그룹

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK | 그룹 ID |
| `name` | `varchar(150)` | UK | 그룹명 |

### `auth_group_permissions` — 그룹별 권한

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `id` | `bigint` | PK | 연결 ID |
| `group_id` | `integer` | FK → `auth_group.id` | 그룹 ID |
| `permission_id` | `integer` | FK → `auth_permission.id` | 권한 ID |

`(group_id, permission_id)` 조합은 고유하다.

### `auth_permission` — Django 모델 권한

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK | 권한 ID |
| `name` | `varchar(255)` |  | 화면 표시 이름 |
| `content_type_id` | `integer` | FK → `django_content_type.id` | 대상 모델 |
| `codename` | `varchar(100)` |  | 권한 코드 |

`(content_type_id, codename)` 조합은 고유하다.

### `django_admin_log` — 관리자 작업 기록

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK | 로그 ID |
| `action_time` | `timestamptz` |  | 작업 시각 |
| `object_id` | `text` |  | 대상 객체의 키 문자열 |
| `object_repr` | `varchar(200)` |  | 대상 객체의 표시 문자열 |
| `action_flag` | `smallint` |  | 생성·수정·삭제 동작 코드 |
| `change_message` | `text` |  | 변경 내용 |
| `content_type_id` | `integer` | FK → `django_content_type.id` | 대상 모델 |
| `user_id` | `bigint` | FK → `accounts_users.id` | 작업 계정 |

### `django_content_type` — Django 모델 식별

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `id` | `integer` | PK | 모델 유형 ID |
| `app_label` | `varchar(100)` |  | Django 앱 이름 |
| `model` | `varchar(100)` |  | 모델 이름 |

`(app_label, model)` 조합은 고유하다.

### `django_migrations` — 마이그레이션 적용 기록

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `id` | `bigint` | PK | 적용 기록 ID |
| `app` | `varchar(255)` |  | Django 앱 이름 |
| `name` | `varchar(255)` |  | 마이그레이션 이름 |
| `applied` | `timestamptz` |  | 적용 시각 |

### `django_session` — 서버 세션

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `session_key` | `varchar(40)` | PK | 세션 식별자 |
| `session_data` | `text` |  | 인코딩된 세션 데이터 |
| `expire_date` | `timestamptz` |  | 만료 시각 |

## 인사·조직

### `persons` — 사람의 기본 인적사항

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `person_id` | `bigint` | PK | 사람 ID; 재입사 시 기존 사람을 재사용할 수 있음 |
| `name` | `varchar(50)` |  | 성명 |
| `birth_date` | `date` |  | 생년월일 |
| `gender` | `char(1)` |  | 성별 코드 |

### `employees` — 고용·재직 정보

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `emp_no` | `integer` | PK | 변경하지 않는 사번 |
| `person_id` | `bigint` | FK → `persons.person_id` | 인적사항 ID |
| `dept_no` | `integer` | FK → `departments.dept_no` | 현재 소속 부서 |
| `position_code` | `varchar(20)` | FK → `positions.position_code` | 현재 직급 |
| `tenure_status` | `varchar(20)` |  | 재직 상태: `재직`, `휴직`, `퇴사` |
| `phone` | `varchar(20)` |  | 연락처 |
| `email` | `varchar(100)` | UK | 사원 업무 이메일 |
| `hire_date` | `date` |  | 입사일 |
| `term_date` | `date` |  | 퇴사일 |
| `ext_no` | `varchar(20)` |  | 내선번호 |
| `address` | `varchar(255)` |  | 주소 |
| `bank_code` | `varchar(20)` |  | 급여 은행 코드 |
| `account_no` | `varchar(100)` |  | 급여 계좌번호 |

`persons`와 `employees`는 1:N 관계여서 재입사 시 새 사번으로 고용 기록을 만들 수 있다.

### `departments` — 부서 계층

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `dept_no` | `integer` | PK | 부서번호 |
| `dept_name` | `varchar(100)` |  | 부서명 |
| `parent_dept_no` | `integer` | FK → `departments.dept_no` | 상위 부서번호 |
| `head_emp_no` | `integer` | FK → `employees.emp_no` | 부서장 사번 |

부서장과 사원 소속은 서로 참조한다. 현재 API는 재직 중이고 해당 부서에 소속된 사원만
부서장으로 지정하도록 검증한다.

### `positions` — 직급 코드

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `position_code` | `varchar(20)` | PK | 직급 코드 |
| `position_name` | `varchar(50)` |  | 직급명 |
| `sort_order` | `integer` |  | 표시 순서 |

### `emp_history` — 인사 이력

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `history_id` | `bigint` | PK | 이력 ID |
| `emp_no` | `integer` | FK → `employees.emp_no` | 대상 사번 |
| `start_date` | `date` |  | 해당 부서·직급의 시작일 |
| `end_date` | `date` |  | 종료일 |
| `dept_no` | `integer` | FK → `departments.dept_no` | 당시 부서 |
| `position_code` | `varchar(20)` | FK → `positions.position_code` | 당시 직급 |
| `base_salary` | `numeric(15,2)` |  | 당시 기본급 |

### `employee_change_requests` — 사원 정보 변경 요청

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `request_id` | `bigint` | PK | 요청 ID |
| `emp_no` | `integer` | FK → `employees.emp_no` | 요청 사원 |
| `field_code` | `varchar(30)` |  | 변경 대상 필드 코드 |
| `before_value` | `text` |  | 변경 전 값 |
| `requested_value` | `text` |  | 요청한 값 |
| `status` | `varchar(20)` |  | 처리 상태: `대기`, `승인`, `반려`, `취소` |
| `requested_at` | `timestamp` |  | 요청 시각 |
| `processed_by` | `integer` | FK → `employees.emp_no` | 처리 사번 |
| `processed_at` | `timestamp` |  | 처리 시각 |
| `reject_reason` | `varchar(255)` |  | 반려 사유 |

### `roles` — 업무 역할 코드

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `role_code` | `varchar(30)` | PK | 업무 역할 코드 |
| `role_name` | `varchar(50)` |  | 역할명 |

`HR_MANAGER`와 `HR_LEAVE_APPROVER`는 `workforce.0002_required_roles`에서 보장하는
초기 역할이다. 역할은 Django `auth_group`과 별도의 업무 권한 체계다.

### `employee_roles` — 사원 역할 부여·회수

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `employee_role_id` | `bigint` | PK | 역할 배정 ID |
| `emp_no` | `integer` | FK → `employees.emp_no` | 역할 보유 사번 |
| `role_code` | `varchar(30)` | FK → `roles.role_code` | 역할 코드 |
| `assigned_at` | `timestamp` |  | 부여 시각 |
| `revoked_at` | `timestamp` |  | 회수 시각 |

활성 역할은 `assigned_at`이 현재 이전이고 `revoked_at`이 없거나 현재 이후인 배정이다.
한 사원에게 여러 역할을 부여할 수 있다.

## 휴가

### `leave_types` — 휴가 유형

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `type_id` | `varchar(20)` | PK | 휴가 유형 코드 |
| `type_name` | `varchar(50)` | UK | 휴가 유형명 |
| `is_paid` | `boolean` |  | 유급 여부 |
| `deduct_days` | `numeric(3,2)` |  | 잔여일수 차감 단위 |

### `leave_balances` — 사원별 휴가 잔여일수

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `balance_id` | `bigint` | PK | 잔여일수 행 ID |
| `emp_no` | `integer` | FK → `employees.emp_no` | 대상 사번 |
| `type_id` | `varchar(20)` | FK → `leave_types.type_id` | 휴가 유형 |
| `remaining_days` | `numeric(5,2)` |  | 남은 일수 |
| `updated_at` | `timestamptz` |  | 마지막 변경 시각 |

`(emp_no, type_id)` 조합은 고유하며 `remaining_days >= 0` CHECK가 Django
마이그레이션에 정의되어 있다.

### `leave_requests` — 휴가 신청

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `request_id` | `bigint` | PK | 신청 ID |
| `emp_no` | `integer` | FK → `employees.emp_no` | 신청 사번 |
| `type_id` | `varchar(20)` | FK → `leave_types.type_id` | 신청 휴가 유형 |
| `start_datetime` | `timestamp` |  | 휴가 시작 일시 |
| `end_datetime` | `timestamp` |  | 휴가 종료 일시 |
| `use_days` | `numeric(3,2)` |  | 사용 일수 |
| `status` | `varchar(20)` |  | 신청 상태 |
| `approver_no` | `integer` | FK → `employees.emp_no` | 승인 담당 사번 |
| `approved_at` | `timestamp` |  | 승인 시각 |
| `reject_reason` | `varchar(255)` |  | 반려 사유 |
| `request_reason` | `text` |  | 신청 사유 |

애플리케이션의 상태값은 `대기`, `승인`, `반려`, `취소`, `회수`다.
`use_days > 0`, `end_datetime >= start_datetime`는 Django 모델에 정의된 조건이다.
기존 테이블의 실제 CHECK 적용 여부는 별도로 확인해야 한다.

### `leave_request_history` — 휴가 상태 변경 이력

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `history_id` | `bigint` | PK | 이력 ID |
| `request_id` | `bigint` | FK → `leave_requests.request_id` | 대상 신청 |
| `from_status` | `varchar(20)` |  | 변경 전 상태 |
| `to_status` | `varchar(20)` |  | 변경 후 상태 |
| `actor_emp_no` | `integer` | FK → `employees.emp_no` | 변경 수행 사번 |
| `reason` | `varchar(255)` |  | 변경 사유 |
| `changed_at` | `timestamp` |  | 변경 시각 |

## 게시판

### `board_notice_categories` — 공지 분류

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `notice_category_code` | `varchar(20)` | 식별 컬럼 | 공지 분류 코드 |
| `category_name` | `varchar(50)` |  | 공지 분류명 |

### `board_posts` — 일반 글·공지

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `post_id` | `bigint` | 식별 컬럼 | 게시글 ID |
| `writer_emp_no` | `integer` | FK → `employees.emp_no` | 작성 사번 |
| `post_type` | `varchar(10)` |  | 일반 글·공지 구분 |
| `notice_category_code` | `varchar(20)` | FK → `board_notice_categories.notice_category_code` | 공지 분류 |
| `title` | `varchar(100)` |  | 제목 |
| `content` | `text` |  | 본문 |
| `created_at` | `timestamp` |  | 작성 시각 |
| `updated_at` | `timestamp` |  | 수정 시각 |

## 평가

### `evaluations` — 사원 평가

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `eval_id` | `bigint` | 식별 컬럼 | 평가 ID |
| `emp_no` | `integer` | FK → `employees.emp_no` | 평가 대상 사번 |
| `eval_year` | `varchar(4)` |  | 평가 연도 |
| `snapshot_dept_no` | `integer` | FK → `departments.dept_no` | 평가 당시 부서 |
| `snapshot_pos_code` | `varchar(20)` | FK → `positions.position_code` | 평가 당시 직급 |
| `evaluator_no` | `integer` | FK → `employees.emp_no` | 평가자 사번 |
| `score` | `numeric(5,2)` |  | 평가 점수 |
| `grade` | `varchar(10)` |  | 평가 등급 |
| `comments` | `text` |  | 평가 의견 |
| `eval_status` | `varchar(20)` |  | 평가 상태 |
| `confirmed_by` | `integer` | FK → `employees.emp_no` | 확정 처리 사번 |
| `confirmed_at` | `timestamp` |  | 확정 시각 |
| `updated_at` | `timestamp` |  | 마지막 수정 시각 |

평가 상태는 제품 명세상 `작성중 → 확정` 흐름을 갖는다.

## 급여

### `payroll_items` — 급여 항목 코드

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `item_code` | `varchar(20)` | 식별 컬럼 | 급여 항목 코드 |
| `item_name` | `varchar(50)` |  | 항목명 |
| `item_type` | `varchar(10)` |  | 지급·공제 구분 |
| `is_active` | `boolean` |  | 항목 사용 여부 |

### `payrolls` — 월별 급여

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `payroll_id` | `bigint` | 식별 컬럼 | 급여 ID |
| `emp_no` | `integer` | FK → `employees.emp_no` | 지급 대상 사번 |
| `pay_yyyymm` | `varchar(6)` |  | 급여 대상 연월 `YYYYMM` |
| `pay_date` | `date` |  | 지급일 |
| `total_pay` | `numeric(15,2)` |  | 지급 합계 |
| `total_deduct` | `numeric(15,2)` |  | 공제 합계 |
| `net_pay` | `numeric(15,2)` |  | 실지급액 |
| `status` | `varchar(20)` |  | 급여 처리 상태 |
| `confirmed_by` | `integer` | FK → `employees.emp_no` | 확정 처리 사번 |
| `confirmed_at` | `timestamp` |  | 확정 시각 |

### `payroll_details` — 급여 항목별 금액

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `detail_id` | `bigint` | 식별 컬럼 | 상세 ID |
| `payroll_id` | `bigint` | FK → `payrolls.payroll_id` | 급여 ID |
| `item_code` | `varchar(20)` | FK → `payroll_items.item_code` | 급여 항목 |
| `amount` | `numeric(15,2)` |  | 항목 금액 |

### `payroll_history` — 급여 작업·정정 이력

| 컬럼 | 타입 | 키·참조 | 설명 |
| --- | --- | --- | --- |
| `history_id` | `bigint` | 식별 컬럼 | 이력 ID |
| `payroll_id` | `bigint` | FK → `payrolls.payroll_id` | 대상 급여 |
| `action` | `varchar(20)` |  | 수행한 작업 |
| `actor_emp_no` | `integer` | FK → `employees.emp_no` | 작업 사번 |
| `reason` | `varchar(255)` |  | 작업·정정 사유 |
| `changed_at` | `timestamp` |  | 작업 시각 |

## 스키마 대조 시 주의할 점

- `workforce.0001_initial`과 `vacation.0001_initial`은 기존 업무 테이블에 대한
  **state-only** 마이그레이션이다. 이 모델의 NULL·CHECK·FK 선언만으로 공유 DB에 실제
  제약이 생성되었다고 판단하면 안 된다.
- 2026-09-22의 계정 생성 작업에서 읽기 전용 확인한 실제 개발 DB는
  `persons.birth_date`, `employees.dept_no`, `employees.position_code`가 `NOT NULL`이었다.
  현재 Django 모델의 nullable 선언과 차이가 있다. 이 문서는 컬럼 타입·관계를 ERD 기준으로
  적었으며 해당 차이를 숨기지 않는다.
- 게시판·평가·급여·변경 요청 테이블은 현재 저장소에 대응 Django 모델 또는 생성
  마이그레이션이 없다. 위의 `식별 컬럼` 표기는 이름에 따른 해석이며 실제 PK·UK·FK와
  NULL 허용 여부는 대상 DB의 `pg_constraint`와 `information_schema`로 재확인해야 한다.
- `accounts_users.password`는 평문이 아니라 Django 해시를 저장한다. `account_no`와
  사원 변경 요청의 전후 값은 민감정보를 담을 수 있으므로 조회·내보내기에 주의한다.

업무 규칙의 원문은 Notion이며, 저장소의 [Notion 명세 스냅샷](./README.md)은
구현 추적용이다. 이 문서는 그 제품 규칙을 새로 확정하지 않는다.
