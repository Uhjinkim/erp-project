# main CI/CD · AWS 배포 실측

일자: 2026-10-29. 사용자 요청: 로컬 변경을 dev에 반영하고 main으로 통합·배포,
GitHub Actions CI/CD, 기존 서울 EC2/RDS/Valkey/Secret, 퍼블릭 IP Let’s Encrypt HTTPS.

## 구현과 인프라

- main만 OIDC 배포하는 CI/CD workflow, ARM64 ECR 이미지, S3 checksum bundle, 제한된 SSM document.
- memory-only Secret 주입, rootless Compose, 환경변수 allowlist, TLS RDS/Valkey, read-only schema preflight.
- 실패 rollback·archive 경로 검사·동적 참조 단일 치환·Secret 없이 stop하는 회귀 테스트.
- ECR 2개·비공개 암호화/versioning S3·OIDC·runtime/deploy IAM 역할·SSM document 생성.
- 기존 EC2에 runtime instance profile 연결. HTTP-01용 80만 추가 개방. 기존 443/SSH 규칙 유지.
- Ubuntu 26.04 ARM64, 기존 rootless Docker 정상. SSM Agent 재시작 후 AWS에서 Online 실측.
- nginx/AWS CLI/Certbot/Workload Credentials Provider 설치. Provider 바이너리 SHA256 검증.
- IP staging·정식 인증서 발급, 갱신 timer·nginx reload hook. 외부 인증서 검증=0, HTTP 301 확인.
- 기존 Secret의 DB_PASSWORD/REDIS_URL 유지. 짧은 Django 키 대신 별도 생성 Secret 사용.
- DB erp-db / 사용자 erp는 사용자 확인. DB_NAME/DB_USER가 Secret에 없어 비밀 없는 호스트 설정 사용.

## 검증

- 기존 전체 변경: backend check/Ruff/pytest 561 passed/migration drift 없음, frontend lint/69 tests/build 통과.
- 배포 회귀 8 tests 통과, deploy Python Ruff 통과, workflow actionlint 통과, shell syntax 통과.
- dummy 환경변수로 AWS Compose config --quiet 통과. 로컬 Docker daemon은 꺼져 있어 새 이미지
  로컬 실행은 하지 않았으며 GitHub ARM64 빌드와 EC2에서 검증한다.
- 개발 start-dev --check는 sandbox의 sysctl 제한 때문에 일반 실행이 실패했으나 허용된 실행에서 통과.
- Secret 값·SSH key·계좌/사원 데이터는 출력하지 않았다. 자격증명 패턴 diff 검사에서 발견 없음.

## 진행 중

Git dev/main 반영, GitHub CI/CD 실제 실행 결과, RDS 연결·schema readiness와 공개 앱 health 결과를
마지막 검증 후 여기에 추가한다. DB migration·schema/data 쓰기·seed는 아직 실행하지 않았다.

## 첫 실행 확인

- 로컬 변경을 dev `ae06cc1`로 commit/push하고 main `f1641be`로 이력 보존 merge/push했다.
- [dev CI](https://github.com/Uhjinkim/erp-project/actions/runs/40857591114) 성공.
- [첫 main 실행](https://github.com/Uhjinkim/erp-project/actions/runs/40857740358)의 backend/frontend 성공.
  OIDC subject가 기존 name-only 예제와 달리 immutable ID를 포함해 역할 인수가 실패했다.
  CloudTrail WebIdentityUser principal에서 실제 subject를 확인하고 정확한 owner/repo ID와 main으로
  trust를 수정했다. wildcard나 다른 branch 허용으로 우회하지 않았다.
- Secret provider 캐시 갱신 시 DescribeSecret AccessDenied를 발견해 지정한 두 Secret 범위에서
  권한을 추가했다. 원문 없는 wrapper 진단·로컬 provider 전용 모드를 보완하고 환경 검사 통과.
- 정식 IP 인증서의 `renew --dry-run --run-deploy-hooks` 성공. nginx 검사/reload hook도 실행됐다.
- 임시 ECR DOCKER_CONFIG가 rootless context 선택을 지우는 경우를 확인하고 socket을 명시했다.
  이 환경변수 조합에 대한 회귀 테스트를 추가했다. Provider token 0600/부모 0700과
  root 소유 launcher/비밀 없는 설정 파일 권한을 확인하고 staging 인증서는 정리했다.
- OIDC 수정 후 ECR 이미지 두 개 build/push와 S3/SSM 전달까지 성공. 첫 컨테이너 검사에서
  rootlesskit `/etc` copy-up 때문에 새 CA bind source가 안 보여 사용자 home으로 옮겼다.
- 수정 후 실제 컨테이너의 production `check --deploy --fail-level WARNING` 통과.
  RDS까지 TCP/TLS 연결은 도달했지만 `erp` 계정의 password authentication 실패.
  계정 존재·Secret 비밀번호의 계정 대응을 사용자에게 확인 요청했다. DB 쓰기는 수행하지 않았다.
