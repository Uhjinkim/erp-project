# ERP Project

사원·부서·인증과 휴가 신청·승인 업무를 제공하는 ERP 애플리케이션입니다. Backend와 Frontend는
개발 PC에서 실행하고 PostgreSQL과 Redis는 팀이 관리하는 원격 인프라를 사용합니다. 로컬
애플리케이션은 SSH 로컬 포워딩으로만 원격 서비스에 접근하며, 저장소에는 로컬 컨테이너 실행
구성이 없습니다.

## 프로젝트 개요

운영 배포는 [main GitHub Actions · EC2/IP HTTPS 가이드](docs/guides/aws-main-cicd.md)를 따른다.
`dev`는 CI, `main`은 CI 성공 후 기존 AWS EC2에 자동 배포한다. 운영 Secret은 서버에서 주입한다.

### 기술 구성

- Backend: Python 3.13, Django 5.2 LTS, Django REST Framework, uv
- Frontend: React 19, TypeScript, Vite, Bun 1.4
- Infrastructure: 원격 PostgreSQL 및 Redis, Cloudflare Tunnel 경유 OpenSSH 로컬 포워딩, 로컬 개발용 nginx
- Authentication: 이메일 로그인, Django 서버 세션, HttpOnly 쿠키, CSRF 보호

### 주요 기능

- 사원, 인적사항, 부서, 직급과 역할 조회·관리
- 이메일 기반 로그인과 서버 세션 인증
- 휴가 신청, 취소, 승인, 반려, 승인 회수와 상태 이력
- 부서장 우선 승인 및 부서장 부재 시 인사 승인담당자 fallback
- Backend, PostgreSQL, Redis와 사원 연동 상태 확인
- 업무별 API 오류 안내와 인증 서버 재시도

### 저장소 구조

```text
erp-project/
├── backend/                 Django API와 도메인 모듈
│   ├── accounts/            이메일 로그인과 세션 인증
│   ├── workforce/           사원·부서·직급·역할
│   ├── vacation/            휴가 신청·승인
│   ├── board/               일반글·공지
│   ├── evaluation/          인사평가
│   ├── payroll/             급여 정산·정정
│   └── config/              환경별 Django 설정과 health check
├── frontend/                React 애플리케이션
├── nginx/                   로컬 개발 reverse proxy 설정 템플릿
├── scripts/                 SSH 터널과 통합 개발환경 실행 스크립트
├── docs/                    작업 보고서와 설계 기록
└── .env.example             SSH 터널 환경변수 예제
```

Python과 Frontend 의존성은 각각의 디렉터리와 lockfile로 관리합니다. `.venv`, `node_modules`,
빌드 결과물, 실제 환경 파일과 자격증명은 Git에 포함하지 않습니다.

기능 모듈을 별도 브랜치에서 개발할 때의 `dev` 동기화, 문서 초안 작성과 병합 절차는
[기능 모듈 브랜치·문서 협업 가이드](docs/guides/module-branch-docs-workflow.md)를 따릅니다.

확정 디자인에 따른 화면 배정, 디자인시스템 범위, 공통 토대 구현 순서와 팀원 작업 카드는
[프론트엔드 모듈 작업 안내서](docs/guides/frontend-module-delivery.md)를 참고합니다.
화면 분할은 Operations Graphite 39장을 참고했으며 확정 시안·버전과 대조한 뒤 배정합니다.
[구현된 공통 토대 사용 계약](docs/guides/frontend-foundation-contracts.md)에서 모듈 진입점과
컴포넌트 사용법, 현재 연결된 화면과 후속 작업을 확인합니다.

## 1. 필수 도구

개발 PC에 다음 도구가 필요합니다.

- Git
- Python 3.13과 uv
- Bun 1.4
- OpenSSH 클라이언트
- cloudflared (Cloudflare Access SSH 연결용)
- nginx

Podman, Docker 또는 로컬 PostgreSQL·Redis는 필요하지 않습니다.

### cloudflared 설치

macOS:

```bash
brew install cloudflared
```

Windows는 설치 후 새 PowerShell을 엽니다.

```powershell
winget install --id Cloudflare.cloudflared --exact
```

Linux는 [Cloudflare 공식 다운로드/설치 안내](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/)를 따릅니다.
설치 후 `cloudflared --version`으로 PATH에서 실행되는지 확인합니다.

### nginx 설치

macOS는 Homebrew로 설치할 수 있습니다.

```bash
brew install nginx
```

Ubuntu/Debian 계열은 배포판 패키지를 사용할 수 있습니다. 개발 스크립트가 nginx 프로세스를
직접 실행하므로 OS 서비스로 시작할 필요는 없습니다.

```bash
sudo apt update
sudo apt install nginx
```

Windows는 WinGet으로 설치한 뒤 새 PowerShell을 엽니다.

```powershell
winget install nginxinc.nginx
```

설치 후 다음 명령으로 `PATH` 인식을 확인합니다. Windows에서의 nginx 동작과 제약은
[nginx/Windows 안내](https://nginx.org/en/docs/windows.html)를 참고합니다.

```powershell
nginx -v
```

nginx를 Windows 서비스로 등록할 필요는 없습니다. 통합 개발 스크립트가 실행마다 전용 설정과
로그·임시 디렉터리를 만들고 종료할 때 정리합니다.

## 2. 저장소 Clone

```bash
git clone <REPOSITORY_URL>
cd erp-project
```

`<REPOSITORY_URL>`은 팀에서 안내받은 저장소 주소로 교체합니다. 문서나 스크립트에 접근 토큰을
직접 입력하지 않습니다.

## 3. 환경변수 구성

환경별 예제 파일을 복사한 뒤 실제 값은 로컬 파일 또는 배포 환경의 secret 관리 기능에만
입력합니다.

### macOS/Linux

```bash
cp .env.example .env
cp backend/.env.development.example backend/.env.development
cp frontend/.env.development.example frontend/.env.development
```

### Windows PowerShell

```powershell
Copy-Item .env.example .env
Copy-Item backend/.env.development.example backend/.env.development
Copy-Item frontend/.env.development.example frontend/.env.development
```

환경 파일의 책임은 다음과 같이 분리합니다.

| 파일 | 용도 | 비밀값 허용 |
| --- | --- | --- |
| 루트 `.env` | SSH 접속 및 PostgreSQL·Redis 포워딩 | SSH 호스트·사용자와 개인 키 경로만 입력, SSH 비밀번호 저장 금지 |
| `backend/.env.development` | Django 개발 설정과 DB·Redis 인증 | 허용, Git 커밋 금지 |
| `backend/.env.production` | Django 운영 설정 | 배포 secret/configuration 시스템으로 주입 |
| `frontend/.env.development` | 개발 UI와 공개 API 설정 | 금지 |
| `frontend/.env.production` | 운영 빌드 공개 설정 | 금지 |

`VITE_`로 시작하는 값은 브라우저 번들에 포함됩니다. 비밀번호, secret, 내부 전용 토큰을
Frontend 환경 파일에 넣으면 안 됩니다.

### SSH 터널 설정

루트 `.env`에는 다음 범주의 값만 설정합니다.

- `SSH_HOST`, `SSH_USER`, `SSH_PORT`, `SSH_IDENTITY_FILE`
- `SSH_TUNNEL_BIND_HOST`
- `DB_TUNNEL_LOCAL_PORT`, `DB_TUNNEL_REMOTE_HOST`, `DB_TUNNEL_REMOTE_PORT`
- `REDIS_TUNNEL_LOCAL_PORT`, `REDIS_TUNNEL_REMOTE_HOST`, `REDIS_TUNNEL_REMOTE_PORT`

`SSH_HOST`는 인프라 담당자가 안내한 **Cloudflare SSH 공개 호스트명**으로 변경합니다.
예제의 `ssh.example.com`은 실제 접속 주소로 교체하며, `https://`·`ssh://`·포트는 붙이지 않습니다.
SSH 별칭을 쓰면 OpenSSH 설정의 HostName이 그 공개 호스트명을 가리켜야 합니다.
`SSH_USER`는 기존 서버의 SSH 사용자입니다. `SSH_PORT`는 별도 안내가 없으면 22로 유지하고,
원격 SSH 서비스 포트는 Cloudflare Tunnel의 서버 측 경로에서 설정합니다.

SSH 비밀번호는 파일이나 명령 인자에 저장하지 않고 실행 시 프롬프트에서 입력합니다.

### Backend 개발 설정

`backend/.env.development`의 `DB_HOST`와 `DB_PORT`는 PostgreSQL 터널의 로컬 접점과 일치해야
합니다. `REDIS_URL`도 Redis 터널의 로컬 접점을 사용합니다.

```dotenv
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=<DB_NAME>
DB_USER=<DB_USER>
DB_PASSWORD=<DB_PASSWORD>

# Redis 비밀번호 인증
REDIS_URL=redis://:<REDIS_PASSWORD>@127.0.0.1:6379/0

# Redis ACL 사용자 인증
# REDIS_URL=redis://<REDIS_USER>:<REDIS_PASSWORD>@127.0.0.1:6379/0
```

실제 계정과 비밀번호는 인프라 관리자에게 받아 로컬 파일에만 입력합니다.

개발 PostgreSQL 연결은 기본적으로 프로세스별 psycopg 풀을 사용합니다. 의존성을 `uv sync`로
갱신하고 백엔드를 재시작하면 적용됩니다. Django runserver의 요청 스레드 사이에서도 연결을
반납·재사용하며, SQLite 오프라인 모드에는 적용하지 않습니다.

| backend 개발 환경변수 | 기본값 | 의미 |
| --- | --- | --- |
| `DB_POOL_ENABLED` | `true` | 개발 PostgreSQL 연결 풀 사용. `false`로 비활성화 가능 |
| `DB_POOL_MIN_SIZE` | `0` | 최소 유지 연결 수. 사용 전 접속을 만들지 않음 |
| `DB_POOL_MAX_SIZE` | `4` | 프로세스별 최대 연결 수 |
| `DB_POOL_TIMEOUT` | `15` | 풀 연결 획득 대기 상한(초) |
| `DB_CONNECT_TIMEOUT` | `10` | PostgreSQL 개별 접속 제한시간(초) |
| `HEALTH_CHECK_TIMEOUT_SECONDS` | `10.0` | 개발 Redis 상태 점검의 접속·응답 대기 제한(각각 초) |

SSH 경유 최초 접속이 4초 이상 걸릴 수 있어 개별 접속 10초·풀 대여 15초의 여유를 둡니다.
풀 대여는 SQL 실행 전체나 프론트 API 제한시간을 뜻하지 않습니다.
Redis 상태 점검도 SSH 최초 연결을 기다리도록 개발 기본값을 10초로 둡니다. 기존 로컬 설정에
`HEALTH_CHECK_TIMEOUT_SECONDS=1.0`이 있으면 `10.0`으로 변경하고 서버를 재시작하세요.
이 값은 점검 API 전체 제한시간이 아니며, 운영 기본값과 업무 API 제한시간은 별도입니다.

풀은 `CONN_MAX_AGE=0`으로 요청 종료 시 연결을 반환하고, 다음 대여 시 연결 검사를 합니다.
유휴 연결은 60초 후 축소하며 프로세스를 종료하면 풀도 종료됩니다. 개발 서버·터미널을 여러 개
띄우면 각각 별도 풀이므로 전체 연결 예산은 프로세스 수 × 최대 연결 수로 확인하세요.
터널 연결 거부는 풀로 해결되지 않으며 기존 SSH 터널부터 복구해야 합니다. 운영 Gunicorn은
기존 `DB_CONN_MAX_AGE=60`·연결 검사 설정을 유지하고 이 개발 풀 환경변수는 사용하지 않습니다.
실측·쿼리 감소 결과는 [성능 보완 보고서](docs/reports/2026-10-29_database-query-improvements.md)를 참고하세요.


### 업무 기준 목록 캐시

직급·역할 코드·부서 표시 목록·활성 휴가 유형은 기존 Redis 또는 ElastiCache Valkey에
캐시합니다. 운영은 기본 활성화, 개발은 기본 비활성화입니다. 개발에서 사용하려면 backend
환경변수에 `REFERENCE_CACHE_ENABLED=true`를 설정하고 서버를 재시작합니다.

| 환경변수 | 기본값 | 용도 |
| --- | --- | --- |
| `REFERENCE_CACHE_ENABLED` | 개발 `false`, 운영 `true` | 기준 목록 캐시 사용 |
| `REFERENCE_CACHE_TTL` | `180` | 목록 유지 시간, 1~300초 |
| `REFERENCE_CACHE_TIMEOUT` | `0.2` | Redis 연결·읽기 각각의 제한시간, 0초 초과~1초 |
| `REFERENCE_CACHE_URL` | `REDIS_URL` 값 | 별도 캐시 접점, TLS는 `rediss://` |
| `REFERENCE_CACHE_KEY_PREFIX` | `erp:<환경>:reference:v1` | 동일 Redis를 사용하는 배포별 키 구분 |

ORM 저장·삭제 후 트랜잭션 커밋 시 해당 목록을 무효화합니다. 캐시 장애 시 DB 조회로 대체하고
5초 동안 캐시 읽기를 생략합니다. 자동 재시도는 없지만 한 요청에 여러 캐시 명령이 있으므로
제한시간은 요청 전체의 제한이 아닙니다. 역할 부여·권한 판정·재직 확인·휴가 잔여·신청·승인·급여는
최신 DB를 사용합니다. 세션 저장 방식도 유지합니다.

외부 SQL·bulk update는 신호를 거치지 않으므로 목록에 최대 TTL만큼 이전 표시가 남을 수
있습니다. 무효화 도중 Redis가 끊겨도 동일한 제한이 있습니다. 운영 연결 및 명령 권한은
[캐시 적용 보고서](docs/reports/2026-10-29_reference-cache.md)를 참고하세요.

### 실제 데이터 연동과 세션 인증

실제 사원·부서 데이터와 이메일 세션 인증을 사용하는 기본 개발 조합입니다.

```dotenv
# backend/.env.development
VACATION_INTEGRATION_MODE=database

# frontend/.env.development
VITE_AUTH_MODE=session
```

로컬 고정 사원 데이터와 `X-Employee-No`를 사용하는 조합은 개발 전용입니다.

```dotenv
VACATION_INTEGRATION_MODE=development
VITE_AUTH_MODE=development
```

## 4. 의존성 설치

환경 파일 구성과 별개로 Backend와 Frontend 의존성을 각각 설치합니다.

### Backend

```bash
cd backend
uv sync
cd ..
```

### Frontend

```bash
cd frontend
bun install --frozen-lockfile
cd ..
```

다른 OS나 CPU에서 생성한 `.venv`와 `node_modules`를 복사하지 말고 각 개발 PC에서 설치합니다.

## 5. 개발환경 실행

SSH 터널을 먼저 연 뒤 통합 개발 스크립트로 Backend, Frontend와 nginx를 함께 실행하는 방식을
기본으로 사용합니다.

### 5.1 SSH 터널

스크립트는 [Cloudflare 공식 SSH 연결 방식](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/use-cases/ssh/ssh-cloudflared-authentication/)에 따라
OpenSSH에 `ProxyCommand=cloudflared access ssh --hostname %h`를 전달합니다.
별도로 로컬 cloudflared TCP 포트를 띄우거나 사용자 SSH 설정에 ProxyCommand를 추가할 필요는 없습니다.
최초 연결이나 Access 세션 만료 시 브라우저에서 조직의 Cloudflare Access 인증을 완료한 뒤,
기존 SSH 키 또는 SSH 비밀번호로 서버 인증을 진행합니다. Access 인증은 서버 SSH 인증을 대체하지 않습니다.


macOS/Linux:

```bash
./scripts/ssh-tunnel.sh
```

Windows PowerShell:

```powershell
.\scripts\ssh-tunnel.ps1
```

연결이 반복 종료될 때는 `./scripts/ssh-tunnel.sh --diagnostic` 또는
`.\scripts\ssh-tunnel.ps1 -Diagnostic`으로 실행하면 사용자 임시 디렉터리에 SSH 상세 로그를
남깁니다. 로그 경로는 시작 시 표시되며 현재 연결에는 소급 적용되지 않습니다. 로그에는
호스트·사용자·키 경로 등의 접속 메타데이터가 포함되므로 공유할 때 가리고 저장소에는 추가하지 않습니다.
SSH 키/비밀번호 입력 방식은 동일하며 자동 재접속하거나 서버 설정을 바꾸지 않습니다.

터널은 PostgreSQL을 기본 `127.0.0.1:5432`, Redis를 기본 `127.0.0.1:6379`에 연결합니다.
포트를 변경하면 루트 터널 설정과 Backend 접속 설정을 함께 변경해야 합니다. 터널을 종료하려면
해당 터미널에서 `Ctrl+C`를 누릅니다.

다른 터널 환경 파일을 사용하려면 경로를 명시합니다.

```bash
./scripts/ssh-tunnel.sh <TUNNEL_ENV_FILE>
```

```powershell
.\scripts\ssh-tunnel.ps1 -EnvFile <TUNNEL_ENV_FILE>
```

[Cloudflared 전환·검증 기록](docs/reports/2026-10-22_cloudflared-ssh-tunnel.md)을 참고합니다.

### 5.2 통합 개발환경 실행

SSH 터널을 별도 터미널에서 먼저 실행한 뒤, Backend·Frontend·nginx를 한 번에 시작할 수 있다.

```bash
./scripts/start-dev.sh
```

Windows PowerShell:

```powershell
.\scripts\start-dev.ps1
```

nginx가 단일 개발 진입점 `http://localhost:8080`을 제공한다.

- `/api/`, `/admin/`, `/static/` → Django `127.0.0.1:8000`
- 그 외 경로와 Vite HMR WebSocket → Vite `127.0.0.1:5173`

스크립트는 세 프로세스 중 하나가 종료되거나 `Ctrl+C`를 받으면 나머지 프로세스도 종료한다.
Django는 자식 프로세스가 남지 않도록 `--noreload`로 실행되므로 Backend Python 파일을 변경한
뒤에는 통합 스크립트를 다시 시작해야 한다. Vite HMR은 계속 사용할 수 있다.

도구와 nginx 설정만 검사하려면 다음 명령을 사용한다.

```bash
./scripts/start-dev.sh --check
```

```powershell
.\scripts\start-dev.ps1 -Check
```

기본 포트를 임시로 변경할 수 있다.

```bash
ERP_DEV_NGINX_PORT=8081 \
ERP_DEV_BACKEND_PORT=8001 \
ERP_DEV_FRONTEND_PORT=5174 \
./scripts/start-dev.sh
```

```powershell
$env:ERP_DEV_NGINX_PORT = "8081"
$env:ERP_DEV_BACKEND_PORT = "8001"
$env:ERP_DEV_FRONTEND_PORT = "5174"
.\scripts\start-dev.ps1
```

이 변수들은 실행 프로세스에만 적용하며 `.env`에 저장할 필요가 없다. Backend는 기존
`backend/.env.development`, Frontend는 기존 `frontend/.env.development`를 그대로 사용한다.

### 5.3 Backend·Frontend 개별 실행

한쪽 애플리케이션만 개발하거나 통합 스크립트 문제를 진단할 때는 프로세스를 개별 실행할 수
있습니다. 일반 개발과 세션·CSRF 검증에는 앞의 nginx 통합 실행을 우선 사용합니다.

Backend:

```bash
cd backend
uv run python manage.py runserver
```

개발 명령은 기본적으로 `config.settings.development`와 `backend/.env.development`를 사용합니다.
Django가 시작 단계에서 migration 상태를 조회하므로 PostgreSQL 터널과 올바른 DB 인증정보가
필요합니다.

Frontend:

```bash
cd frontend
bun run dev
```

Vite는 `/api` 요청을 `http://127.0.0.1:8000`으로 프록시합니다.

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Health check: `http://localhost:8000/api/health/`
- Django admin: `http://localhost:8000/admin/`

## 6. 연결 상태와 오프라인 개발

`GET /api/health/`는 Backend, PostgreSQL, Redis, Workforce와 전체 E2E 상태를 반환합니다.
운영 진단 API로 유지하며 프론트엔드는 이를 폴링하지 않습니다. 업무 화면은 각 API의
성공·실패를 기준으로 표시하며 별도 연결 상태 UI로 입력을 차단하지 않습니다.

Redis health check는 `REDIS_URL`의 ACL 사용자·비밀번호·TLS·DB 설정으로 실제 `PING` 명령을
실행합니다. TCP 터널만 열려 있거나 인증에 실패하거나 제한시간 안에 응답하지 않으면 Redis를
`disconnected`로 보고하며 전체 E2E 상태도 연결 실패로 처리합니다.

### Backend 오프라인 모드

PostgreSQL과 Redis 없이 Backend 상태 API를 실행하려면 다음 값을 사용합니다.

```dotenv
DEVELOPMENT_OFFLINE_MODE=true
```

이 모드는 개발 settings에서만 동작하며 SQLite를 사용합니다. 초기 SQLite에는 migration이
적용되어 있지 않으므로 상태 확인과 연결 실패 시뮬레이션 용도로 사용합니다.

공통 컴포넌트 전시·연결 상태 화면과 개발 오프라인 제어는 배포 준비 과정에서 제거했습니다.
운영 빌드에서는 개발용 사원 선택도 비활성화됩니다.

## 7. 인증과 업무 모듈

### 사원·부서·인증

기존 PostgreSQL의 `persons`, `employees`, `departments`, `positions`, `emp_history`, `roles`,
`employee_roles`를 `workforce` 앱이 매핑합니다. 로그인 ID는 이메일이며 인증 상태는 JWT 대신
Django 서버 세션과 HttpOnly 쿠키로 관리합니다.

- 인증 API: `/api/auth/csrf/`, `/api/auth/login/`, `/api/auth/logout/`, `/api/auth/me/`
- 계정 관리 API: `/api/auth/accounts/`
- 사원·부서 API: `/api/workforce/`
- 인사 관리 권한: 활성 `HR_MANAGER` 또는 슈퍼유저
- 휴가 fallback 승인자: 단일 활성 `HR_LEAVE_APPROVER`

### 휴가

휴가 모듈은 신청, 취소, 승인, 반려, 승인 회수, 수정·재신청과 상태 이력을 제공합니다. 재직 중인
소속 부서장이 1차 승인자이며, 부서장이 없거나 신청자 본인이 부서장이면 인사 승인담당자를
사용합니다.

### 기여 문서 부분 통합 모듈

본인 인사정보·개인정보 수정 요청, 게시글 작성·조회·수정·삭제, 인사평가 작성·등급·확정·본인 결과 조회,
급여 생성·항목 수정·확정·정정·조회에 대한 기존 명세를 공용 문서에 통합했습니다.
기본 API 경로는 `/api/workforce/`, `/api/board/`, `/api/evaluations/`, `/api/payroll/`입니다.
코드는 추가 정책과 미해결 연동 문제를 포함하므로 전체 기능의 명세 준수·배포 완료를 뜻하지 않습니다.
화면은 이전에 결정한 디자인 시안을 기준으로 재설계하며 기존 배치를 공용 기준으로 채택하지 않습니다.

[API 명세](docs/specs/notion/06-api-specification.md),
[테이블 명세](docs/specs/notion/08-table-specification.md),
[모듈 담당자 의제](docs/reports/2026-10-12_module-review-agenda.md),
[통합 보고서](docs/reports/2026-10-12_contribution-docs-integration.md)를 확인합니다.

## 8. Migration과 공유 DB 안전수칙

기존 인사·휴가 테이블의 Django state migration과 신규 계정·세션·휴가 잔여일수 migration이
포함되어 있습니다. 신규 테이블이 적용되지 않은 환경에서는 이메일 로그인과 서버 세션 기능을
사용할 수 없습니다.

공유 DB에는 `migrate`, seed, 데이터 수정 명령을 자동 실행하지 않습니다. 다음 절차를 따릅니다.

1. 대상 환경과 사용 권한을 확인합니다.
2. 기존 스키마, 중복 이메일과 orphan 데이터를 읽기 전용으로 점검합니다.
3. 별도 staging DB에서 migration을 리허설합니다.
4. migration SQL과 영향 범위를 검토합니다.
5. 인프라 관리자와 사용자 승인을 받은 후 적용합니다.

모델을 변경한 경우 migration 파일 생성까지만 수행할 수 있습니다.

```bash
cd backend
uv run python manage.py makemigrations
```

## 9. 검증 명령

Backend:

```bash
cd backend
uv run python manage.py check
uv run ruff check .
```

Frontend:

```bash
cd frontend
bun run lint
bun run build
bun run test
```

기능 변경 시 가장 좁은 관련 테스트부터 실행하고 완료 전 영향받는 전체 테스트를 확인합니다.

## 10. 운영 환경

운영 환경 파일은 예제를 직접 배포하는 대신 배포 플랫폼의 secret/configuration 시스템으로
주입합니다. Backend 관리 명령에는 운영 settings를 명시합니다.

```bash
cd backend
DJANGO_SETTINGS_MODULE=config.settings.production uv run python manage.py check --deploy
```

Frontend production build:

```bash
cd frontend
bun install --frozen-lockfile
bun run build
```

ASGI와 WSGI 진입점은 운영 settings를 기본으로 사용합니다. 운영 배포는 **Docker rootless + Compose**의
backend·nginx 두 컨테이너를 사용합니다. Cloudflare Tunnel은 호스트 loopback 8080으로 연결하고,
backend는 Compose 내부에서만 접근합니다. 로컬 개발 명령과 SSH 터널은 기존 방식을 유지합니다.
[Ubuntu EC2·빈 RDS 배포 가이드](docs/guides/ec2-rds-deployment.md)를 따릅니다.
GitHub Actions·Secrets Manager와 운영 .env 전달 없는 경로를 준비할 때는
[빈 Ubuntu 26.04.1 서버 준비 안내](docs/guides/github-actions-aws-deployment.md)를 먼저 확인합니다.
현재 아래 명령은 기존 서버 환경 파일·서버 빌드 경로이며 Actions/Secret 주입 자동화는 아직 없습니다.

```bash
./scripts/prepare-production.sh /home/erp/.config/erp/compose.env --check
./scripts/prepare-production.sh /home/erp/.config/erp/compose.env
```

Compose 2.30 이상이 필요합니다. deploy/compose.env.example과 backend/.env.production.example을
참고해 서버에서 환경 파일을 준비합니다. 첫 명령은 daemon 없이 Compose 구성을 검사하고, 두 번째는
rootless daemon에서 이미지 빌드·일회성 Django/nginx 검사를 수행합니다. migration·서비스 시작은
자동 실행하지 않습니다. 빈 RDS는 legacy state-only migration 때문에 baseline 스키마 이관이 먼저입니다.

운영 설정의 `DJANGO_CSRF_TRUSTED_ORIGINS`는 실제 HTTPS origin,
`DJANGO_SECURE_HSTS_SECONDS`는 기본 3600초입니다. `DB_SSLMODE`는 기본 verify-full,
`DB_CONNECT_TIMEOUT`은 기본 5초입니다. Compose가 호스트 RDS CA 파일을 읽기 전용 마운트하고
`DB_SSLROOTCERT=/run/rds/ca.pem`으로 설정합니다. Django 정적 파일과 frontend 빌드는 nginx 이미지에
포함합니다. nginx는 X-Forwarded-Proto를 덮어쓰고 backend 포트는 호스트에 공개하지 않습니다.

## 보안 원칙

- 실제 환경 파일, 비밀번호, SSH 개인 키, 접근 토큰과 DB dump를 커밋하지 않습니다.
- SSH 비밀번호를 파일, 스크립트 또는 명령 인자에 저장하지 않습니다.
- 브라우저에 포함되는 `VITE_` 변수에는 민감정보를 넣지 않습니다.
- 운영 세션 쿠키는 Secure와 HttpOnly 정책을 유지합니다.
- 공유 PostgreSQL과 Redis는 승인 없는 초기화, migration, flush 또는 seed를 금지합니다.
