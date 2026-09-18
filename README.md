# ERP Project

애플리케이션은 개발 PC에서 실행하고, PostgreSQL과 Redis는 팀에서 제공하는 원격 개발 인프라를 사용합니다. 개발자는 서버 셸이나 컨테이너 제어 권한 없이 SSH 로컬 포워딩으로만 인프라에 접속합니다.

## 표준 도구

- Backend: Python 3.13, Django 5.2 LTS, uv
- Frontend: Bun 1.4, React, TypeScript, Vite
- Infrastructure: 팀 제공 원격 PostgreSQL 및 Redis

`.venv`, `node_modules`, 컨테이너 볼륨은 OS/CPU별 또는 서버별 로컬 생성물이므로 Git으로 공유하지 않습니다. Python 의존성은 `pyproject.toml`과 `uv.lock`, Frontend 의존성은 `package.json`과 `bun.lock`, DB 스키마는 Django migration으로 공유합니다.

## 처음 시작하기

개발 PC 필수 도구: Git, uv, Bun, OpenSSH 클라이언트. Podman이나 Podman Compose는 개발 PC에 필요하지 않습니다.

```bash
git clone <REPOSITORY_URL>
cd <PROJECT_DIR>
cp .env.example .env
```

`.env`에 팀에서 제공한 DB 이름, 사용자, 비밀번호를 설정합니다. SSH 서버 주소와 SSH 사용자 정보는 인프라 관리자에게 받습니다.

### 1. SSH 터널 실행

macOS Terminal 또는 Windows PowerShell에서 다음 명령을 실행한 채로 둡니다.

```bash
ssh -N \
  -o ExitOnForwardFailure=yes \
  -L 5432:127.0.0.1:5432 \
  -L 6379:127.0.0.1:6379 \
  <SSH_USER>@<SSH_HOST>
```

`<SSH_USER>`와 `<SSH_HOST>`는 인프라 관리자에게 받은 값으로 바꿉니다. SSH 계정 비밀번호는 명령 실행 후 프롬프트에서 입력합니다. 비밀번호를 `.env`, 명령 인자, 스크립트 또는 Git에 저장하지 않습니다. Windows에서도 기본 제공 OpenSSH 클라이언트를 사용하면 같은 명령을 한 줄로 실행할 수 있습니다.

터널이 연결된 동안 Django는 `.env`의 `DB_HOST=localhost`, `DB_PORT=5432`, `REDIS_URL=redis://localhost:6379/0`을 그대로 사용합니다. 인프라 관리자가 다른 포트를 안내하면 SSH 포워딩과 `.env`의 해당 포트를 함께 변경합니다.

### 2. Backend 실행

별도 터미널에서 실행합니다.

```bash
cd backend
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

`migrate`는 DB 스키마 변경 권한이 있는 계정에서만 실행합니다. 권한이 없는 계정이라면 인프라 관리자에게 migration 적용을 요청합니다.

### 3. Frontend 실행

```bash
cd frontend
bun install --frozen-lockfile
bun run dev
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Backend health check: http://localhost:8000/api/health/
- Django admin: http://localhost:8000/admin/

Vite는 개발 중 `/api` 요청을 Django의 8000번 포트로 프록시합니다.

## 휴가 신청 모듈

휴가 신청/승인 기능은 `backend/vacation/` 안에서 Domain → Application → Infrastructure →
Presentation 레이어로 분리되어 있습니다. Domain과 Application에는 Django 의존성이 없으며,
상태 변경과 이력 저장은 하나의 트랜잭션으로 처리합니다.

현재 사원·조직·인증 모듈이 아직 없으므로 계약 우선 개발 어댑터를 사용합니다.

- React 화면의 현재 사용자 선택 또는 `X-Employee-No` 요청 헤더로 개발용 사원을 선택합니다.
- 개발용 사원·승인선·잔여일수는 `backend/config/settings.py`의
  `VACATION_DEVELOPMENT_EMPLOYEES`에만 정의되어 있습니다.
- 사원 모듈이 준비되면 `WorkforceGateway`, `LeaveBalanceGateway` 구현과 요청 사용자 식별만
  실제 어댑터로 교체해야 합니다. 클라이언트가 보낸 사원번호를 운영 인증으로 사용하면 안 됩니다.

주요 API는 `/api/vacations/` 아래에 있으며 휴가 유형, 본인 신청, 승인 대상, 취소, 승인·반려,
승인 회수, 수정·재신청, 상태 이력 조회를 제공합니다.

모델 변경 migration은 생성되어 있지만 공유 DB에는 자동 적용하지 않습니다. 적용 전 대상 환경과
권한을 확인한 뒤 인프라 관리자와 협의하세요.

## 자주 사용하는 명령

```bash
# 모델 변경 후 migration 생성 및 적용
cd backend
uv run python manage.py makemigrations
uv run python manage.py migrate

# 검사
uv run python manage.py check
uv run ruff check .

cd ../frontend
bun run lint
bun run build
```

## 환경 변수

`.env.example`을 `.env`로 복사하고 팀에서 제공한 DB 접속 정보를 설정합니다. `.env`는 Git에서 제외됩니다. SSH 비밀번호는 이 파일에 넣지 않습니다.

기본 Django 설정은 로컬 개발을 위한 단일 설정입니다. 운영 환경을 만들 때는 secret을 환경에서 주입하고 settings 모듈을 개발/운영으로 분리합니다.

## 플랫폼 호환성

각 개발 PC에서 `uv sync`와 `bun install --frozen-lockfile`을 실행하고 `.venv`나 `node_modules`를 다른 플랫폼으로 복사하지 않습니다.

Windows에서는 PowerShell의 `Copy-Item .env.example .env`를 사용해 환경 파일을 만들 수 있습니다.

## 배포 환경 후속 작업

배포용 Compose, Django/Frontend Containerfile, Nginx, cloudflared 구성은 배포 도메인과 이미지 빌드·배포 방식이 확정된 후 인프라 관리자와 별도로 관리합니다. 최종 배포 이미지는 `linux/amd64` 기준으로 x64 서버 또는 CI에서 빌드합니다.

함께 확정할 항목:

- Redis를 사용하는 기능과 캐시/큐 구성
- Django 개발/운영 settings 분리
- 배포 이미지 저장소, 도메인, TLS 및 Cloudflare Tunnel 구성
- 공통 초기 데이터의 fixture 또는 seed 명령 정책
