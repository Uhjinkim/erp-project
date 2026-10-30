# erp-db 구조 복원 검토안 · 2026-10-30

> 사용자 승인 후 새 RDS erp-db에 적용을 완료했다. 결과는
> [재개 보고서](./2026-10-30_aws-deployment-resume.md)에 기록한다. 아래 내용은 승인 당시 검토 범위다.

## 대상과 승인 범위

대상: 계정 610849077646, ap-northeast-2 RDS erp-postgres의 새 DB erp-db, 소유자 erp.
DB/role 및 앱 Secret 생성은 사용자 승인으로 완료했다. 이 문서는 **다음 단계인 구조 복원과
앱 metadata/코드 기준정보 초기화**의 검토안이다. 아직 RDS에는 업무 테이블을 만들지 않았다.

## 복원 내용

- 원본: 사용자가 선택한 팀 개발 DB erp_dev.public의 동일한 읽기 전용 snapshot.
- 검증된 SQL: [schema-main.sql](/private/tmp/erp-baseline-20261030/schema-main.sql).
  SHA256: `b05407f7d4e97b7bc1106db2cf87f9b3d724190a26f63d7ecddd045bbcae5765`.
- 원본 36개 테이블 중 현재 main에 필요한 33개(모델 32개 + django_migrations)를 복원한다.
- main에 없는 employee_change_requests, scheduled_employment_changes,
  scheduled_employment_change_events와 accounts_users.must_change_password,
  evaluations.snapshot_assignment_source/snapshot_basis_date는 새 빈 복원안에서 제외했다.
  기존 운영 데이터나 기존 테이블을 삭제하는 작업이 아니다. 개발 DB는 변경하지 않는다.
- btree_gist와 PK/FK/UNIQUE/CHECK/배타 제약·인덱스·identity sequence 정의를 재현한다.
  시퀀스의 실제 사용 카운터나 데이터 행은 복사하지 않는다.
- 원본 데이터 조회 권한이 없는 두 테이블은 허용된 시스템 카탈로그 정의만 사용했다.
- 원본의 NULL 제약을 유지한다. 모델과 차이가 있는 기존 조건을 배포 과정에서 임의로 완화하지 않는다.

## metadata 초기화

[initialize_metadata.py](../../deploy/aws/initialize_metadata.py)는 자동 배포와 분리된 일회성 도구다.

1. erp/erp-db 연결과 33개 대상 테이블의 완전한 빈 상태를 확인한다.
2. 원본에서 검증한 컬럼·제약·인덱스·시퀀스 정의를 실제 target과 대조한다.
3. 원본에도 적용되어 있고 저장소에도 존재하는 41개 migration ID만 기록한다.
   저장소에 없는 원본 migration 6개는 기록하지 않는다. migrate/fake를 일괄 실행하지 않는다.
4. 현재 코드의 여섯 seed migration만 실행한다: workforce 0002/0003,
   payroll 0003/0004/0005, board 0003. 역할 3개, 급여 구성항목 8개, 공지 분류 3개다.
5. Django content type 29개와 permission 116개를 생성한다.
6. 검증·기록·seed는 한 transaction으로 수행한다. 비어 있지 않으면 재실행을 거부한다.

개발 DB의 로그인 계정·사원·급여·평가·신청 데이터는 복사하지 않는다. 휴가 유형·직급·부서·공휴일
같은 별도 업무 기준정보 행도 이 작업에서 복사하지 않는다. 초기 관리자 계정 생성은 별도 사용자
이메일 확인과 요청이 있어야 진행한다.

## 검증·복구

- 격리 PostgreSQL 18에 앱 소유자 권한으로 복원 성공.
- 33개 테이블의 구조를 원본과 대조해 차이 없음. PostgreSQL minor별 varchar 배열 cast의
  동등한 출력 형식과 삭제된 컬럼의 내부 번호 차이만 명시적으로 정규화했다.
- migration 41개와 시스템 metadata/6개 seed 초기화 성공. 계정·사원은 0건을 유지했다.
- 재실행이 쓰기 전에 차단됨을 검증했다. 관련 회귀 10 tests와 Ruff 통과.
- 실제 적용도 앱 계정으로 SQL을 single transaction에 복원한다. 실패하면 해당 transaction은
  rollback한다. 새 빈 erp-db만 대상이며 기존 DB·계정은 바꾸지 않는다.
- RDS 적용 후 동일한 구조 검증과 migration check·health 검사를 수행한다. 앱 runtime의 Secret을
  전용 database Secret으로 바꾸고 관리자 Secret의 runtime 읽기 권한은 제거한다.
- SQL 성공 후 metadata 초기화가 실패하면 앱을 시작하지 않고 원인을 검토한다. 자동 DROP/재생성,
  기존 DB 복원, migration 역실행은 하지 않는다.

이 구조 복원·시스템 metadata/코드 기준정보 초기화는 AGENTS.md에 따른 사용자 승인 후 실행했다.
