# ERP Project

애플리케이션은 개발 PC에서 실행하고 PostgreSQL과 Redis는 원격 개발 서버의 Podman 컨테이너로 실행하는 개발 환경입니다. 개발 PC는 SSH 로컬 포워딩을 통해 인프라에 접속합니다.

## 표준 도구

- Backend: Python 3.13, Django 5.2 LTS, uv
- Frontend: Bun 1.4, React, TypeScript, Vite
- Infrastructure: 원격 서버의 PostgreSQL 17, Redis 7, Podman Compose

`.venv`, `node_modules`, 컨테이너 볼륨은 OS/CPU별 또는 서버별 로컬 생성물이므로 Git으로 공유하지 않습니다. Python 의존성은 `pyproject.toml`과 `uv.lock`, Frontend 의존성은 `package.json`과 `bun.lock`, DB 스키마는 Django migration으로 공유합니다.

## 처음 시작하기

개발 PC 필수 도구: Git, uv, Bun, OpenSSH 클라이언트. Podman 및 Podman Compose는 원격 개발 인프라 서버에 설치합니다.

```bash
git clone <REPOSITORY_URL>
cd <PROJECT_DIR>
cp .env.example .env
```

`.env`에서 원격 서버 주소, SSH 사용자, DB 비밀번호를 실제 개발 환경 값으로 바꿉니다. DB 비밀번호는 원격 서버에서 Compose를 시작할 때 사용한 값과 같아야 합니다.

### 1. 원격 서버에서 인프라 실행

원격 서버에 저장소와 `.env`를 준비한 뒤 실행합니다.

```bash
podman compose -f compose.dev.yml up -d
podman compose -f compose.dev.yml ps
```

PostgreSQL과 Redis 포트는 원격 서버의 `127.0.0.1`에만 바인딩되므로 외부에 직접 공개되지 않습니다.

### 2. 개발 PC에서 SSH 터널 실행

macOS Terminal 또는 Windows PowerShell에서 다음 명령을 실행한 채로 둡니다.

```bash
ssh -N \
  -o ExitOnForwardFailure=yes \
  -L 5432:127.0.0.1:5432 \
  -L 6379:127.0.0.1:6379 \
  <SSH_USER>@<SSH_HOST>
```

SSH 계정 비밀번호는 명령 실행 후 프롬프트에서 입력합니다. 비밀번호를 `.env`, 명령 인자, 스크립트 또는 Git에 저장하지 않습니다. Windows에서도 기본 제공 OpenSSH 클라이언트를 사용하면 같은 명령을 한 줄로 실행할 수 있습니다.

터널이 연결된 동안 Django는 `.env`의 `DB_HOST=localhost`, `DB_PORT=5432`, `REDIS_URL=redis://localhost:6379/0`을 그대로 사용합니다.

### 3. Backend 실행

별도 터미널에서 실행합니다.

```bash
cd backend
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

### 4. Frontend 실행

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

## 자주 사용하는 명령

```bash
# 원격 인프라 서버에서 상태 및 로그 확인
podman compose -f compose.dev.yml ps
podman compose -f compose.dev.yml logs -f

# 원격 인프라 종료 (데이터 유지)
podman compose -f compose.dev.yml down

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

컨테이너 데이터까지 삭제해야 할 때만 원격 서버에서 `podman compose -f compose.dev.yml down -v`를 사용합니다. 이 명령은 팀이 공유하는 개발 DB와 Redis 데이터를 삭제하므로 반드시 팀과 합의한 뒤 실행합니다.

## 환경 변수

`.env.example`을 `.env`로 복사하고 실제 값을 설정합니다. `.env`는 Git에서 제외됩니다. 개발 PC의 Django와 원격 서버의 Compose가 동일한 DB 접속 정보를 사용해야 합니다. SSH 비밀번호는 이 파일에 넣지 않습니다.

기본 Django 설정은 로컬 개발을 위한 단일 설정입니다. 운영 환경을 만들 때는 secret을 환경에서 주입하고 settings 모듈을 개발/운영으로 분리합니다.

## 플랫폼 호환성

개발용 Compose에는 `platform`을 강제하지 않습니다. 공식 멀티아키텍처 이미지가 원격 서버 아키텍처에 맞는 이미지를 선택합니다. 각 개발 PC에서 `uv sync`와 `bun install --frozen-lockfile`을 실행하고 `.venv`나 `node_modules`를 다른 플랫폼으로 복사하지 않습니다.

Windows에서는 PowerShell의 `Copy-Item .env.example .env`를 사용해 환경 파일을 만들 수 있습니다.

## 배포 환경 후속 작업

배포용 `compose.yml`, Django/Frontend Containerfile, Nginx, cloudflared 구성은 배포 도메인과 이미지 빌드·배포 방식이 확정된 후 추가합니다. 최종 배포 이미지는 `linux/amd64` 기준으로 x64 서버 또는 CI에서 빌드합니다.

함께 확정할 항목:

- Redis를 사용하는 기능과 캐시/큐 구성
- Django 개발/운영 settings 분리
- 배포 이미지 저장소, 도메인, TLS 및 Cloudflare Tunnel 구성
- 공통 초기 데이터의 fixture 또는 seed 명령 정책
