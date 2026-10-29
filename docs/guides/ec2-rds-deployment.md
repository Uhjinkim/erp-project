# Ubuntu EC2 · RDS · rootless Compose 배포

> 최신 운영 경로는 [main CI/CD·퍼블릭 IP HTTPS](./aws-main-cicd.md)다.
> 아래 Cloudflare/env-file 경로는 이전 설계 기록으로 유지한다.

- 작성·갱신: 2026-10-29
- 사용자 확인: Ubuntu EC2 내부 미설정, 빈 RDS, backend·nginx를 rootless Compose로 운영.
- 권장 엔진: Docker rootless + Docker Compose 2.30 이상(`env_file.format: raw` 필요).
- 상태: 저장소 준비. 실제 EC2 설치·접속·RDS 쓰기·DNS 변경·배포는 수행하지 않음.
- 경로: Cloudflare named Tunnel → 호스트 127.0.0.1:8080 → nginx 컨테이너 → backend:8000 → RDS.
- 로컬 개발은 기존 start-dev·SSH 터널을 유지한다. Compose는 운영 배포용이다.

## GitHub Actions · Secrets Manager 경로

2026-10-29 사용자는 운영 .env를 배포하지 않고 GitHub Actions와 AWS Secrets Manager를
사용하기로 했다. 빈 Ubuntu 26.04.1 서버의 준비 순서는
[Actions·AWS 준비 안내](./github-actions-aws-deployment.md)를 따른다.
아래 env 파일·서버 빌드 방식은 기존 구현 설명이다. Actions workflow·파일 없는 Secret 주입은
아직 구현되어 있지 않으며 그 방식에 아래 명령을 그대로 적용하지 않는다.

## 호스트 준비

Ubuntu 버전·CPU 아키텍처, EC2 접속 alias, Cloudflare 도메인·Tunnel 권한, RDS private endpoint·DB명·
실행 계정 권한을 확인한다. root 권한으로 최초 OS 패키지·배포 사용자·subuid/subgid를 준비하고
실제 daemon과 Compose는 `erp` 사용자로 실행한다. docker 그룹으로 rootful 소켓에 접근하는 것은
rootless 구성이 아니다.

[Docker Ubuntu 설치](https://docs.docker.com/engine/install/ubuntu/)와
[rootless 설치](https://docs.docker.com/engine/security/rootless/)에 따라 uidmap, rootless extras,
Compose plugin을 설치한다. subuid/subgid 각 65,536개 이상을 확보하고 `erp` 로그인 세션에서:

```bash
dockerd-rootless-setuptool.sh install
docker context use rootless
systemctl --user enable --now docker
```

관리자가 `sudo loginctl enable-linger erp`를 한 번 실행해 로그아웃 후·재부팅 때도 사용자 서비스를
유지한다. `docker info`의 Security Options에 rootless가 있어야 한다. 운영 Compose에 sudo를 쓰지
않는다. 사용자 namespace 제한·cgroup v2 요구사항은 해당 Ubuntu 버전의 공식 가이드를 따른다.

RDS 5432는 EC2 보안그룹에서만 허용하고 웹 80/443/8000/8080은 외부에 열지 않는다.
Compose는 nginx만 호스트 loopback 8080에 공개한다. backend는 호스트 포트가 없다.
RDS는 컨테이너에서 private endpoint로 직접 연결하며 SSH 터널을 사용하지 않는다.
Redis는 현재 health에 필요하지만 세션은 DB에 저장된다. 외부/관리형 Redis endpoint를 설정한다.
컨테이너의 localhost는 호스트가 아니므로 호스트 loopback Redis URL을 그대로 쓰면 연결되지 않는다.
Redis를 같은 Compose에 추가하는 것은 이번 두 서비스 범위에 포함하지 않았다.

## HTTPS · Cloudflare Tunnel

cloudflared는 호스트 서비스로 유지한다. named Tunnel 공개 호스트를
`http://127.0.0.1:8080`으로 연결하고 `deploy/cloudflared/config.yml.example`을 참고한다.
credential JSON은 서버에만 둔다. Cloudflare에서 공개 HTTP→HTTPS 리다이렉트를 활성화하고
API·로그인·HTML 캐시는 우회한다. nginx는 `X-Forwarded-Proto: https`를 직접 설정한다.
이 전제 때문에 Compose 포트를 0.0.0.0으로 공개하지 않는다.

컨테이너 구성은 `deploy/nginx/nginx.conf.template`을 사용한다. 기존 `nginx/production*.template`은
호스트 nginx용 대안이며 Compose에서 사용하거나 호스트 nginx로 함께 실행하지 않는다.
무료 직접 TLS 대안은 [Let’s Encrypt](https://letsencrypt.org/getting-started/)다. 직접 공개 방식을
선택하면 인증서 갱신·컨테이너 마운트·포트·프록시 scheme을 별도 구성해야 한다.

## 빈 RDS 초기화 · 배포 전 필수

**이 저장소에서 빈 RDS에 `migrate`부터 실행하면 안 된다.** workforce·vacation·board·evaluation·payroll의
초기 migration은 legacy 테이블을 생성하지 않는 state-only 정의다. ERD Markdown은 실행 가능한 DDL이
아니며 NOT NULL·CHECK·FK·배타 제약까지 재현할 수 없다. SQLite 테스트도 migration을 우회하므로
테스트 통과가 빈 PostgreSQL 초기화 성공을 보장하지 않는다.

1. 인프라/DB 담당자가 승인된 기존 ERP DB의 **스키마 전용** 백업과 migration 적용 이력 목록을
   별도 보안 경로로 확보한다. 개발 사원·계정·급여·평가 데이터는 운영에 복사하지 않는다.
2. 독립 staging DB에 해당 스키마를 복원한다. `pg_dump --schema-only`는 django_migrations의 행을
   포함하지 않으므로 스키마만 복원한 뒤 전체 migration을 실행하면 이미 있는 컬럼/테이블에서 충돌한다.
3. 스키마와 각 migration SQL을 대조해 이미 반영된 작업만 확인한다. `--fake`나 `--fake-initial`을
   일괄 실행하지 않는다. 테이블 존재만으로 컬럼·제약·시드 완료가 증명되지 않는다.
4. 시퀀스/identity, 외래키, NOT NULL, 금액 CHECK, 평가 상태 CHECK와 인사이력 제약을 확인한다.
   역할·직급·부서·휴가 유형·게시판 분류·급여 구성항목·공휴일 등 기준정보도 별도 승인 목록을 준비한다.
   스키마 전용 복원에는 기준정보가 없고 fake한 데이터 migration은 시드도 수행하지 않는다.
5. staging에서 적용 계획과 `showmigrations --plan`, `migrate --plan`, 필요한 `sqlmigrate`를 검토한다.
   workforce 0007 연락처·주소 컬럼, 평가 0002~0004 및 휴가 스냅샷 등 최신 변경을 포함한다.
6. 대상 RDS 식별자·DB명·쓰기 권한과 복구 지점을 확인해 사용자 승인을 받은 뒤 실제 적용한다.
   신규 DB 기준 스키마 SQL이 필요하다면 승인된 DDL을 별도 변경으로 관리한다. 이번 준비에서
   모델만으로 운영 제약을 추측한 초기화 SQL은 만들지 않았다.

## 파일 · 이미지 준비

배포 checkout을 `/srv/erp/releases/<release-id>`에 두고 `/srv/erp/current` symlink로 선택한다.
`erp` 사용자가 checkout과 Docker 빌드 컨텍스트를 읽을 수 있어야 한다. 호스트에 Python·Bun·nginx를
설치할 필요 없이 멀티스테이지 Dockerfile이 backend와 정적 frontend·Django static을 만든다.
의존성은 uv/Bun frozen lockfile로 설치하고 운영 비밀 없이 test settings로 static을 수집한다.
빌드 컨텍스트는 .dockerignore로 .env·개인 키·DB dump·캐시·node_modules를 제외한다.
base image는 registry manifest에서 확인한 digest로 고정했다. 갱신 때 새 digest를 검증·교체한다.
운영 앱 이미지는 빌드 후 식별자를 기록하고 같은 release tag를 다른 코드에 재사용하지 않는다.

서버에서만 다음 파일을 만든다:

| 파일 | 내용·권한 |
| --- | --- |
| /home/erp/.config/erp/compose.env | deploy/compose.env.example 참고. 릴리스 tag·도메인·절대 경로. erp 소유 0600 |
| /home/erp/.config/erp/backend.env | backend/.env.production.example 참고. 실제 DB·Redis·Django 비밀. erp 소유 0600 |
| /home/erp/.config/erp/rds-global-bundle.pem | AWS 공식 RDS CA. 컨테이너 비root UID가 읽도록 0444 |

backend.env는 KEY=value 형식이며 shell처럼 실행하지 않는다. Compose raw 형식으로 `$` 등을
그대로 전달하므로 값에 shell용 따옴표를 붙이지 않는다. 비밀은 이미지/build args에 넣지 않는다.
환경변수는 해당 Docker 사용자에게 inspect로 보일 수 있으므로 계정 접근을 제한한다.
Compose config를 출력하면 비밀이 포함될 수 있어 `config --quiet`만 사용한다.

DB_HOST는 인증서에 맞는 실제 RDS endpoint를 사용하고 sslmode=verify-full을 유지한다.
Compose가 DB_SSLROOTCERT를 컨테이너 내부 `/run/rds/ca.pem`으로 설정하고 호스트 CA 파일을 읽기
전용 마운트한다. HTTPS origin·ALLOWED_HOSTS는 실제 도메인으로 설정한다.
HSTS는 해당 호스트에 3600초, 미확인 서브도메인에 대한 includeSubDomains/preload는 비활성화한다.
관련 W005·W021만 제외하고 나머지 운영 경고는 준비 명령을 실패시킨다.

릴리스 checkout에서 `erp` 사용자로:

```bash
./scripts/prepare-production.sh /home/erp/.config/erp/compose.env --check
./scripts/prepare-production.sh /home/erp/.config/erp/compose.env
```

`--check`는 daemon 없이 Compose 구조·환경 파일만 검사한다. 기본 실행은 rootless daemon을 확인한
뒤 이미지 두 개를 빌드하고 일회성 컨테이너에서 운영 Django check와 nginx 문법 검사를 수행한다.
DB migration·시드·운영 서비스 시작은 하지 않는다. 임시 backend 검사에도 운영 비밀을 사용하므로
승인된 호스트에서 실행한다. Compose 실행 권한은 해당 환경의 비밀과 DB 접근 권한을 뜻한다.

컨테이너 내부도 비root(backend UID 10001, nginx UID 101), read-only rootfs, /tmp tmpfs,
cap_drop ALL, no-new-privileges를 사용한다. rootless daemon 자체는 호스트 사용자로 동작한다.
backend는 컨테이너 내부 0.0.0.0:8000에 수신하지만 private app network에만 연결되고 publish하지 않는다.
Gunicorn의 forwarded IP wildcard는 이 네트워크의 nginx를 신뢰한다는 전제다. 신뢰하지 않는
서비스를 이 네트워크에 추가하지 않는다. nginx는 Docker DNS로 backend를 재조회한다.

## 활성화 · 재부팅 · 롤백

빈 DB 준비·staging 검증·실제 DB 적용 승인이 완료된 뒤:

```bash
docker compose --env-file /home/erp/.config/erp/compose.env -f deploy/compose.production.yml up -d --no-build --wait
```

재부팅 관리는 `deploy/systemd/erp.service`를 사용자 unit인
`/home/erp/.config/systemd/user/erp.service`로 설치하고 다음을 실행한다:

```bash
systemctl --user daemon-reload
systemctl --user enable --now erp
```

이 unit은 사용자 docker.service에 의존한다. 앱 변경 시 `systemctl --user restart erp`를 사용한다.
current symlink와 compose.env의 release tag를 함께 관리한다. 빌드는 systemd 시작 중 실행하지 않는다.
Docker 바이너리가 /usr/bin/docker가 아니면 unit의 경로를 수정한다.
healthcheck는 backend TCP·nginx 프로세스 생존만 확인한다. 공개 HTTPS `/api/health/`의 본문에서
`status=online`, `end_to_end.status=connected`를 별도로 검증한다. 장애여도 HTTP 200이다.

CSRF→로그인→세션→로그아웃, Secure 쿠키, HR 메뉴, 수정 요청·평가·급여 권한을 승인된 계정으로
검수한다. Docker 로그는 local driver로 회전하고 access log는 URL의 개인정보 때문에 비활성화한다.
오류 로그에도 민감정보가 들어갈 수 있어 서버 계정 접근·보존을 제한한다.

롤백은 이전 image tag와 checkout을 선택한 뒤 Compose up으로 재생성한다. 기존 이미지는 검수 완료
전 삭제하지 않는다. DB 스키마가 이전 코드와 호환될 때만 수행하며 migration 역실행·데이터 복원은
별도 승인/복구 계획을 따른다. rootless 네트워크·CA 읽기·DNS·reboot 후 복구는 EC2에서 검증해야 한다.

근거: [Docker rootless](https://docs.docker.com/engine/security/rootless/),
[Compose 서비스 명세](https://docs.docker.com/reference/compose-file/services/),
[uv Docker 안내](https://docs.astral.sh/uv/guides/integration/docker/),
[nginx unprivileged 이미지](https://github.com/nginx/docker-nginx-unprivileged),
[RDS TLS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Concepts.General.SSL.html).

## 로컬 컨테이너 검증 기록 · 2026-10-28

Docker Desktop(linux/arm64)에서 backend·nginx 이미지 빌드와 두 서비스 healthy를 확인했다.
비root UID·읽기 전용 파일시스템·CA 파일 읽기·포트 제한, 정적 파일·CSRF Secure 쿠키·HSTS,
backend 재생성 후 프록시 응답을 검증했다. 임시 SQLite/offline 설정으로 공유 DB에 연결하지 않았다.
Desktop daemon은 rootless가 아니므로 준비 스크립트가 이를 거절하는 것도 확인했다.
Ubuntu EC2 rootless·systemd·RDS 연결·amd64 빌드는 별도 검증이 필요하다.
[상세 검증 보고서](../reports/2026-10-28_documentation-deployment-readiness.md)를 따른다.


## 개발 연결 풀과 운영 연결 구분 · 2026-10-29

개발 PostgreSQL은 요청 스레드 간 재사용을 위해 프로세스별 psycopg 풀(최대 4, 최소 0)을 사용한다.
운영은 기존 Gunicorn WSGI의 DB_CONN_MAX_AGE=60과 연결 검사를 유지한다. 개발 DB_POOL_* 변수를
운영에 복사해 풀과 영속 연결을 동시에 켜지 않는다. 상세 설정·검증과 터널 실측 제한은
[성능 보완 보고서](../reports/2026-10-29_database-query-improvements.md)를 따른다.
