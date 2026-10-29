# 기여 문서 확정 내용 통합 · EC2/RDS 배포 준비

- 작업일: 2026-10-28
- 기준: dev 5dc4415, 시작 작업 트리 clean
- 사용자 지정 범위: 확정 기여 내용의 공용 반영, 필요시 Notion 갱신, 배포 준비
- 확인된 인프라: Ubuntu EC2 인스턴스(내부 미설정), 빈 RDS
- 추가 사용자 지정: backend·nginx를 rootless Compose로 운영
- Notion: 연결 도구가 없어 이번 원문 조회·수정 없음. 기존 원문 확인일 유지.

## 공용 반영 결과

| 근거 | 확인한 구현·결정 | 공용 반영 |
| --- | --- | --- |
| workforce/jyoun·profile/jyoun, 2026-10-27 사용자 결정 | 연락처·주소도 승인 후 반영, 본인 PATCH 405, 수정 요청 5개 항목 | 02 HR-002·003·011·012, 03 FN-HR-002~005·011, 04 상세, 06 API, workforce 대응표 |
| workforce 0007·domain ApprovalRequiredValues | 연락처·주소 생략/null은 미수정, 빈 문자열은 미등록으로 지움, 계좌는 짝으로 제출 | 06 입력·응답, 08 실제 personal_info_change_requests 컬럼 표 |
| profile/workforce registration·routing | profile 4개 화면, my-profile 수정 모드, saved=request, workforce HR_MANAGER 역할 제한 | frontend 토대 계약·모듈 배정 가이드 |
| evaluation/bae 최신 기여·게이트웨이·UI | targets 일괄 조회, 오류 시 입력 유지, 본인 평가 HR 처리 버튼 숨김 | frontend 토대 계약의 현재 동작; EV 정책 보류 유지 |
| 기존 board/payroll/vacation 기여·2026-10-14 통합 | 기본 API·화면·보류 분류는 이미 공용 문서에 있음 | 기존 기록 유지, 추가 정책 승인으로 바꾸지 않음 |

기여 원본은 보존한다. HR-01 정본 테이블·HR-02 보호/보존·HR-03 특별 처리자/대기 제한,
BD-01~03·EV-01/02·PY-01/02·OPS-01 등 기존 의제를 자동 종결하지 않았다.
HR_MANAGER 없는 superuser 메뉴 차이와 처리함 노출도 미결이다.

## Notion 반영 대기 변경안

문서 담당자는 아래 원문에 저장소의 확정 변경을 반영하고 재조회한 날짜를 별도로 기록한다.
이 보고서는 원문 갱신 완료를 뜻하지 않는다.

- [비즈니스 규칙](https://app.notion.com/p/3d78eced448d81528023db7f8dd1b49a):
  HR-002는 연락처·주소·이메일·급여계좌를 모두 수정 요청으로 제출하고 인사관리자 승인 후 반영.
  HR-003·011은 개인정보 수정 요청 용어, HR-012는 수정 이력 및 연락처·주소 예시.
- [기능 명세](https://app.notion.com/p/3d78eced448d8118bd7ce952069417ed):
  FN-HR-002 내 정보 수정, 003 개인정보 수정 요청 제출, 004 개인정보 변경 승인·반려,
  005 개인정보 수정 요청 결과·이력 조회, 011 대기 개인정보 수정 요청 취소.
- [핵심 상세](https://app.notion.com/p/3d78eced448d81018ff7c3cf39e01776):
  FN-HR-002 동일 화면 수정 모드·취소·수정완료 흐름 추가, 003 진입을 수정완료로 변경.
- [API](https://app.notion.com/p/3e58eced448d81f4ade6c86fc337bd26):
  본인 PATCH 삭제(405), 수정 요청 phone/address 및 null/빈 문자열 의미, previous/requested 확장.
- [테이블 명세](https://app.notion.com/p/3d78eced448d8124b3b4d00cd2c0b5f3):
  구현 표에 0007의 previous/requested_phone(20), previous/requested_address(255) nullable 컬럼 추가.
  employee_change_requests 정본 교체는 HR-01 결정을 기다린다.
- [미확정 정책](https://app.notion.com/p/3d78eced448d81c0be0ff8f95b5ee9c3): 수정 요청 용어 정리.
  급여 지급일·추가 평가 워크플로 등 기존 보류는 이번에 확정하지 않는다.

## 배포 준비 결과

- Gunicorn 26.2.0을 uv로 추가하고 pyproject·lock 동시 갱신.
- 운영 설정에 HTTPS 프록시·리다이렉트, trusted origins, 호스트 범위 HSTS, STATIC_ROOT,
  RDS verify-full·CA·연결 제한시간·연결 건강 검사를 추가.
- HSTS includeSubDomains·preload는 미확인 다른 호스트까지 강제하지 않도록 비활성화하고
  해당 경고 W005·W021만 명시적으로 제외. 나머지 warning은 준비 명령 실패 처리.
- 최종 배포안은 Docker rootless + Compose backend·nginx 두 서비스다. 호스트 cloudflared가
  127.0.0.1:8080에 접근하고 backend는 Compose 내부에만 수신한다. 기존 호스트 nginx용 템플릿은
  대안 자료로만 유지한다. systemd unit은 사용자 unit으로 변경했다.
- 멀티스테이지 Dockerfile은 uv·Python·Bun·Node·nginx base image를 확인한 manifest digest로 고정하고,
  비밀 없이 Django static과 frontend를 빌드한다. .dockerignore로 비밀·로컬 산출물을 제외한다.
- 컨테이너 내부도 비root, read-only rootfs·tmpfs·cap_drop ALL·no-new-privileges를 사용한다.
  RDS CA는 읽기 전용 마운트, backend 비밀은 raw env_file로 주입하며 config 출력은 하지 않는다.
- 준비 스크립트는 --check에서 daemon 없이 Compose config --quiet, 기본 실행에서 rootless 확인 후
  이미지 빌드·일회성 운영 Django/nginx 검사를 한다. migration·서비스 시작은 자동 실행하지 않는다.
- [배포 가이드](../guides/ec2-rds-deployment.md)에 스키마 이관·기준정보·migration 이력 대조,
  staging·승인·활성화·검수·롤백 순서를 기록. backend README의 급여 legacy 부재 오기 수정.

빈 RDS에는 legacy baseline이 없어 migrate만으로 배포할 수 없다. 승인된 스키마 전용 백업과
migration 이력·기준정보를 확보해야 한다. 스키마 전용 백업에는 migration 행과 기준정보가 없으며
일괄 fake나 기존 개인정보/급여 테스트 데이터를 복사하는 방식으로 해결하지 않는다.

## 검증

- backend pytest: 504 passed(SQLite·fake, 새 운영 프록시/쿠키 설정 테스트 포함).
- backend Ruff 및 Django check(test settings): 통과.
- migration drift: test settings의 SQLite를 사용하되 MIGRATION_MODULES를 빈 dict로 재설정해
  실제 전체 migration 그래프를 로드한 makemigrations check/dry-run, No changes detected.
- frontend test: 53 passed; lint·production build 통과.
- 최종 운영 준비 --check: 임시 Compose/backend 환경 파일로 daemon 없이 통과.
- 컨테이너용 nginx 템플릿: 로컬 nginx -t 통과, 잘못된 도메인 입력 거절 확인.
- base image 다섯 개의 registry manifest 조회·digest 확인 완료(컨테이너 실행 아님).
- rootless 전환 후 운영 설정 회귀 테스트 1개 및 Ruff 재검사 통과.
- Gunicorn 운영 WSGI·서비스 실행 인자: --check-config 통과(외부 연결 없음).
- nginx production 두 템플릿: 임시 self-signed 검사 인증서로 nginx -t 통과(인증서 배포 아님).
- start-dev.sh --check 및 start-dev/docs-workflow/prepare-production bash 문법 검사 통과.
- 문서 상대 링크·git diff --check 검사 통과.
- dev에서 승인된 공용 문서 유지보수이므로 feature 전용 docs scope check는 적용하지 않음.

## 남은 작업과 제한

EC2 접속 alias·Ubuntu 버전/아키텍처, 공개 도메인·Cloudflare 권한, RDS private endpoint/DB명·권한,
Redis 배치, baseline schema 제공 경로를 확인해야 실제 서버 설치와 staging 검증을 진행할 수 있다.
Docker Desktop 시작 후 linux/arm64 이미지 빌드·컨테이너 검증은 아래 추가 기록처럼 통과했다.
Desktop daemon은 rootless가 아니므로 Ubuntu rootless daemon 검증을 대신하지 않는다.
Podman 대체 실행은 하지 않았다. EC2의 운영 준비 스크립트 전체 실행,
rootless 네트워크·사용자 namespace에서의 CA 읽기·DNS, 사용자 systemd/재부팅 복구, 터널·RDS TLS 연결,
PostgreSQL baseline 복원 및 migration 리허설, 실제 브라우저 세션은 검증하지 않았다.
공유 PostgreSQL·Redis·RDS에 접속/쓰기/migration/seed를 수행하지 않았다.

## Docker 시작 후 실제 이미지·컨테이너 검증

- 환경: Docker Desktop Linux/aarch64, Compose 5.6.1. daemon SecurityOptions에는 rootless 없음.
- deploy/compose.production.yml로 backend·nginx 두 이미지를 빌드했다. frontend frozen install·build와
  Django static 154개 수집까지 성공했다. 태그는 erp-backend:local-validation,
  erp-nginx:local-validation이다. Ubuntu EC2/amd64 빌드는 검증하지 않았다.
- production settings로 일회성 backend `check --deploy --fail-level WARNING` 통과(명시한 HSTS
  경고 2종만 제외). nginx 일회성 컨테이너 문법 검사도 준비 스크립트와 같은 명령으로 통과했다.
- 실제 서비스 검증은 별도 erp-validation 프로젝트·임의 loopback 포트·dummy 환경 파일을 사용했다.
  임시 settings는 production을 상속하되 DB를 SQLite memory, health를 offline simulation으로 바꿨다.
  따라서 실제 DB·Redis·RDS에 연결하지 않았으며 health=online이나 로그인 검증을 주장하지 않는다.
- 두 서비스 healthy, frontend HTML·JS 및 캐시 헤더, Django admin CSS 응답을 확인했다.
- 프록시를 통한 CSRF 발급 200·Secure 쿠키·HSTS를 확인했다. 클라이언트의 X-Forwarded-Proto=http도
  nginx가 https로 덮어써 정상 동작했다.
- backend UID 10001·nginx UID 101, read-only rootfs·cap_drop ALL·no-new-privileges,
  backend 호스트 포트 비공개·nginx loopback 공개를 inspect로 확인했다.
  backend에서 CA 파일 읽기·/tmp 쓰기는 성공하고 앱 경로 쓰기는 EROFS로 실패했다.
  backend 이미지 안에 .env 파일이 없음을 확인했다.
- backend 재생성 뒤 nginx를 재시작하지 않고 CSRF 프록시 응답이 정상임을 확인했다.
- 준비 스크립트 --check는 통과했고, 기본 실행은 Desktop daemon을 rootless가 아니라고 거절했다.
  rootless 검사를 우회하거나 변경하지 않고 이미지·컨테이너 명령을 별도로 검증했다.
- 검증 컨테이너·네트워크는 down으로 제거했고 local-validation 이미지 두 개는 남겼다.
  실제 EC2 설치·DNS 변경·DB 쓰기·migration·seed·서비스 배포는 수행하지 않았다.
