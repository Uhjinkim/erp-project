# ERP Project

사원·부서·인증과 휴가 신청·승인 업무를 제공하는 ERP 애플리케이션입니다. Backend와 Frontend는
개발 PC에서 실행하고 PostgreSQL과 Redis는 팀이 관리하는 원격 인프라를 사용합니다. 로컬
애플리케이션은 SSH 로컬 포워딩으로만 원격 서비스에 접근하며, 저장소에는 로컬 컨테이너 실행
구성이 없습니다.

## 프로젝트 개요

### 기술 구성

- Backend: Python 3.13, Django 5.2 LTS, Django REST Framework, uv
- Frontend: React 19, TypeScript, Vite, Bun 1.4
- Infrastructure: 원격 PostgreSQL 및 Redis, OpenSSH 로컬 포워딩, 로컬 개발용 nginx
- Authentication: 이메일 로그인, Django 서버 세션, HttpOnly 쿠키, CSRF 보호

### 주요 기능

- 사원, 인적사항, 부서, 직급과 역할 조회·관리
- 이메일 기반 로그인과 서버 세션 인증
- 휴가 신청, 취소, 승인, 반려, 승인 회수와 상태 이력
- 부서장 우선 승인 및 부서장 부재 시 인사 승인담당자 fallback
- Backend, PostgreSQL, Redis와 사원 연동 상태 확인
- 개발환경 전용 오프라인 시뮬레이션과 연결 상태 표시

### 저장소 구조

```text
erp-project/
├── backend/                 Django API와 도메인 모듈
│   ├── accounts/            이메일 로그인과 세션 인증
│   ├── workforce/           사원·부서·직급·역할
│   ├── vacation/            휴가 신청·승인
│   └── config/              환경별 Django 설정과 health check
├── frontend/                React 애플리케이션
├── nginx/                   로컬 개발 reverse proxy 설정 템플릿
├── scripts/                 SSH 터널과 통합 개발환경 실행 스크립트
├── docs/                    작업 보고서와 설계 기록
└── .env.example             SSH 터널 환경변수 예제
```

Python과 Frontend 의존성은 각각의 디렉터리와 lockfile로 관리합니다. `.venv`, `node_modules`,
빌드 결과물, 실제 환경 파일과 자격증명은 Git에 포함하지 않습니다.

## 1. 필수 도구

개발 PC에 다음 도구가 필요합니다.

- Git
- Python 3.13과 uv
- Bun 1.4
- OpenSSH 클라이언트
- nginx

Podman, Docker 또는 로컬 PostgreSQL·Redis는 필요하지 않습니다.

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

실제 계정과 비밀번호는 인프라 관리자에게 받아 로컬 파일에만 입력합니다. Redis 관리 도구의 key
separator는 `:`, ERP key filter는 `erp:*`를 사용합니다. 실제 키에는 wildcard를 넣지 않고
`erp:dev:<module>:<identifier>`처럼 환경과 모듈을 구분합니다.

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

SSH 터널, Backend, Frontend를 각각 별도 터미널에서 실행합니다.

### 5.1 SSH 터널

macOS/Linux:

```bash
./scripts/ssh-tunnel.sh
```

Windows PowerShell:

```powershell
.\scripts\ssh-tunnel.ps1
```

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

### 5.2 Backend

```bash
cd backend
uv run python manage.py runserver
```

개발 명령은 기본적으로 `config.settings.development`와 `backend/.env.development`를 사용합니다.
Django가 시작 단계에서 migration 상태를 조회하므로 PostgreSQL 터널과 올바른 DB 인증정보가
필요합니다.

### 5.3 Frontend

```bash
cd frontend
bun run dev
```

Vite는 `/api` 요청을 `http://127.0.0.1:8000`으로 프록시합니다.

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Health check: `http://localhost:8000/api/health/`
- Django admin: `http://localhost:8000/admin/`

### 5.4 nginx 통합 개발환경

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
직접 Vite `5173` 또는 Django `8000`에 접속하는 방식도 계속 지원하지만, 세션·CSRF와 실제
same-origin 흐름을 확인할 때는 nginx `8080` 주소를 사용한다.

## 6. 연결 상태와 오프라인 개발

`GET /api/health/`는 Backend, PostgreSQL, Redis, Workforce와 전체 E2E 상태를 반환합니다.
Frontend는 전체 연결이 정상이 아닐 때 `오프라인 / 미연결` 상태를 표시하고 업무 입력을
비활성화합니다.

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

### Frontend 오프라인 시뮬레이션

개발 화면의 `오프라인 테스트` 제어를 사용하거나 다음 값으로 초기 상태를 지정합니다.

```dotenv
VITE_ENABLE_CONNECTION_TEST_CONTROLS=true
VITE_DEV_OFFLINE_MODE=true
```

운영 빌드에서는 개발용 사용자 선택과 오프라인 테스트 제어가 비활성화됩니다.

## 7. 인증과 업무 모듈

### 사원·부서·인증

기존 PostgreSQL의 `persons`, `employees`, `departments`, `positions`, `emp_history`, `roles`,
`employee_roles`를 `workforce` 앱이 매핑합니다. 로그인 ID는 이메일이며 인증 상태는 JWT 대신
Django 서버 세션과 HttpOnly 쿠키로 관리합니다.

- 인증 API: `/api/auth/csrf/`, `/api/auth/login/`, `/api/auth/logout/`, `/api/auth/me/`
- 계정 관리 API: `/api/auth/accounts/`
- 사원·부서 API: `/api/workforce/`
- 인사 관리 권한: 활성 `HR_MANAGER`
- 휴가 fallback 승인자: 단일 활성 `HR_LEAVE_APPROVER`

### 휴가

휴가 모듈은 신청, 취소, 승인, 반려, 승인 회수, 수정·재신청과 상태 이력을 제공합니다. 재직 중인
소속 부서장이 1차 승인자이며, 부서장이 없거나 신청자 본인이 부서장이면 인사 승인담당자를
사용합니다.

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

ASGI와 WSGI 진입점은 운영 settings를 기본으로 사용합니다. 배포 이미지, 도메인, TLS, reverse
proxy와 Cloudflare Tunnel 구성은 인프라 정책이 확정된 뒤 별도로 관리합니다.

## Notion MCP 연결

프로젝트의 `.codex/config.toml`에 공식 Notion MCP 서버가 등록되어 있습니다. 설정 파일에는
토큰이나 워크스페이스 정보가 없으며, 각 사용자가 자신의 Notion 권한으로 OAuth 인증해야 합니다.

```bash
codex mcp login notion
```

인증을 마친 뒤 Codex 앱 또는 IDE 확장을 재시작하고 MCP 서버 목록에서 `notion` 연결을
확인합니다. 읽기 도구는 자동 실행할 수 있지만 Notion 내용을 생성하거나 변경하는 도구는 사용자
승인을 요구하도록 설정되어 있습니다. 프로젝트별 MCP 설정은 신뢰한 저장소에서만 활성화합니다.

## 보안 원칙

- 실제 환경 파일, 비밀번호, SSH 개인 키, 접근 토큰과 DB dump를 커밋하지 않습니다.
- SSH 비밀번호를 파일, 스크립트 또는 명령 인자에 저장하지 않습니다.
- 브라우저에 포함되는 `VITE_` 변수에는 민감정보를 넣지 않습니다.
- 운영 세션 쿠키는 Secure와 HttpOnly 정책을 유지합니다.
- 공유 PostgreSQL과 Redis는 승인 없는 초기화, migration, flush 또는 seed를 금지합니다.
