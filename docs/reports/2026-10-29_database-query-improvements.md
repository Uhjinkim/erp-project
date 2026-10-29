# DB 연결 재사용·반복 질의 보완 · 2026-10-29

- 기준: dev 5dc4415 위 기존 작업 트리. 이전 배포·문서·역할 UX 작업을 보존했다.
- 요청: 직전 UX 보완 후 남은 DB 연결·반복 쿼리 최적화 진행.
- 선행 근거: [성능 검토](./2026-10-29_release-flow-performance-review.md),
  [역할 UX 보완](./2026-10-29_release-ux-improvements.md).
- 범위: 개발 연결 풀, 세션 인증 프로필, 공지 자격 역할 조회, 개인정보 처리함 일괄 조회.
- 모델·스키마·migration·프론트·제품 정책 변경 없음. Notion 조회·수정 없음.

## 1. 개발 연결 재사용

psycopg의 pool extra를 uv로 추가해 pyproject와 lockfile을 함께 갱신했다. 개발 PostgreSQL에
OPTIONS.pool을 적용하고 CONN_MAX_AGE=0을 유지한다. 기본 min_size=0/max_size=4,
대여 timeout=15초, connect_timeout=10초, max_idle=60초, reconnect_timeout=30초다.
아래 후속 연결 실패 재현 후 SSH 최초 접속 시간을 반영해 제한시간을 보정했다.
CONN_HEALTH_CHECKS=True로 대여 시 유효 연결을 확인한다. 풀은 프로세스별이며 요청 스레드 간
공유한다. 최소 연결이 0이므로 설정 로딩·서비스 시작만으로 DB 접속을 요구하지 않는다.

DB_POOL_ENABLED=false로 비활성화할 수 있다. 경계가 잘못된 크기·제한시간은 설정 단계에서
거절한다. SQLite 오프라인·테스트 설정에는 풀이 없고, 기존 운영 WSGI 영속 연결(60초)은 유지한다.
여러 프로세스의 최대 연결 예산과 브라우저 API 제한시간(기본 5초)을 함께 검토해야 한다.
풀 대여 제한시간은 SQL 실행시간 전체를 제한하는 statement timeout이 아니다.

근거: [Django 5.2 연결 관리·pool](https://docs.djangoproject.com/en/5.2/ref/databases/#connection-pool),
[psycopg 풀 동작](https://www.psycopg.org/psycopg3/docs/advanced/pool.html).
설치된 Django backend도 pool을 alias별로 공유하고 요청 종료 시 putconn으로 반환하는 것을 확인했다.
회귀 테스트는 이 대여·반환 경로를 fake pool로 검증하며 실제 PostgreSQL 재사용 실측과 구분한다.

적용은 backend에서 uv sync 후 서버 재시작이다. 환경변수는 backend 개발 예제와 README에 기록했다.
실제 로컬 개인 환경 파일은 수정하지 않았다.

## 2. 조회 결과 재사용과 일괄 조회

### 세션 인증·현재 사용자

재직 검사에서 사원·person·department·position과 부서장 지정 여부 EXISTS를 한 쿼리로 읽는다.
인증된 user에 요청 수명의 사원 객체를 연결해 프로필 DTO와 부서장 표시 정보를 재사용한다.
현재 사용자 view가 같은 사용자를 다시 읽던 쿼리를 제거했다. 부서장 여부는 자기 소속 외 부서의
부서장인 경우도 포함하며 별도의 왕복을 추가하지 않는다.

역할은 현재 요청마다 다시 읽고, 다음 요청에서도 사원 재직 상태를 DB로 확인한다.
프로세스 전역 user/권한 캐시·세션 backend 변경·세션 무효화는 도입하지 않았다.
accounts infrastructure gateway와 기존 workforce application port/infra gateway를 이용하며
domain/application 안에 ORM·Django 의존성을 추가하지 않았다.

### 공지 자격

workforce의 활성 역할 조회 application port와 infrastructure 구현을 추가했다.
세 역할별 exists 대신 현재 유효 코드 집합을 한 번에 읽어 기존 공지 분류 규칙에 대응한다.
미래 부여·과거 회수는 제외하고 역할 회수 후 다음 요청의 자격에 바로 반영한다.

### 개인정보 처리함

요청자와 부서장을 select_related로 읽고, 두 집합의 유효 HR_MANAGER 역할을 한 번에 읽는다.
순수 ProcessorContext DTO를 application에 전달해 기존 domain 처리자 규칙으로 계산한다.
처리 가능 목록뿐 아니라 목록 직렬화의 can_process도 같은 요청 안의 결과를 재사용한다.
승인·반려 명령은 처리자 캐시를 비우고 트랜잭션 안에서 현재 조직·역할을 다시 판정한다.
특별 HR 처리자·본인 처리·superuser 예외는 기존 정책대로 유지한다.

## 3. 쿼리 수 결과

config.settings.test 메모리 SQLite와 합성 데이터에서 실제 세션 인증 APIClient GET을
CaptureQueriesContext로 측정했다. 다음 수치는 세션·사용자 인증 조회를 포함한다.
SQL·개인정보·계좌·자격증명은 결과에 기록하지 않았다.

| 대상 | 이전 기록 | 보완 후 |
| --- | --- | --- |
| /api/auth/me/ | 최초 검토 6회, 이후 부서장 여부 조회 1회 추가 구조 | 4회: 세션·사용자·관계/부서장 조회·활성 역할 |
| 공지 작성 자격 | 6회 | 4회 |
| 처리 가능 개인정보 요청 1건 | 6회 | 7회 |
| 처리 가능 개인정보 요청 10건 | 15회 | 7회 |
| 일반/HR 요청 혼합 21건 | 별도 이전 측정 없음 | 7회 |

처리함은 1건에서 2개의 일괄 준비 조회가 필요해 1회 늘지만, 요청자 수에 따라 증가하던 비용을
고정했다. 별도의 force_authenticate 회귀도 2건/10건의 쿼리 수가 같은지 검증한다.
SQLite 쿼리 수에는 PostgreSQL 풀 대여의 연결 검사·접속 초기화가 포함되지 않으므로 실제
네트워크 왕복·실행시간과 동일시하지 않는다.

## 4. 검증

- backend 전체 pytest: **524 passed** (기존 509 + 새 15개).
- Ruff 통과. test settings manage.py check 및 development settings manage.py check 통과.
- 새 테스트: 실제 세션 me 4회 상한, 공지 자격 4회 상한, 처리함 1/10/21건 7회 상한과 권한 결과.
- 역할 미래 부여·회수 제외, 다음 요청의 역할/부서장 변경·퇴사 후 403 검사.
- 목록 판정 후 조직을 변경한 동일 service 인스턴스의 승인도 거절하고 대기 상태를 유지하는지 검사.
- 설정 subprocess: 기본 PostgreSQL 풀·명시적 비활성·SQLite 오프라인 분리.
- fake pool: Django alias별 풀 공유, 지연 시작, 대여·반환, 물리 close 미호출 검사.
- 비정상 최소/최대 크기·획득/접속 제한시간 거절 검사.
- uv lock 갱신은 uv add로 수행. 모델 변경이 없어 migration drift 검사는 추가 실행하지 않았다.
- 프론트는 수정하지 않아 이번 작업에서 프론트 검사를 재실행하지 않았다(직전 58개·lint·build 통과).

## 5. 실제 접속 확인과 남은 검증

개발 설정으로 별도 요청 스레드의 읽기 전용 SELECT pg_backend_pid()를 실행해 풀 재사용을
확인하려 했으나 첫 접속에서 로컬 DB 전달 포트가 연결을 거부했다. 첫 시도 후 중단하고 풀을
닫았다. 당시 pool 대여 제한은 2초였으며 약 2.01초에 실패했다. 당시 기본 대여 제한은 최초 접속
여유를 위해 4초로 설정했으나, 후속 검증에서 부족한 것으로 확인했다. 이 실패를 풀 재사용 성공·성능 개선 실측으로 기록하지 않는다.

공유 PostgreSQL·Redis의 migration·계정 생성·업무 데이터 쓰기·flush·배포는 수행하지 않았다.
터널 복구 후 서로 다른 요청 스레드에서 동일 DB 세션 재사용, 재연결, 동시 요청과 풀 포화,
지연된 최초 접속을 실측해야 한다. 원격 DB/Redis의 가용성은 코드 변경으로 해결되지 않는다.

프론트 기준정보/급여 조회 범위, 저장 성공 뒤 재조회 실패 구분, 기존 HR/EV/PY 정책·스키마 의제는
이번 DB 세 항목의 쿼리 최적화 완료와 구분한다. 선행 보고서의 해당 후속 항목을 승인·완료로
바꾸지 않았다. 이번 변경은 운영 배포 승인 또는 실제 원격 응답시간 개선 수치를 의미하지 않는다.


## 6. 연결 실패 후속 수정

사용자 연결 실패 신고 후 통합 실행을 재현했다. 개별 접속 3초·풀 대여 4초에서는
runserver의 시작 시 migration 상태 읽기가 PoolTimeout으로 실패하고, 통합 실행기가
프론트·nginx도 종료했다. 이는 migration 적용이 아닌 Django 시작 단계의 읽기 검사다.
동일 설정의 직접 PostgreSQL 연결에 12초 여유를 주자 SELECT 1이 약 4.24초에 성공했다.

개발 기본값을 개별 접속 10초·풀 대여 15초·재연결 시도 기간 30초로 수정했다.
최대 연결 수 4·최소 0은 유지한다. 환경 예제·README·설정 회귀 검사를 함께 갱신했다.
로컬 환경 파일·SSH 프로세스·공유 데이터는 변경하지 않았다. 명시적으로 짧은 제한시간을
설정한 환경에서는 해당 환경변수가 기본값보다 우선하므로 별도 조정이 필요하다.

수정 후 표준 통합 실행으로 nginx 8080·Django 8000·Vite 5173을 기동했다.
HTTP GET / 및 /api/auth/csrf/는 200, 비로그인 /api/auth/me/는 정상적인 403이었다.
별도 프로세스의 순차 독립 요청 스레드에서 읽기 전용 SELECT pg_backend_pid()를 실행한 결과
최초 4.91초·다음 1.19초였고 같은 DB 세션이 재사용됐다. PID·연결정보는 출력하지 않았다.
이 두 번의 측정은 현재 터널 상태에서의 관찰이며 일반적인 응답시간 보장은 아니다.

health는 HTTP 200이며 backend/database/workforce connected를 확인했다.
Redis 직접 PING은 약 3.89초에 성공했지만, 기존 health 제한 1초에서는 disconnected였다.
이 별도 지연과 health 제한은 이번 PostgreSQL 수정으로 해결됐다고 기록하지 않는다.
공유 DB/Redis 쓰기·migration·배포는 수행하지 않았다.

후속으로 Redis 상태 점검 제한을 개발환경 10초로 확대해 전체 online 응답을 확인했다.
설정·실측·메뉴 배치 보완 범위는 [후속 기록](./2026-10-29_health-timeout-menu-layout.md)을 따른다.
