# 07. 테이블 설계 결정안

- Notion 원문: <https://app.notion.com/p/3d78eced448d81e99cd6fb0d87399979>
- 원문 최종 수정: 2026-09-11
- 저장소 확인: 2026-09-25

## 목적

확정된 비즈니스 규칙과 기능 명세를 수용할 수 있도록 초기 데이터베이스 중간안을 보완한다.
복수 역할, 재입사, 승인·확정·정정 이력처럼 명세에 존재하는 개념을 관계와 이력 구조로
분리하고, 평가 당시 조직처럼 시점 보존이 필요한 값은 스냅샷으로 유지한다.

## 권장 논리 구조

- 사원·조직·권한: `persons`, `employees`, `departments`, `positions`, `emp_history`,
  `roles`, `employee_roles`, `employee_change_requests`
- 휴가: `leave_types`, `leave_requests`, `leave_request_history`
- 급여: `payroll_items`, `payrolls`, `payroll_details`, `payroll_history`
- 평가: `evaluations`
- 게시판: `board_notice_categories`, `board_posts`

재입사는 기존 `persons`에 새로운 불변 사번의 `employees`를 연결한다. 부서장은 조직 책임으로,
그 밖의 업무 권한은 `roles`와 `employee_roles`의 기간형 배정으로 관리한다. 개인정보 변경,
휴가와 급여의 상태 변경은 현재 상태를 직접 덮어쓰는 대신 요청 또는 이력 테이블에 기록한다.

## 주요 결정

- 사원 이메일과 주요 업무 조합에는 고유 제약을 적용한다.
- 기간형 인사이력은 동일 사원의 기간 중복을 허용하지 않는다.
- 휴가 승인·회수·재신청과 급여 확정·취소·재확정은 상태 전이와 이력으로 보존한다.
- 평가 점수·등급·확정 상태와 평가 당시 부서·직급을 함께 보존한다.
- 게시글은 일반글과 공지를 구분하고 공지 분류 마스터를 별도로 둔다.
- 핵심 업무·이력 FK는 기본적으로 삭제 제한을 적용하고, 선택 관계만 `SET NULL`을 검토한다.

상세 컬럼, 현재 구현 테이블과 공유 개발 DB 대조 결과는
[08. 테이블 명세](./08-table-specification.md)에서 관리한다.
