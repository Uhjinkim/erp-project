# AWS 배포 이어하기 메모

> 2026-10-30 사용자가 재개했다. 최신 상태는
> [재개 보고서](./2026-10-30_aws-deployment-resume.md)를 우선 확인한다.

사용자가 2026-10-29에 “작업 내용 기억하고 나중에 이어서”라고 요청하여 작업을 중단했다.
사용자의 재개 요청 전에는 추가 배포·DB 작업을 진행하지 않는다. 재개 시 이 문서와
`docs/guides/aws-main-cicd.md`, `docs/reports/2026-10-29_main-cicd-deployment.md`를 먼저 읽는다.

## 확정된 사용자 요청

- 기존 ap-northeast-2 EC2/RDS/Valkey/Secrets Manager를 사용한다.
- 로컬 기존 변경 전체를 dev에 올린 뒤 main으로 통합하고 main 소스로 배포한다.
- main GitHub Actions CI/CD도 구축한다. Docker rootless + nginx/backend 구조를 유지한다.
- Cloudflare 웹 Tunnel 대신 퍼블릭 IP `https://13.125.22.237`와 Let’s Encrypt 인증서를 사용한다.
- DB 이름 `erp-db`, 업무 사용자 `erp`. 사용자가 **DB와 erp 계정을 아직 만들지 않았다고 확인**했다.

## 저장소 상태

- 기존 약 175개 파일 변경을 포함해 dev `ae06cc1`로 commit/push했고 main `f1641be`로 merge했다.
- 후속 `cbd2b9b`(provider/OIDC), `bc5430e`(rootless socket), `038ac7e`(CA 경로/preflight)를
  dev/main 양쪽에 push했다. 마지막 원격 소스는 `038ac7eb427ff7be4080b96ad34f9a6d3626526d`다.
- 현재 체크아웃은 dev. 중단 직전 Valkey URL 우선순위 수정·회귀 테스트·가이드 변경은 로컬에만 있다.
  이 메모와 함께 보존한다. main에 새 push를 하면 자동 배포가 실행되므로 재개 전 push하지 않는다.
- 로컬 변경의 목적: 기존 Secret REDIS_URL이 literal placeholder라 DNS 실패. 실제 비밀번호 없는
  private Valkey endpoint를 runtime.json에서 우선 사용한다. 인증 URL이 필요한 경우 config의
  redis_url을 null로 두어 Secret URL을 사용하게 한다. Secret 원래 값은 수정하지 않았다.

## 실제 완료한 인프라

- 계정 610849077646, 서울. EC2 erp-server `i-0a4ecf2b587053b08`, Ubuntu 26.04.1 ARM64,
  t4g.small. 기존 erp 사용자 UID 1002의 rootless Docker 확인, linger 켜짐.
- ECR `erp/backend`, `erp/nginx`: immutable SHA tags, scan-on-push. 이미지 build/push 실측 성공.
- 비공개 S3 `erp-releases-610849077646-ap-northeast-2`: encryption/versioning/public-block 설정.
- GitHub OIDC provider와 `erp-github-deploy`, `erp-ec2-runtime` 역할 생성. EC2 profile 연결.
- OIDC 실제 subject는 name-only가 아닌
  `repo:Uhjinkim@13661028/erp-project@1363960456:ref:refs/heads/main`이다.
  CloudTrail에서 확인하여 trust를 정확히 수정했다. main 외 접근 허용 없음.
- EC2 역할은 지정 Secret 2개 GetSecretValue/DescribeSecret, ECR pull, S3 release prefix 읽기,
  SSM Core. GitHub 역할은 ECR push/S3 prefix 쓰기/지정 EC2·document SendCommand/결과 조회.
- SSM document `ERP-DeployRelease`: SHA40/checksum64 정규식, erp 사용자로 rootless 배포.
  SSM Agent가 실제 AWS에서 Online. SSM 전달·EC2 컨테이너 pull까지 실측.
- nginx/AWS CLI/Certbot 5.8/AWS Workload Credentials Provider 3.1.1 설치.
  Provider ARM64 공식 SHA256 검증. `erp-secrets.service`, SSRF token 0600/부모 0700.
- `/usr/local/lib/erp/asm_exec.py`, `/usr/local/bin/erp-release`는 root 소유.
  `/etc/erp/runtime.json`은 비밀 없는 설정. user `erp.service`와 rootless socket 설정 설치.
- rootlesskit의 /etc copy-up 때문에 CA는 `/home/erp/.config/erp/rds-global-bundle.pem`에 둔다.
- 80 ingress 추가, 기존 443/SSH 규칙 유지. 8000/8080 공개 안 함.
- IP staging→정식 인증서 발급 성공. `snap.certbot.renew.timer` active, nginx reload hook 설치.
  `renew --dry-run --run-deploy-hooks` 성공. staging 인증서는 정리했다.
- 외부 인증서 검증 성공(ssl_verify_result=0), HTTP 301→HTTPS 확인.
  **앱 기동은 미완료이므로 공개 주소는 502일 수 있다.**

## 비밀과 DB 상황: 재개 시 가장 먼저 확인

- 기존 Secret ARN:
  `arn:aws:secretsmanager:ap-northeast-2:610849077646:secret:SecretManager-StO81K`.
  DB_PASSWORD, 짧은 DJANGO_SECRET_KEY, placeholder REDIS_URL이 존재했다. 값은 출력하지 않았다.
- 별도 생성 Django 키 Secret:
  `arn:aws:secretsmanager:ap-northeast-2:610849077646:secret:erp/production/django-uPFC79`.
  무작위 키는 생성 프로세스에서만 만들고 값은 표시하지 않았다. 기존 Secret 값은 변경하지 않았다.
- 모든 비밀 조회는 asm-exec 동적 참조로 자식 환경에만 전달한다. get-secret-value 또는
  provider secret endpoint를 직접 호출해 원문을 출력하지 않는다. credential 파일도 출력하지 않는다.
- RDS `erp-postgres`, 실제 관리자 username은 **postgres**. Endpoint는 runtime.json.example 참조.
  RDS는 private/encrypted, EC2 SG의 5432만 허용. TLS 도달은 확인했다.
- 운영 컨테이너 `check --deploy --fail-level WARNING` 통과. DB 접속은 erp 사용자 인증 실패.
  사용자가 erp 계정/DB를 만들지 않았음을 확인했으므로 예상된 상태다.
- **마지막 질문에 아직 답이 없다:** “기존 SecretManager의 DB_PASSWORD가 실제 postgres 관리자
  비밀번호인가, 아니면 별도 관리자 Secret을 준비할 것인가?” 사용자에게 비밀번호를 채팅으로
  보내라고 하지 말고 Secret ARN 또는 콘솔에서 입력하도록 안내한다.
- DB/user/schema/migration/data 쓰기는 **전혀 실행하지 않았다**. 계정/비밀번호를 추측하지 않는다.
- 다음 단계는 관리자 credential 경로 확인 → 읽기 전용 DB 상태 확인 → 검토 가능한 생성/복원 계획
  준비 → 대상/권한/복구 지점 확인과 사용자 승인 후 DB 쓰기다.
- 여러 초기 migration이 state-only다. 빈 RDS에 migrate부터 실행하거나 일괄 fake하지 않는다.
  기존 승인된 schema-only baseline/실제 제약·migration 대응표·승인된 기준정보가 필요하다.
  관련 절차는 기존 `docs/guides/ec2-rds-deployment.md`의 빈 RDS 절을 읽는다.
  개발 사원·계정·급여·평가 데이터는 복사하지 않는다. bootstrap SQL은 아직 작성/실행하지 않았다.

## CI/CD 실행과 검증

- `.github/workflows/ci-cd.yml`: dev/PR은 CI, main은 CI→ARM64 build/ECR→S3→SSM→내부/공개 health.
  문서만 바뀐 push는 생략. GitHub OIDC와 EC2 role을 쓰며 GitHub Secret 등록 불필요.
- backend check/Ruff/561 pytest/migration drift 검사 통과. frontend lint/69 tests/build 통과.
- 배포 regression은 중단 직전 **9 tests 통과**, deploy Ruff/actionlint/shell syntax/Compose config 통과.
- 실제 [첫 dev CI](https://github.com/Uhjinkim/erp-project/actions/runs/40857591114) 성공.
- [첫 main](https://github.com/Uhjinkim/erp-project/actions/runs/40857740358): CI 성공, OIDC subject 불일치 실패.
- [OIDC 수정 후 main](https://github.com/Uhjinkim/erp-project/actions/runs/40858769642): CI·이미지·SSM 전달 성공,
  /etc CA bind 실패. CA home 경로로 수정.
- [socket 수정 main](https://github.com/Uhjinkim/erp-project/actions/runs/40859213678): CI 성공, 배포 실패.
- 마지막 main 실행 [40859734247](https://github.com/Uhjinkim/erp-project/actions/runs/40859734247),
  dev [40859727943](https://github.com/Uhjinkim/erp-project/actions/runs/40859727943).
  중단 시 아직 실행 중이었다. 기존 자동 실행은 credential/placeholder preflight에서 실패할 것으로
  예상되지만 재개 시 실제 상태를 조회한다. 새 실행은 시작하지 않는다.
- GitHub CLI 로그인은 ddrk42로 이 repo read-only. API 읽기는 gh 가능하지만 설정/취소 등 쓰기는
  이 토큰으로 불가하다. GitHub connector는 Uhjinkim. Git push는 origin의 github-primary SSH 사용.
- SSH host key는 AWS GetConsoleOutput 지문과 대조했다.
  ED25519 `SHA256:6v4BlBq1Sx5wv+SjOdvgtjMcgDxO8R8yq5po2FgibSM`.
  SSH key는 `/Users/home/.ssh/erp-pair.pem`(내용 조회 금지), verified known_hosts 임시 경로는
  `/private/tmp/erp-known-hosts`. 키 파일이나 비밀을 repo/대화에 복사하지 않는다.

## 남은 작업

1. 사용자가 재개하면 Git status와 현재 원격/Actions/EC2 상태 재확인. uncommitted 변경을 보존한다.
2. 관리자 Secret과 DB 쓰기 권한 확인. 승인된 baseline과 기준정보/첫 계정 계획을 준비·검토한다.
3. 승인 후 업무 DB/user/schema를 준비하고 앱 전용 비밀번호를 Secret에 안전하게 저장한다.
4. 로컬 Valkey URL 보완을 배포에 반영하고 실제 TLS PING·RDS schema·앱 시작을 검증한다.
5. main workflow 성공·공개 health 본문 online/connected·CSRF/세션·역할별 로그인 흐름 확인.
6. 이전 릴리스 복구·재부팅 복구는 아직 운영 실측 안 했음(회귀 테스트만 있음).
7. 가이드/최종 보고서를 실제 완료 상태로 갱신하고 dev/main을 동기화한다.
