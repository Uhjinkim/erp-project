classDiagram
direction BT
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

board_posts  -->  board_notice_categories : notice_category_code
board_posts  -->  employees : writer_emp_no:emp_no
departments  -->  departments : parent_dept_no:dept_no
departments  -->  employees : head_emp_no:emp_no
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
leave_requests  -->  employees : approver_no:emp_no
leave_requests  -->  employees : emp_no
leave_requests  -->  leave_types : type_id
payroll_details  -->  payroll_items : item_code
payroll_details  -->  payrolls : payroll_id
payroll_history  -->  employees : actor_emp_no:emp_no
payroll_history  -->  payrolls : payroll_id
payrolls  -->  employees : confirmed_by:emp_no
payrolls  -->  employees : emp_no
