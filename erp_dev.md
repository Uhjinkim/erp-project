# ERP 개발 DB 스키마

- 기준 환경: 공유 개발 PostgreSQL (`public` 스키마)
- 최종 확인일: 2026-09-20
- 반영 범위: 기존 ERP 업무 테이블과 Django migration으로 생성된 계정, 권한, 세션,
  관리 로그, 휴가 잔여일수 테이블

> 이 문서는 실제 적용된 migration의 결과를 기준으로 작성한 개발 DB 스냅샷이다.
> `workforce`와 기존 `vacation` 테이블은 state-only migration으로 관리되므로, 배포 전에는
> Django model state와 대상 DB 스키마를 다시 비교해야 한다.

## 적용 결과 요약

- `erp_dev.public`에는 23개 migration 이력이 기록되어 있으며 기본 테이블은 총 29개다.
- 이번 migration에서 새로 생성된 테이블은 Django 계정·권한·관리·세션 테이블 10개와
  `leave_balances`를 합친 11개다.
- 신규 업무 테이블은 `leave_balances` 1개다. `workforce.0001`과 `vacation.0001`은 기존
  업무 테이블을 Django에 등록하는 state-only migration이므로 생성 SQL이 없다.
- `workforce.0002_required_roles`는 테이블을 만들지 않고 기존 `roles` 테이블에 필수 역할
  2개를 생성하는 데이터 migration이다.

## ERD

```mermaid
classDiagram
direction BT
class accounts_users {
   bigint id
   varchar(128) password
   timestamptz last_login
   boolean is_superuser
   varchar(150) first_name
   varchar(150) last_name
   boolean is_staff
   boolean is_active
   timestamptz date_joined
   varchar(254) email
   integer emp_no
}
class accounts_users_groups {
   bigint id
   bigint user_id
   integer group_id
}
class accounts_users_user_permissions {
   bigint id
   bigint user_id
   integer permission_id
}
class auth_group {
   integer id
   varchar(150) name
}
class auth_group_permissions {
   bigint id
   integer group_id
   integer permission_id
}
class auth_permission {
   integer id
   varchar(255) name
   integer content_type_id
   varchar(100) codename
}
class board_notice_categories {
   varchar(50) category_name
   varchar(20) notice_category_code
}
class board_posts {
   integer writer_emp_no
   varchar(10) post_type
   varchar(20) notice_category_code
   varchar(100) title
   text content
   timestamp created_at
   timestamp updated_at
   bigint post_id
}
class departments {
   varchar(100) dept_name
   integer parent_dept_no
   integer head_emp_no
   integer dept_no
}
class django_admin_log {
   integer id
   timestamptz action_time
   text object_id
   varchar(200) object_repr
   smallint action_flag
   text change_message
   integer content_type_id
   bigint user_id
}
class django_content_type {
   integer id
   varchar(100) app_label
   varchar(100) model
}
class django_migrations {
   bigint id
   varchar(255) app
   varchar(255) name
   timestamptz applied
}
class django_session {
   varchar(40) session_key
   text session_data
   timestamptz expire_date
}
class emp_history {
   integer emp_no
   date start_date
   date end_date
   integer dept_no
   varchar(20) position_code
   numeric(15,2) base_salary
   bigint history_id
}
class employee_change_requests {
   integer emp_no
   varchar(30) field_code
   text before_value
   text requested_value
   varchar(20) status
   timestamp requested_at
   integer processed_by
   timestamp processed_at
   varchar(255) reject_reason
   bigint request_id
}
class employee_roles {
   integer emp_no
   varchar(30) role_code
   timestamp assigned_at
   timestamp revoked_at
   bigint employee_role_id
}
class employees {
   bigint person_id
   integer dept_no
   varchar(20) position_code
   varchar(20) tenure_status
   varchar(20) phone
   varchar(100) email
   date hire_date
   date term_date
   varchar(20) ext_no
   varchar(255) address
   varchar(20) bank_code
   varchar(100) account_no
   integer emp_no
}
class evaluations {
   integer emp_no
   varchar(4) eval_year
   integer snapshot_dept_no
   varchar(20) snapshot_pos_code
   integer evaluator_no
   numeric(5,2) score
   varchar(10) grade
   text comments
   varchar(20) eval_status
   integer confirmed_by
   timestamp confirmed_at
   timestamp updated_at
   bigint eval_id
}
class leave_request_history {
   bigint request_id
   varchar(20) from_status
   varchar(20) to_status
   integer actor_emp_no
   varchar(255) reason
   timestamp changed_at
   bigint history_id
}
class leave_balances {
   bigint balance_id
   numeric(5,2) remaining_days
   timestamptz updated_at
   integer emp_no
   varchar(20) type_id
}
class leave_requests {
   integer emp_no
   varchar(20) type_id
   timestamp start_datetime
   timestamp end_datetime
   numeric(3,2) use_days
   varchar(20) status
   integer approver_no
   timestamp approved_at
   varchar(255) reject_reason
   text request_reason
   bigint request_id
}
class leave_types {
   varchar(50) type_name
   boolean is_paid
   numeric(3,2) deduct_days
   varchar(20) type_id
}
class payroll_details {
   bigint payroll_id
   varchar(20) item_code
   numeric(15,2) amount
   bigint detail_id
}
class payroll_history {
   bigint payroll_id
   varchar(20) action
   integer actor_emp_no
   varchar(255) reason
   timestamp changed_at
   bigint history_id
}
class payroll_items {
   varchar(50) item_name
   varchar(10) item_type
   boolean is_active
   varchar(20) item_code
}
class payrolls {
   integer emp_no
   varchar(6) pay_yyyymm
   date pay_date
   numeric(15,2) total_pay
   numeric(15,2) total_deduct
   numeric(15,2) net_pay
   varchar(20) status
   integer confirmed_by
   timestamp confirmed_at
   bigint payroll_id
}
class persons {
   varchar(50) name
   date birth_date
   char gender
   bigint person_id
}
class positions {
   varchar(50) position_name
   integer sort_order
   varchar(20) position_code
}
class roles {
   varchar(50) role_name
   varchar(30) role_code
}

accounts_users  -->  employees : emp_no
accounts_users_groups  -->  accounts_users : user_id:id
accounts_users_groups  -->  auth_group : group_id:id
accounts_users_user_permissions  -->  accounts_users : user_id:id
accounts_users_user_permissions  -->  auth_permission : permission_id:id
auth_group_permissions  -->  auth_group : group_id:id
auth_group_permissions  -->  auth_permission : permission_id:id
auth_permission  -->  django_content_type : content_type_id:id
board_posts  -->  board_notice_categories : notice_category_code
board_posts  -->  employees : writer_emp_no:emp_no
departments  -->  departments : parent_dept_no:dept_no
departments  -->  employees : head_emp_no:emp_no
django_admin_log  -->  accounts_users : user_id:id
django_admin_log  -->  django_content_type : content_type_id:id
emp_history  -->  departments : dept_no
emp_history  -->  employees : emp_no
emp_history  -->  positions : position_code
employee_change_requests  -->  employees : emp_no
employee_change_requests  -->  employees : processed_by:emp_no
employee_roles  -->  employees : emp_no
employee_roles  -->  roles : role_code
employees  -->  departments : dept_no
employees  -->  persons : person_id
employees  -->  positions : position_code
evaluations  -->  departments : snapshot_dept_no:dept_no
evaluations  -->  employees : confirmed_by:emp_no
evaluations  -->  employees : evaluator_no:emp_no
evaluations  -->  employees : emp_no
evaluations  -->  positions : snapshot_pos_code:position_code
leave_request_history  -->  employees : actor_emp_no:emp_no
leave_request_history  -->  leave_requests : request_id
leave_balances  -->  employees : emp_no
leave_balances  -->  leave_types : type_id
leave_requests  -->  employees : approver_no:emp_no
leave_requests  -->  employees : emp_no
leave_requests  -->  leave_types : type_id
payroll_details  -->  payroll_items : item_code
payroll_details  -->  payrolls : payroll_id
payroll_history  -->  employees : actor_emp_no:emp_no
payroll_history  -->  payrolls : payroll_id
payrolls  -->  employees : confirmed_by:emp_no
payrolls  -->  employees : emp_no
```

## Migration 반영 사항

### 계정 및 Django 기반 테이블

- `accounts_users`는 이메일을 로그인 식별자로 사용하며 `email`에 고유 제약이 적용된다.
- `accounts_users.emp_no`는 nullable 고유 FK로, 한 사원에 최대 한 사용자 계정만 연결된다.
- 사용자-그룹, 사용자-권한, 그룹-권한 연결 테이블은 각 FK 조합에 고유 제약을 가진다.
- `auth_permission`은 `(content_type_id, codename)`, `django_content_type`은
  `(app_label, model)` 조합이 고유하다.
- `django_session`과 `django_migrations`는 각각 세션과 migration 적용 이력을 관리한다.

### 휴가 잔여일수

- `leave_balances`는 사원과 휴가 유형별 잔여일수를 저장한다.
- `(emp_no, type_id)` 조합은 고유하며, `remaining_days`에는 0 이상 체크 제약이 적용된다.
- 사원 및 휴가 유형 FK는 Django 모델에서 `RESTRICT`로 정의되어 참조 중 삭제를 차단한다.

### Workforce 권한 데이터

- `workforce.0002_required_roles` 데이터 migration은 `roles`에 다음 역할을 멱등 생성한다.
  - `HR_MANAGER`: 인사 관리자
  - `HR_LEAVE_APPROVER`: 휴가 승인 인사담당자
- 위 역할은 행 데이터이므로 ERD의 별도 테이블로 표현하지 않는다.

### 관리 경계

- `accounts_users`, Django 기반 테이블, `leave_balances`는 스키마 생성 migration으로 관리한다.
- 기존 ERP 업무 테이블은 실제 테이블을 재생성하지 않는 state-only migration으로 Django 모델
  상태만 추적한다.
