# main GitHub Actions · EC2 운영 배포

작성·검증일: 2026-10-29. 기존 Cloudflare/env-file 설계 대신 사용자가 선택한 퍼블릭 IP HTTPS 경로다.

## 배포 흐름

1. 로컬 검증 후 `dev`에 commit/push한다. `dev` push와 `dev`/`main` 대상 PR은 CI만 수행한다.
   Markdown/문서만 변경한 push/PR은 실행을 생략하며, 수동 실행은 main에서 가능하다.
2. `dev`를 `main`에 merge/push하면 `.github/workflows/ci-cd.yml`이 실행된다.
3. SQLite 기반 backend 검사·전체 pytest·migration drift 검사·배포 회귀 테스트,
   frontend lint·69개 테스트·production build가 모두 성공해야 배포한다.
4. GitHub OIDC가 `erp-github-deploy`를 인수한다. 신뢰 조건은 이 저장소의 `refs/heads/main`이다.
   실제 발급 subject는 `repo:Uhjinkim@13661028/erp-project@1363960456:ref:refs/heads/main`이며
   CloudTrail에서 확인한 owner/repository immutable ID 포함 값을 정확히 사용한다.
   GitHub Environment를 추가하면 OIDC subject가 바뀌므로 역할 신뢰 정책도 함께 바꿔야 한다.
5. ARM64 runner에서 backend와 nginx/frontend 이미지를 빌드해 ECR에 commit SHA로 push한다.
   태그는 immutable이며 같은 SHA 재실행은 기존 이미지를 사용한다.
6. 비밀 없는 Compose/runtime bundle을 비공개 S3에 올리고 SHA256과 commit SHA를
   `ERP-DeployRelease` SSM document로 전달한다. 문서는 두 값을 정규식으로 제한한다.
7. EC2에서 `erp` 사용자로 checksum·archive 경로·Secret/config·운영 Django 검사·스키마 존재를
   확인한다. DB migration·seed·계정 생성은 실행하지 않는다.
8. 검사 성공 후 current symlink를 변경하고 user systemd를 시작한다. 실패하면 이전 릴리스로
   되돌려 시작한다. 사전 검사가 실패하면 기존 릴리스를 중지하지 않는다.
9. 내부 health 본문과 공개 HTTPS health 본문이 모두 정상이어야 배포 성공이다.
   SSM 명령 성공·HTTP 200·backend TCP 연결만으로 성공 처리하지 않는다.

## 실제 리소스

| 항목 | 값 |
| --- | --- |
| AWS | 계정 610849077646, ap-northeast-2 |
| EC2 | erp-server / i-0a4ecf2b587053b08 / ARM64 t4g.small |
| 공개 주소 | https://13.125.22.237 |
| RDS | erp-postgres, DB erp-db, 사용자 erp |
| Valkey | erp-cache-cluster, TLS 6379 |
| ECR | erp/backend, erp/nginx |
| 릴리스 S3 | erp-releases-610849077646-ap-northeast-2, releases/ prefix |
| EC2 역할 | erp-ec2-runtime |
| GitHub 역할 | erp-github-deploy |
| 운영 Secret | 기존 SecretManager, 별도 erp/production/django |

호스트 nginx 443 → 127.0.0.1:8080 nginx 컨테이너 → private network backend:8000 → RDS/Valkey다.
8000/8080은 공개하지 않는다. HTTPS와 인증서 파일은 호스트 nginx가 관리한다.
로컬 개발의 Cloudflare SSH 터널과 운영 배포는 별도다.

## 설정과 비밀

`/etc/erp/runtime.json`은 `deploy/aws/runtime.json.example` 기반의 **비밀 없는** 설정이다.
DB 이름·사용자·endpoint·도메인/IP·Secret ARN·ECR/S3 식별자를 둔다.
기존 Secret의 DB_NAME/DB_USER가 있다면 우선 사용하고, 없으면 runtime.json을 사용한다.
기존 Secret 값은 유지하며 별도 Secret의 Django 키가 기존 키보다 우선한다.
현재 비밀번호 없는 private Valkey의 REDIS_URL은 runtime.json의 실제 TLS endpoint를 사용한다.
기존 Secret의 URL은 placeholder여서 사용하지 않는다. 인증이 필요한 URL을 Secret에서 사용하려면
runtime.json의 redis_url을 null로 설정한다. URL은 `rediss://`여야 하고 추가 cache URL도 TLS를 요구한다.

EC2 역할은 지정한 Secret 2개의 GetSecretValue/DescribeSecret, 해당 ECR pull,
릴리스 prefix 읽기와 SSM Core만 허용한다. DescribeSecret은 provider의 캐시 갱신에도 필요하다.
GitHub 역할은 ECR push, 릴리스 prefix 쓰기, 지정 EC2/document의 SendCommand와 결과 조회만
허용한다. GitHub에는 운영 Secret 읽기 권한이나 장기 AWS 키가 없다.

AWS Workload Credentials Provider 3.1.1 ARM64 바이너리를 공식 SHA256으로 검증해 설치했다.
`erp-secrets.service`가 loopback 2773에서 동작하고 SSRF token은 `/run/erp-secrets/token`에 둔다.
vendored `asm_exec.py`가 동적 참조를 자식 프로세스 환경으로 치환한다. Secret JSON은 파일·CI·
image·command arguments·보고서에 저장하지 않는다. Compose에는 허용한 키만 넘긴다.
Docker 운영자는 inspect로 환경변수를 볼 수 있으므로 erp 계정 접근을 제한한다.
ECR 로그인 password는 stdin으로 전달하고 임시 Docker 인증 디렉터리는 작업 후 삭제한다.
임시 DOCKER_CONFIG가 사용자 context 설정을 가리지 않도록 rootless 소켓을 DOCKER_HOST로 명시한다.
CA bind mount는 rootlesskit의 `/etc` copy-up과 충돌하지 않는 `/home/erp/.config/erp/` 아래에 둔다.
재부팅 후에도 로그인·Secret 조회를 다시 수행한다. stop은 Secret/API 장애 중에도 가능하다.

기존 Django 키는 길이 검사에 실패해 별도 Secret에 새 키를 생성했다. 원래 Secret의 비밀번호나
값은 변경하지 않았고, 값은 채팅·로그로 읽지 않았다. 새 키를 교체하면 기존 세션에 영향을 준다.

## 인증서와 IP 변경

Certbot 5.8과 Let’s Encrypt shortlived IP 인증서를 사용한다. staging 발급을 먼저 확인한 후 정식
인증서를 발급했다. IP 인증서는 약 6일간 유효하므로 자동 갱신이 필수다.
`snap.certbot.renew.timer`와 `/etc/letsencrypt/renewal-hooks/deploy/erp-nginx`가 nginx를 reload한다.

관리자 진단 명령:

```bash
sudo certbot certificates
sudo /snap/bin/certbot renew --cert-name 13.125.22.237 --dry-run --run-deploy-hooks
sudo systemctl status snap.certbot.renew.timer erp-secrets
```

현재 IP가 EC2 stop/start로 변경되면 기존 인증서와 URL을 그대로 사용할 수 없다. runtime.json,
workflow PUBLIC_HOST, nginx, 새 IP 인증서를 함께 변경한다. IP를 고정하려면 별도 Elastic IP
도입과 비용을 검토한다. 현재 작업에서 Elastic IP를 새로 할당하지 않았다.

## 호스트 파일과 운영

최초 준비는 root로 `deploy/aws/bootstrap.sh`, 인증서 발급 후 `enable-ip-tls.sh`를 사용한다.
이 스크립트는 현재 Ubuntu ARM64/erp 사용자 환경에 맞춰져 있다. 임의 호스트에 그대로 적용하지 않는다.
SSM document의 UID 1002는 현재 erp UID와 일치한다. 사용자를 바꾸면 문서도 갱신해야 한다.
root 소유 launcher/asm/systemd/provider 변경은 관리자가 재설치해야 한다. 자동 release bundle은
Compose/runtime만 갱신하며 root 소유 프로그램을 자동 교체하지 않는다.

erp 로그인 세션에서:

```bash
systemctl --user status erp docker
systemctl --user restart erp
python3 /srv/erp/current/deploy/aws/runtime.py secret-keys
```

서비스 로그에는 애플리케이션 오류가 포함될 수 있으므로 제한된 서버에서만 확인한다. 컨테이너
환경이나 Secret 원문을 출력하지 않는다. 이전 버전 복구도 workflow에서 해당 main commit을 다시
실행하거나 관리자가 승인한 SHA/checksum으로 `erp-release`를 실행한다. 스키마 호환성을 확인하고
DB migration 역실행은 하지 않는다.

## 첫 운영 기동의 제약

기존 migration에는 state-only 업무 테이블 정의가 있다. 빈 RDS는 `migrate`만으로 초기화되지 않는다.
사용자가 확인한 DB에 읽기 전용 접속·스키마 검사부터 하고, schema baseline·기준정보·계정 준비는
대상·권한·복구 지점의 별도 승인 후 진행한다. 이 workflow에는 DB 쓰기 명령을 추가하지 않는다.
현재 실측 결과와 미완료 항목은 [배포 보고서](../reports/2026-10-29_main-cicd-deployment.md)에 기록한다.

근거: [GitHub OIDC](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws),
[IP 인증서/Certbot](https://letsencrypt.org/2026/03/11/shorter-certs-certbot),
[AWS Workload Credentials Provider](https://docs.aws.amazon.com/secretsmanager/latest/userguide/workload-credentials-provider.html).
