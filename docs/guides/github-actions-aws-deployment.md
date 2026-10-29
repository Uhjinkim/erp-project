# 빈 Ubuntu EC2에서 GitHub Actions · Secrets Manager 운영 준비

> 후속 구현: [main CI/CD 실행 가이드](./aws-main-cicd.md). 아래 문서는 기존 Cloudflare 경로의
> 초기 설계 기록이다. 실제 운영은 퍼블릭 IP HTTPS·ECR/SSM·Secrets Manager launcher를 사용한다.

- 작성일: 2026-10-29
- 대상: 사용자가 보유한 Ubuntu 26.04.1 EC2. 서버에 설치된 프로그램 없음.
- 사용자 결정: GitHub Actions 사용, 운영 .env 파일을 GitHub/이미지/배포 산출물로 전달하지 않음.
- 기존 구성 유지: rootless Docker Compose, nginx+backend, 호스트 Cloudflare Tunnel, 외부 PostgreSQL/Redis.
- 상태: 설치·권한·배포 설계 안내. 실제 AWS 변경이나 자동화 코드 구현·배포를 완료한 문서가 아니다.

## 1. 먼저 구분할 준비 상태

현재 `deploy/Dockerfile`은 운영 비밀 없이 backend/nginx 이미지를 빌드할 수 있다. 그러나
`deploy/compose.production.yml`과 `deploy/systemd/erp.service`는 서버의 env 파일을 요구한다.
`.github/workflows/`와 Secrets Manager 조회 launcher는 아직 없다. 기존 준비 스크립트는 서버에서
빌드하는 경로이므로 아래 ECR/Actions 경로에 그대로 사용하지 않는다.

이 문서의 OS/AWS 준비는 지금 진행할 수 있다. 첫 운영 기동 전에는 8절 DB baseline 준비와
9절 저장소 연결 구현이 끝나야 한다. 환경 파일을 배포에서 제외하는 것과 프로세스 환경변수를
없애는 것은 다르다. Django의 `env("DB_PASSWORD")`는 그대로 사용한다.

## 2. 목표 구조와 준비할 값

```text
GitHub Actions --OIDC--> AWS 배포 역할
  ├─ 테스트·이미지 빌드 --> ECR
  ├─ 비밀 없는 릴리스 파일 --> 비공개 S3 (선택한 배포 전달 경로)
  └─ SSM 배포 명령 --> EC2

EC2의 IAM 역할
  ├─ ECR 이미지 pull
  ├─ S3 릴리스 파일 download
  └─ Secrets Manager 읽기 --> 시작 프로세스 메모리 --> 컨테이너 환경변수

사용자 HTTPS --> Cloudflare Tunnel --> 호스트 127.0.0.1:8080
  --> nginx 컨테이너 --> backend:8000 --> RDS / Redis
```

AWS 계정 ID·리전, EC2 ID·CPU 아키텍처, 저장소 소유자/이름, 운영 도메인, RDS endpoint·DB명·
업무용 DB 사용자, Redis endpoint, Secret ARN, ECR 2개, 릴리스 S3 bucket을 정한다.
아래 `ap-northeast-2`, `erp.example.com`, 이름/ARN의 예시는 실제 환경에 맞춘다.

**OS 확인:** Docker 공식 Ubuntu 설치 목록에는 Resolute 26.04가 있다. 반면 확인한 AWS Systems
Manager 지원 OS 표와 Ubuntu Agent 설치 문서에는 26.04가 없다. 따라서 Docker 지원을 SSM 지원으로
간주하지 않는다. 6절 등록을 실측하고, 공식 지원이 필수이거나 등록이 안 되면 SSM 지원 Ubuntu
버전으로 별도 호스트를 준비하거나 검증된 다른 배포 전달 경로를 확정한다. 실행 중 OS를 임의로
다운그레이드하지 않는다.

근거: [Docker Ubuntu](https://docs.docker.com/engine/install/ubuntu/),
[AWS Systems Manager 지원 OS](https://docs.aws.amazon.com/systems-manager/latest/userguide/operating-systems-and-machine-types.html).

## 3. AWS 콘솔에서 네트워크와 EC2 역할 준비

- EC2 보안그룹: 초기 SSH 22는 본인 공인 IP/32만. Cloudflare Tunnel 경로의 80/443/8000/8080
  inbound는 필요 없다. SSM 배포도 inbound 22를 사용하지 않는다.
- RDS/Redis는 가능하면 EC2와 연결 가능한 private VPC에 둔다. RDS 5432 inbound source는
  EC2 보안그룹으로, Redis 포트도 EC2 보안그룹으로 제한한다. 운영에서 개발 SSH 터널을 쓰지 않는다.
- EC2 outbound: OS 패키지 저장소, AWS API/ECR/S3, Cloudflare 연결이 가능해야 한다.
  Cloudflare Tunnel은 7844 UDP/TCP, 패키지/API는 보통 443이 필요하다.
- private subnet은 NAT/적절한 VPC endpoint가 필요하다. AWS endpoint만으로 Cloudflare와 외부
  패키지 저장소까지 접근할 수 있는 것은 아니다.

IAM → 역할 생성 → AWS 서비스 → EC2로 `erp-ec2-runtime` 같은 역할을 만든다.
EC2 → 인스턴스 → 보안 → IAM 역할 수정에서 연결한다.

필요 권한을 역할에 부여한다:

| 용도 | 권한 범위 |
| --- | --- |
| SSM 연결 | AWS 관리형 AmazonSSMManagedInstanceCore |
| 비밀값 조회 | secretsmanager:GetSecretValue, 운영 Secret의 정확한 ARN만 |
| 고객 관리 KMS 사용 시 | kms:Decrypt, 해당 키 ARN 및 키 정책 허용 |
| ECR 인증 | ecr:GetAuthorizationToken, Resource * |
| 이미지 pull | ecr:BatchGetImage, ecr:GetDownloadUrlForLayer, ecr:BatchCheckLayerAvailability, ERP 저장소 2개만 |
| 릴리스 다운로드 | s3:GetObject, 선택한 bucket의 ERP release prefix만 |

SSM Core에는 운영 Secret 조회 권한이 포함되어 있지 않다. runtime 역할에 ECR push·Secret 수정
권한은 필요 없다. AWS 장기 액세스 키를 EC2에 `aws configure`로 입력하지 않는다.

근거: [EC2 역할과 Secret 읽기](https://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access_iam-policies.html),
[ECR 인증](https://docs.aws.amazon.com/AmazonECR/latest/userguide/registry_auth.html).

## 4. Ubuntu 최초 설치

EC2 기본 `ubuntu` SSH 계정에서 실행한다. 관리자 명령과 이후 `erp` 사용자 명령을 구분한다.

```bash
cat /etc/os-release
uname -m
dpkg --print-architecture
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y ca-certificates curl gnupg unzip less python3 uidmap dbus-user-session slirp4netns fuse-overlayfs
sudo timedatectl set-timezone Asia/Seoul
timedatectl status
```

x86_64이면 CI 이미지 플랫폼은 linux/amd64, aarch64이면 linux/arm64다. ARM 서버에 amd64
전용 이미지를 보내지 않는다. OS 시간대는 운영 로그 편의 설정이며 Django의 Asia/Seoul/USE_TZ와
프론트 업무 시간대 처리도 별도로 유지한다. 업데이트가 재부팅을 요구하면 재접속 가능성을 확인한 뒤
재부팅하고 다음 작업을 진행한다.

Docker 공식 저장소 등록:

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF_DOCKER
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF_DOCKER
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin docker-ce-rootless-extras
sudo systemctl disable --now docker.service docker.socket
```

공식 deb의 rootless extras는 Ubuntu의 AppArmor 사용자 namespace 처리를 따른다. rootless 오류가
나면 [Docker 문제 해결](https://docs.docker.com/engine/security/rootless/troubleshoot/)을 확인한다.
AppArmor를 전역 해제하거나 사용자 namespace 제한을 무작정 끄지 않는다.

배포 사용자 준비:

```bash
sudo adduser --disabled-password --gecos "" erp
sudo install -d -m 0700 -o erp -g erp /home/erp/.ssh
sudo install -m 0600 -o erp -g erp /home/ubuntu/.ssh/authorized_keys /home/erp/.ssh/authorized_keys
sudo install -d -m 0755 -o erp -g erp /srv/erp/releases
sudo loginctl enable-linger erp
sudo grep '^erp:' /etc/subuid /etc/subgid
```

각 subordinate UID/GID 범위가 최소 65,536개인지 확인한다. 없다면 관리자가 다른 사용자와 겹치지
않는 범위를 배정한다. `erp`를 docker 그룹이나 sudo 그룹에 추가할 필요는 없다.

**새 SSH 세션으로 erp 사용자에 직접 로그인**한 뒤 실행한다. 단순 `sudo su` 세션에서 사용자
systemd 버스가 없다는 오류를 정상 설치 실패로 오인하지 않는다.

```bash
whoami
dockerd-rootless-setuptool.sh install
docker context use rootless
systemctl --user enable --now docker
docker info --format '{{json .SecurityOptions}}'
docker compose version
mkdir -p ~/.config/erp ~/.config/systemd/user
chmod 700 ~/.config/erp
```

출력에 rootless가 있어야 한다. 앱 컨테이너도 기존처럼 비root UID로 실행한다.
근거: [rootless 설치](https://docs.docker.com/engine/security/rootless/),
[사용자 systemd/linger](https://docs.docker.com/engine/security/rootless/tips/).

## 5. AWS CLI와 리소스 준비

AWS CLI v2를 시스템 전체에서 사용할 수 있게 설치한다. 관리자 ubuntu 세션에서:

```bash
sudo snap install aws-cli --classic
aws --version
```

AWS가 제공하는 snap 설치 경로다. 버전 고정이 필요하면 공식 CLI 설치 안내의 버전 지정 설치를
사용한다. 이후 erp 세션에서 다음만 확인한다. 역할 이름/계정 식별자는 나오지만 비밀값은 나오지 않는다.

```bash
aws sts get-caller-identity --region ap-northeast-2
```

CLI가 자격증명을 찾지 못하면 EC2 IAM 역할 연결·IMDS 접근을 먼저 확인한다. 컨테이너에서
IMDS를 읽는 설계가 아니라 EC2 호스트 launcher가 조회하는 설계다. rootless user service에서도
AWS CLI를 찾도록 추후 unit에 /snap/bin 등을 포함한 PATH를 지정한다.

ECR 콘솔에서 비공개 `erp-backend`, `erp-nginx` 저장소를 생성하고 tag immutability를 켠다.
이미지는 latest 대신 Git commit SHA로 식별하며 같은 SHA tag에 다른 이미지를 덮어쓰지 않는다.
동일 SHA 재실행은 이미 존재하는 이미지를 재사용하도록 workflow에서 처리해야 한다.
S3 릴리스 전달을 선택하면 private bucket, public access block, 암호화, versioning을 구성한다.
이 bucket에는 비밀값이나 .env를 넣지 않고 릴리스 SHA별 배포 파일만 넣는다.

Secrets Manager → 새 보안 암호 저장 → 다른 유형 → 키/값으로 다음을 등록한다:

```json
{
  "DJANGO_SECRET_KEY": "<운영 전용 충분히 긴 무작위 키>",
  "DB_PASSWORD": "<RDS 업무용 사용자 비밀번호>",
  "REDIS_URL": "<운영 Redis 접속 URL>"
}
```

이름 예시는 `erp/prod/backend`. 운영 DB 비밀번호와 같은 값이어야 하며 RDS master 계정을 앱
계정으로 쓰지 않는다. Redis TLS 사용 시 URL은 rediss://이며, 사용자/비밀번호에 URL 예약문자가
있으면 URL 인코딩한다. RDS에서 자동 관리하는 Secret의 username/password 구조를 사용한다면
launcher에서 현재 DB_USER/DB_PASSWORD 이름으로 명시적으로 매핑한다.

나머지 도메인·DB host/name/user·포트·timeout·CA 경로는 비밀 없는 호스트 설정으로 둔다.
Secret ARN 자체는 비밀번호가 아니다. GitHub에는 ARN/리전/도메인 등의 식별자만 Variables로
보관할 수 있다. 운영 비밀을 VITE_* 또는 Docker build ARG에 넣지 않는다.

RDS CA는 erp 세션에서 AWS 공식 bundle을 내려받는다:

```bash
curl -fsSL https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem -o ~/.config/erp/rds-global-bundle.pem
chmod 444 ~/.config/erp/rds-global-bundle.pem
```

bind mount의 부모 경로는 호스트 Docker 사용자가 접근할 수 있어야 하고, 파일은 컨테이너 비root
UID가 읽을 수 있어야 한다. DB_HOST는 실제 RDS 인증서 호스트를 쓰고 verify-full을 유지한다.

근거: [CLI 설치](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html),
[Secret 생성](https://docs.aws.amazon.com/secretsmanager/latest/userguide/create_secret.html),
[RDS TLS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Concepts.General.SSL.html).

## 6. SSM 등록 실측

Ubuntu 26.04 지원은 2절 제약을 먼저 읽는다. 초기 ubuntu 관리자 세션에서 기존 Agent 존재 여부를
확인하고 이미 있으면 중복 설치하지 않는다:

```bash
snap list amazon-ssm-agent
systemctl status amazon-ssm-agent --no-pager
```

snap과 deb 둘 중 하나로 이미 정상 실행 중이면 유지한다. 둘 다 없고 이 OS에서 검증을 진행한다면:

```bash
sudo snap install amazon-ssm-agent --classic
sudo snap start --enable amazon-ssm-agent
sudo snap services amazon-ssm-agent
```

EC2 IAM 역할에 SSM Core를 연결한 뒤 Systems Manager → Fleet Manager에서 이 인스턴스가
Online인지 확인하고 Run Command의 `whoami`·`uname -m` 같은 읽기 명령을 검증한다.
인스턴스 내부 프로세스가 살아 있다는 것만으로 SSM 배포 가능이 확인된 것은 아니다.
미등록이면 IAM/네트워크/Agent 로그를 확인하고, 해당 OS 지원 제약이 남으면 자동 배포 단계로
넘어가지 않는다. 대안 전달 경로가 SSH라면 별도의 키·host key 검증·GitHub runner 접근 경로를
확정해야 하며, 불특정 runner를 위해 22를 전 세계에 개방하지 않는다.

[공식 Ubuntu Agent 설치 안내](https://docs.aws.amazon.com/systems-manager/latest/userguide/agent-install-ubuntu-64-snap.html).

## 7. Cloudflare 웹 진입

관리자 ubuntu 세션에서 Cloudflare 공식 패키지를 설치한다:

```bash
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt-get update
sudo apt-get install -y cloudflared
```

Cloudflare 콘솔에서 운영 named tunnel을 만들고 Ubuntu/해당 CPU의 서비스 설치 절차를 따른다.
기존 locally-managed tunnel이면 `deploy/cloudflared/config.yml.example`의 UUID/credential 경로를
채워 호스트 서비스로 설치한다. remotely-managed tunnel이면 콘솔 절차에 따라 관리한다.
Tunnel credential/token은 GitHub나 채팅에 넣지 않는다.

공개 hostname은 실제 운영 도메인, origin service는 `http://127.0.0.1:8080`으로 지정한다.
공개 HTTP는 HTTPS로 리다이렉트하고 API/로그인/HTML 캐시는 우회한다. nginx 컨테이너는 도메인
Host를 검사하므로 도메인도 일치시킨다. 앱 기동 전 origin 연결 오류는 자연스러운 상태다.

[공식 패키지](https://pkg.cloudflare.com/index.html),
[Tunnel 생성](https://developers.cloudflare.com/tunnel/get-started/).

## 8. 빈 RDS baseline: 앱 첫 기동의 선행 조건

**이 저장소는 빈 RDS에 migrate만 실행해 초기화할 수 없다.** 여러 업무 모듈의 첫 migration에
SeparateDatabaseAndState(database_operations=[])가 있어 업무 테이블을 만들지 않는다.
Docker/SSM 성공과 DB 준비 완료는 별개다.

기존 [빈 RDS 준비 절차](./ec2-rds-deployment.md#빈-rds-초기화--배포-전-필수)를 따른다.
DB 담당자가 승인된 schema-only baseline과 제약·시퀀스/identity·기준정보·migration 이력 대응표를
준비하고 독립 staging에서 먼저 검증한다. 스키마 dump는 migration 적용 행·시드 데이터를 포함하지
않는다. 복원 후 migrate/fake/fake-initial을 일괄 적용하지 않는다.

운영 적용은 대상 RDS·DB명·권한·복구 지점을 확인하고 별도로 승인받는다. GitHub 배포 workflow에
migrate·seed·createsuperuser를 자동으로 넣지 않는다. 첫 계정과 사원 연결도 승인된 초기 등록
절차로 준비해야 실제 ERP 로그인 이후 업무를 사용할 수 있다. 개발 사원·개인정보를 운영에 복사하지 않는다.

## 9. 저장소에서 추가 구현할 자동화 계약

다음은 **현재 구현된 동작이 아니라 필요한 변경 목록**이다. 이 문서만 추가했다고 workflow나
Secret 조회 코드가 생긴 것은 아니다.

1. **Compose 런타임 변경:** backend env_file 요구를 제거하고 환경변수를 명시적으로 매핑한다.
   backend/nginx image는 ECR 정규 URI와 SHA로 바꾼다. 호스트 CA, loopback 8080, 비root,
   read-only rootfs 등 기존 제약은 유지한다.
2. **호스트 launcher:** 리전/Secret ARN/도메인/DB host 등 비밀 없는 설정을 읽는다. AWS CLI/SDK로
   SecretString을 읽고 JSON을 파싱해 허용한 키만 자식 프로세스 환경에 넣는다. Secret을 shell 코드로
   eval하거나 JSON을 source하지 않는다. 정상 시작/검사 경로에서만 조회하며 요청마다 조회하지 않는다.
   ECR login의 password-stdin으로 인증하고 pull → check --deploy → up 순으로 진행한다.
3. **user systemd unit:** erp 사용자의 rootless docker.service에 의존하게 하고 launcher를 실행한다.
   PATH/XDG_RUNTIME_DIR 등 비대화식 실행 조건을 맞춘다. Secret을 Environment=에 박아 넣거나
   EnvironmentFile로 저장하지 않는다. 재부팅 시 재조회·재실행하고, Secret 장애 중에도 stop은 가능해야 한다.
4. **GitHub workflow:** 테스트 → backend/nginx target 이미지 build/push → 비밀 없는 배포 bundle
   업로드 → SSM 명령 → 명령 완료 및 앱 본문 상태 검증. SSM 전달 성공만으로 배포 성공 처리하지 않는다.
5. **릴리스/복구:** 릴리스 SHA별 파일을 분리하고 현재 symlink를 관리한다. 순차 배포 lock을 두고
   건강하지 않은 새 릴리스를 성공으로 기록하지 않는다. 이전 이미지와 호환 가능한 설정/스키마로
   복구하며 DB migration 역실행을 자동화하지 않는다.

Compose 전달 형태의 예시(이 두 키만 있으면 운영 설정이 완성되는 것은 아니다):

```yaml
environment:
  DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY:?required}
  DB_PASSWORD: ${DB_PASSWORD:?required}
```

필수 환경변수 목록은 `backend/.env.production.example`과 production.py를 대조한다. Secret 조회
결과만으로 일반 DB/도메인 설정까지 채워지는 것은 아니다. 컨테이너 환경변수는 Docker 운영자에게
inspect로 보일 수 있다. `.env` 파일이 없다는 것을 모든 운영자가 비밀을 못 본다는 의미로 해석하지 않는다.
ECR 로그인도 credential helper 또는 제한된 임시 Docker auth 설정의 정리까지 설계한다.

## 10. GitHub OIDC 설정

AWS IAM → 자격 증명 공급자 → OpenID Connect:

- Provider URL: https://token.actions.githubusercontent.com
- Audience: sts.amazonaws.com

별도 GitHub 배포 역할을 만든다. EC2 runtime 역할과 구분한다. GitHub Environment를 production으로
사용하는 예시 신뢰 조건은 다음과 같다. 000000000000은 실제 AWS 계정 ID로 대체한다.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "arn:aws:iam::000000000000:oidc-provider/token.actions.githubusercontent.com"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {"StringEquals": {
      "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
      "token.actions.githubusercontent.com:sub": "repo:Uhjinkim/erp-project:environment:production"
    }}
  }]
}
```

이 sub는 workflow의 environment: production과 짝이다. environment를 쓰지 않는 방식이라면
sub는 repo:Uhjinkim/erp-project:ref:refs/heads/main 형태가 된다. 둘을 혼동하지 않는다.
GitHub production Environment의 배포 가능 branch를 main으로 제한한다. 보호 규칙은 저장소
plan/설정에 맞춰 적용한다. 임의 PR/ref가 운영 역할을 인수하지 않게 한다.

GitHub 역할에는 ERP 저장소 2개 ECR push, ECR 인증, 릴리스 S3 prefix 쓰기, 배포 대상 EC2와
승인된 SSM document의 SendCommand 및 결과 조회 권한만 부여한다. Secret 읽기 권한은 주지 않는다.
SSM 명령은 높은 권한으로 실행될 수 있으므로 대상 인스턴스/document를 제한하고, 실제 Docker는
명시적으로 erp 사용자·해당 사용자 systemd로 실행해야 한다. root SSM 환경에서 docker up을
직접 실행하면 준비한 rootless daemon과 다른 경로를 사용하게 된다.

GitHub → Settings → Environments → production → Variables 예시:

| 이름 | 내용 |
| --- | --- |
| AWS_REGION | ap-northeast-2 등 실제 리전 |
| AWS_ROLE_ARN | GitHub OIDC 배포 역할 ARN |
| EC2_INSTANCE_ID | 배포할 인스턴스 ID |
| ECR_REGISTRY | 계정ID.dkr.ecr.리전.amazonaws.com |
| RELEASE_BUCKET | 비밀 없는 릴리스 bundle 저장 bucket |
| IMAGE_PLATFORM | linux/amd64 또는 linux/arm64 |
| ERP_DOMAIN | 실제 운영 도메인 |

GitHub에 AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY나 DB_PASSWORD를 등록할 필요가 없다.

workflow의 OIDC 연결 뼈대이며, 전체 배포 workflow가 아니다:

```yaml
permissions:
  contents: read
  id-token: write
concurrency:
  group: erp-production
  cancel-in-progress: false
jobs:
  deploy:
    runs-on: ubuntu-24.04
    environment: production
    steps:
      # 검토한 commit SHA로 고정한 actions/checkout 뒤에 실행
      - uses: aws-actions/configure-aws-credentials@<검토한-commit-SHA>
        with:
          role-to-assume: ${{ vars.AWS_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}
```

첫 배포는 main의 명시적 workflow_dispatch로 확인하고, DB/기동/복구 검증 후 main push 자동화를
추가할 수 있다. CI는 production Secret 없이 테스트 설정으로 검사하고 이미지를 빌드한다.
GitHub runner의 env가 EC2에 자동 전달되지는 않는다. 이미지에는 Python/Bun의 frozen lockfile을
사용하고 Actions 자체도 검토한 SHA로 고정한다.

[GitHub AWS OIDC 공식 안내](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws),
[ECR push 권한](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-push-iam.html).

## 11. 첫 기동과 검수 순서

8~10절 구현/권한/DB 준비 후 배포 launcher의 최종 명령과 실제 환경을 검토한다. 지금 저장소에는
해당 launcher가 없으므로 `aws deploy` 같은 존재하지 않는 프로젝트 명령을 실행하지 않는다.

- CI 검사 성공, 동일 CPU 이미지 pull, 운영 Django check --deploy 통과.
- RDS 인증서·DB 연결·업무 schema 준비, Redis PING을 확인.
- erp 사용자 rootless Compose up, nginx/backend 상태 확인.
- SSH에서 공개 도메인 Host를 넣어 로컬 프록시 확인:

```bash
curl --fail --silent --show-error --max-time 30 \
  -H 'Host: erp.example.com' http://127.0.0.1:8080/api/health/ \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); ok=d.get("status")=="online" and d.get("end_to_end",{}).get("status")=="connected"; print("ready" if ok else "not ready"); sys.exit(0 if ok else 1)'
```

- 공개 HTTPS에서도 동일하게 확인한다. health API는 장애에도 HTTP 200을 줄 수 있어 본문 검사가
  필요하다. nginx /healthz 204와 backend TCP health만으로 DB/업무 연결을 판정하지 않는다.
- CSRF→로그인→세션 유지→로그아웃, Secure cookie, 역할별 메뉴, 승인된 사원의 휴가 잔여/신청을
  허용된 범위에서 검수한다. 계정이 employee와 연결되어 있는지도 확인한다.
- EC2 재부팅 후 user Docker, 앱, Cloudflare 복구와 공개 health를 확인한다.
- 이전 릴리스로 복구할 수 있는지 staging에서 검증한다. 스키마 호환성이 없는 롤백을 강행하지 않는다.

원격 AWS/공유 DB/실제 도메인에 이 문서 작성자가 수행한 변경은 없다. Secret 값은 보고서·로그·
workflow 출력에 남기지 않는다. 이 문서는 현재 없는 자동화를 구현 완료로 표시하지 않는다.


## 2026-10-29 기준 목록 캐시 설정

운영 backend는 기준 목록 캐시를 기본 사용한다. `REDIS_URL`의 기존 Redis/Valkey를 사용하며
분리하려면 Secret JSON에 `REFERENCE_CACHE_URL`을 추가한다. TLS endpoint는 `rediss://`다.
같은 endpoint를 여러 배포에서 공유하면 `REFERENCE_CACHE_KEY_PREFIX`를 배포별로 구분한다.
`REFERENCE_CACHE_ENABLED=false`로 비활성화할 수 있다. TTL 기본 180초(최대 300), 연결·읽기
제한시간 기본 각각 0.2초이며 health PING 제한시간과 별개다.

캐시 사용자는 기존 PING과 클라이언트 연결 명령에 더해 GET/SET(SET NX·EX 포함)을 허용해야
한다. RBAC 키 패턴은 해당 prefix 범위로 제한하고 세션·업무 데이터 키와 구분한다.
운영에서 실제 TLS/RBAC 연결과 반복 조회·목록 수정 후 갱신을 staging에서 확인한다.
본 구현 검증은 SQLite/로컬 캐시·장애 모의이며 AWS 연결 검증은 수행하지 않았다.
상세 범위와 외부 SQL 갱신 제한은 [캐시 적용 보고서](../reports/2026-10-29_reference-cache.md)를 따른다.
