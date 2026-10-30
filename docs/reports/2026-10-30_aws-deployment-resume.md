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
