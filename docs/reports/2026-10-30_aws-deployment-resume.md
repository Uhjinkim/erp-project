# AWS 배포 재개 · 2026-10-30

## 확인된 상태

- 사용자가 재개를 요청했다. 작업 브랜치 dev, 원격 dev/main 모두 038ac7e. 기존 미커밋 Valkey
  URL 보완과 10-29 이어하기 메모를 보존했다.
- [지난 dev CI](https://github.com/Uhjinkim/erp-project/actions/runs/40859727943) 성공,
  [main 배포](https://github.com/Uhjinkim/erp-project/actions/runs/40859734247) 실패로 종료.
- EC2 실행 중, 퍼블릭 IP 13.125.22.237 유지. nginx/provider/rootless Docker active, 앱 inactive.
- 실제 컨테이너에서 설정 파일의 Valkey TLS endpoint로 PING 성공. 키·데이터 쓰기 없음.
- Valkey URL 보완의 회귀 9 tests와 deploy Ruff 통과. 기존 Secret 값은 수정하지 않았다.
- 사용자가 기존 Secret DB_PASSWORD는 postgres 관리자용이라고 확인하고 AWS 콘솔에서 수정했다.
  Secret metadata의 AWSCURRENT 변경도 확인했다(값 조회/출력 없음).
- Provider를 재시작해 캐시를 비우고 asm-exec 자식 환경으로만 비밀번호를 전달했다.
  RDS postgres DB에 default_transaction_read_only=on으로 접속을 시도했으나 인증 오류로 실패했다.
- RDS 식별자 erp-postgres, endpoint와 관리자 postgres를 AWS metadata로 재확인했다.
- 개발 DB schema metadata 읽기 시도도 현재 SSH tunnel 연결이 없어 실패했다. 개발 데이터는
  조회·복사하지 않았다. 승인된 schema-only baseline은 아직 확보하지 못했다.

## DB/user 생성 검토안 · 아직 실행하지 않음

대상은 ap-northeast-2 계정 610849077646의 RDS erp-postgres다.
검토 가능한 SQL은 `deploy/aws/create-database.psql`이다.

1. 관리자 인증 성공 후 pg_database/pg_roles를 읽기 전용으로 확인한다.
2. 별도 앱 Secret에 생성한 무작위 비밀번호로 로그인 역할 erp를 만든다.
   SUPERUSER/CREATEDB/CREATEROLE/REPLICATION은 허용하지 않는다.
3. UTF8 신규 DB erp-db를 erp 소유로 생성하고 PUBLIC의 DB 접근과 public schema CREATE를 제한한다.
4. 같은 이름의 DB/role이 있으면 중단한다. 기존 대상의 비밀번호 변경·삭제·덮어쓰기는 하지 않는다.
5. 이 SQL은 DB/role만 준비한다. 업무 테이블은 별도의 승인된 schema-only baseline과
   migration 대응표를 확보·검증한 뒤 적용한다. migrate/fake 일괄 실행은 하지 않는다.
6. 운영 앱에는 앱 Secret만 연결하고 기존 관리자 Secret 읽기는 runtime 역할에서 제거한다.
   GitHub에는 DB 비밀번호/관리자 Secret 권한을 주지 않는다.

DB 생성은 transaction 밖에서 실행되므로 DB 생성 실패 시 새 role만 남을 수 있다.
그 경우 재실행/정리 계획을 검토하며 자동 DROP하지 않는다. 기존 자동 백업의 복구 가능 시각과
대상 환경·쓰기 권한을 확인한 뒤 AGENTS.md에 따라 사용자 승인을 받아 실행한다.
현재는 관리자 인증 실패로 읽기 검사·최종 실행 승인 단계에 도달하지 못했다.

검토용 SQL은 로컬에 이미 설치된 PostgreSQL 18 바이너리와 임시 디렉터리·unix socket만 사용해
검증했다. DB/role 최초 생성, role의 로그인 허용·관리 권한 제외, 기존 DB 재실행 차단이 통과했다.
테스트 서버는 종료하고 임시 디렉터리를 삭제했다. RDS/공유 개발 DB에는 쓰지 않았다.
초기 검증에서 psql의 `\\quit 3`이 기대한 실패 코드를 보장하지 않는 점을 발견하여,
ON_ERROR_STOP과 명시적 예외로 실행을 차단하도록 고친 후 다시 검증했다.

## 미해결 입력

Secret 수정 후에도 인증 실패한다. 사용자가 RDS의 실제 관리자 비밀번호와 Secret 값을 다시
맞추도록 요청했다. 비밀번호 자체는 채팅·보고서·명령 인자에 입력하지 않는다.
업무 스키마 baseline 출처도 필요하다. 테이블 생성 제약을 모델/ERD만 보고 추측하지 않는다.

## 인증 재확인 후 진행

- 사용자가 RDS 비밀번호와 Secret을 다시 맞춘 후 관리자 읽기 전용 접속이 성공했다.
  pg_database/pg_roles 검사에서 erp-db와 erp가 모두 없음을 확인했다.
- 사용자 선택: 팀 개발 DB의 **구조만** 원본으로 사용. 업무 데이터 행은 복사하지 않는다.
- 개발 SSH 터널 실행은 SSH 비밀번호를 요구해 중지했다. 사용자에게 별도 터미널에서
  `./scripts/ssh-tunnel.sh` 실행·직접 인증·유지를 요청했다. 비밀번호를 받거나 기록하지 않는다.
- SQL대로 신규 DB/role 생성과 별도 앱 Secret 저장을 승인받는 질문은 아직 대기 중이다.
  승인 전 RDS 쓰기를 하지 않는다. 스키마 복원은 실제 추출·검증 결과를 준비한 뒤 진행한다.
- EC2에 PostgreSQL client 18만 설치했다. PostgreSQL 서버는 설치/시작하지 않았다.
- dev ba06194 push와 [CI 40982004461](https://github.com/Uhjinkim/erp-project/actions/runs/40982004461)
  backend/frontend 모두 성공. main은 아직 038ac7e이며 재배포하지 않았다.

## 승인 후 DB 준비

- 사용자가 신규 erp-db/erp 생성과 앱 Secret 저장을 명시적으로 승인하고 개발 터널을 열었다.
- 새 Secret `erp/production/database` 생성:
  `arn:aws:secretsmanager:ap-northeast-2:610849077646:secret:erp/production/database-BhSrJ8`.
  무작위 앱 비밀번호는 생성 프로세스에서만 만들고 값은 출력하지 않았다.
- RDS 자동 백업 보존 1일, 변경 전 LatestRestorableTime=2026-10-30T01:01:00Z 확인.
- 최초 SQL은 role 생성 후 DB owner를 지정하는 단계에서 PostgreSQL 18 SET ROLE 조건 때문에
  중단됐다. 새 role을 삭제/재생성하지 않고 부여 속성과 DB 부재를 확인해 생성 작업을 계속했다.
- creator에 INHERIT FALSE/SET TRUE를 일시 부여해 DB·schema 소유권을 설정했다. RDS grantor는
  postgres가 아니라 rdsadmin으로 기록되어 explicit GRANTED BY CURRENT_USER 정리가 해당되지
  않음을 발견했다. 최종 GRANT INHERIT FALSE/SET FALSE로 정리하고 실제 두 플래그 false 확인.
- 앱 Secret으로 erp 사용자의 erp-db 로그인 성공, public table_count=0 확인.
- 보완한 SQL은 격리 PostgreSQL 18의 **비슈퍼유저** CREATEDB/CREATEROLE 조건에서도 검증했다.

## 스키마 추출·staging 준비

- 동일 READ ONLY/REPEATABLE READ snapshot에서 원본 erp_dev.public의 36개 테이블 구조와
  47개 migration 적용 metadata를 추출했다. 업무/계정 데이터 행은 추출하지 않았다.
- emp_history_changes/payroll_public_holidays에는 SELECT 권한이 없어 pg_dump table lock이
  실패했다. 이 두 테이블은 허용된 pg_catalog의 컬럼·identity sequence·constraint·index 정의만
  읽어 DDL을 생성했다. 데이터 조회 권한을 확대하거나 공유 DB 권한을 바꾸지 않았다.
- btree_gist 확장은 별도 생성 구문을 포함했다. 스키마 한정 pg_dump에는 extension 생성이
  포함되지 않는 점과 supplementary FK의 search_path를 로컬 staging에서 검증·보완했다.
- 원본의 모든 저장소 migration은 적용되어 있지만 저장소에 없는 migration 6개도 기록되어 있다.
  미출시 테이블 employee_change_requests/scheduled_employment_changes/
  scheduled_employment_change_events, 컬럼 accounts_users.must_change_password와
  evaluations.snapshot_assignment_source/snapshot_basis_date는 새 빈 복원안에서 제외했다.
- 현재 main용 33개 테이블(모델 32 + django_migrations) SQL을 임시 PostgreSQL에 복원 성공.
  원본/target 컬럼·제약·인덱스·시퀀스 구조 대조 중이다. 삭제됐던 컬럼의 내부 attnum 차이는
  의미적 구조 비교에서 컬럼명으로 정규화한다.
- 파일은 Git 밖 `/private/tmp/erp-baseline-20261030/`에 0600으로 보관한다. dump/실제 DDL은
  저장소에 커밋하지 않는다. 임시 staging은 `/private/tmp/erp-staging-20261030/` unix socket 15435다.
- Source의 기존 NULL 조건과 모델에는 차이가 있으며 복원안은 기존 DB 제약을 유지한다.
  아직 RDS 업무 스키마/seed/migration 기록은 적용하지 않았다. 실제 복원안 검증 후 승인 필요.

- 33개 테이블의 정규화된 컬럼·제약·인덱스·시퀀스 대조에서 차이 없음 확인.
  PostgreSQL minor가 varchar 배열의 text cast를 배열 전체/원소별로 출력하는 동등한 형태는
  좁게 정규화하고 해당 경우와 무관한 CHECK 보존 회귀를 추가했다(배포 tests 10개 통과).
- staging에서 initialize_metadata.py 실행 성공: migration 41, content type 29, permission 116,
  역할 3. 앱 계정·사원 0건 유지, 재실행이 쓰기 전에 거부됨 확인. 기존 code seed 6개만 실행했다.
- 검증 완료된 [스키마 적용 계획](./2026-10-30_schema-restore-plan.md)을 제시했고, 실제 새 erp-db의
  테이블/metadata/기준정보 초기화 승인 및 선택적 최초 관리자 이메일 답변을 기다린다.
- 복원 SQL SHA256=b05407f7d4e97b7bc1106db2cf87f9b3d724190a26f63d7ecddd045bbcae5765,
  manifest SHA256=dc52f188aa0c54bc1e1aa6e925495a3739fb90a9d290989f3be3bcce2fb76eab.

## 스키마/metadata 적용과 계정 준비 완료

- 사용자가 복원안과 metadata/기준정보 초기화를 승인했고 첫 관리자 계정 생성을 요청했다.
  실제 이메일·비밀번호는 보고서/저장소에 기록하지 않는다.
- 앱 소유자로 reviewed SQL을 single transaction에 적용하여 새 erp-db의 테이블 33개 복원 성공.
- 별도 경로에 mount한 metadata 스크립트의 Django project import 경로 문제를 발견해 WORKDIR를
  sys.path에 명시하고, 기존 스키마를 다시 만들지 않고 metadata 단계만 이어서 실행했다.
- 실제 RDS에서 구조 manifest 일치·모든 테이블 빈 상태 확인 후 migration 41개·Django 시스템
  metadata·코드 seed 6개 적용 성공. 단계는 한 transaction으로 처리했다.
- 초기 관리자 1개 생성. 비밀번호는 erp/production/bootstrap-admin Secret에만 보관한다.
  실제 직원 신원을 만들거나 개발 계정을 복사하지 않았다.
- runtime.json의 secret_arn을 앱 전용 database Secret으로 전환했다. EC2 역할에서 기존
  postgres 관리자 Secret 읽기 권한을 제거했다. 첫 계정/세션 검사 후 bootstrap-admin 접근도 제거한다.
