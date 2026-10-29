# 배포 전 기존 사용 흐름·성능 검토

- 검토일: 2026-10-29
- 기준: dev `5dc4415` + 검토 시작 시 존재하던 배포·문서 변경 34개 파일
- 범위: 구성된 프론트 화면의 진입 → 조회 → 입력 → 처리 → 결과 확인·복구와 대응 백엔드
- 이번 변경: 이 검토 문서만 추가. 애플리케이션·설정·의존성은 변경하지 않음.
- Notion 연결 도구 없음. 저장소 스냅샷과 기여 검토 문서를 대조했으며 원문 검증·정책 확정을 주장하지 않음.

## 판단

인사정보 수정 요청, 입퇴사·재입사·발령, 휴가 신청·승인·회수·재신청, 게시글·댓글,
평가 작성·제출·확정, 급여 생성·항목 수정·확정·명세서의 핵심 연결은 구현되어 있다.
배포 준비의 중심은 기존 흐름의 대기·실패·복귀·권한 안내를 완성하고 반복 조회를 줄이는 것이다.
홈 집계 등 새로운 기능을 확대하지 않아도 개선할 수 있는 항목이 많다.

현재 자동 검증은 통과하지만, 실제 브라우저에서 역할별 업무를 끝까지 수행한 출시 검수는 별도로 필요하다.
아래 P0는 진입 차단·입력 유실·처리 결과 오인에 직접 연결되므로 우선 보완한다.

## 1. DB 연결 재사용

### 개발환경

- [개발 설정](../../backend/config/settings/development.py)은 PostgreSQL 연결 유지·풀을 지정하지 않는다.
  [통합 실행](../../scripts/start-dev.sh)은 Django `runserver`를 사용한다.
- `CONN_MAX_AGE`만 늘리는 방식은 권장하지 않는다. Django 개발 서버는 요청마다 새 스레드를 만들기 때문에
  스레드별 영속 연결의 재사용 효과가 사라진다.
- Django 5.2의 PostgreSQL `OPTIONS.pool`과 psycopg 풀을 이용하면 요청 스레드 사이에서 연결을 빌리고 반환할 수 있다.
  현재 의존성은 `psycopg[binary]`이므로 `pool` extra 또는 `psycopg-pool`을 uv로 추가해야 한다.
- 풀을 켜는 설정에서는 `CONN_MAX_AGE=0`을 유지해야 한다. 설치된 Django PostgreSQL backend 소스도
  영속 연결과 풀의 동시 활성화를 `ImproperlyConfigured`로 거절한다.
- 작은 명시적 풀에서 시작해 동시 요청 수·DB 연결 한도를 보고 조정한다. 프로세스마다 별도 풀이므로
  최대 연결 수는 프로세스 수 × 각 풀 상한에 관리·기타 연결을 더해 계산한다.
- 풀 획득 제한시간, DB 접속 제한시간, 브라우저 제한시간을 함께 설계한다. 풀 초기 연결과 터널 재연결 시 지연도 검증한다.
  `runserver --nothreading`은 동시 요청을 직렬화하므로 성능 해결책으로 삼지 않는다.

### 운영환경

- [운영 설정](../../backend/config/settings/production.py)에 이미 `CONN_MAX_AGE=60` 기본값과
  `CONN_HEALTH_CHECKS=True`, 접속 제한시간, RDS TLS 설정이 있다.
- [컨테이너 실행](../../deploy/Dockerfile)은 Gunicorn WSGI worker 2개다.
  우선 현재 연결 유지를 검증하고, 풀은 동시성·연결 예산이 요구할 때 선택한다.
  기존 60초 설정에 `pool=True`만 덧붙이면 안 된다.
- 개발 PC → Cloudflare/SSH → 원격 DB의 지연과 EC2 → RDS 지연은 별도 측정한다.
  이전 개발환경 수치를 운영 응답시간으로 간주하지 않는다.
- 연결 재사용은 접속 비용을 줄인다. 개별 쿼리 왕복 지연은 남으므로 쿼리 감소를 병행해야 한다.

근거: [Django 5.2 DB 연결·개발 서버·PostgreSQL 풀](https://docs.djangoproject.com/en/5.2/ref/databases/),
[psycopg 풀](https://www.psycopg.org/psycopg3/docs/advanced/pool.html).

## 2. 반복 쿼리·조회 개선 대상

실측은 `config.settings.test`의 메모리 SQLite와 합성 사원·역할·요청으로 수행했다.
`APIClient.force_login()` 후 실제 세션 인증 GET을 `CaptureQueriesContext`로 측정했으며,
세션·사용자 인증 쿼리를 포함한다. SQL·개인정보·응답 본문은 출력하지 않았다.

| 대상 | 확인 결과 | 개선 방향 |
| --- | --- | --- |
| `/api/auth/me/` | 6 queries | 세션 사용자→사원 조회 후 뷰가 사용자·사원을 다시 조회하고 프로필 gateway가 사원을 또 조회한다. 인증 backend/인프라에서 필요한 관계를 묶고 요청 범위 DTO·조회 결과를 재사용한다. |
| `/api/board/notice-categories/eligible/` | 6 queries | gateway가 3개 역할을 각각 `exists()` 한다. 현재 유효 역할 코드를 한 번에 읽어 분류를 계산한다. |
| 개인정보 `?processable=true` | 요청자 1명·요청 1건: 6 queries / 요청자 10명·요청 10건: 15 queries | 서비스의 요청자별 캐시는 이미 있으나 서로 다른 요청자의 역할 조회는 선형 증가한다. 역할·조직·부서장 정보를 일괄 조회하는 application port와 infrastructure 구현으로 처리자 판정을 수행한다. |
| 인사·내 정보 화면 전환 | 공통 부모의 화면별 key 때문에 하위 컴포넌트가 재마운트됨 | `useMasterData`·본인 정보의 화면 간 유지 주석과 실제 생명주기가 다르다. 인증 사용자 범위에서 기준정보/본인 조회를 유지하고 변경 성공 시 무효화한다. |
| 사원 목록 페이지 전환 | 프론트 `pageOf`로 페이지를 나누지만 URL 변경마다 전체 조건 조회를 다시 실행 | 같은 조회 조건의 캐시를 페이지 사이에 재사용한다. 데이터 규모가 커지면 서버 페이지네이션을 배열 응답 계약과 함께 변경한다. |
| 급여 관리 화면 | 각 화면의 `useManagerData`가 구성항목·대상자·전 기간 명세서 전체를 반복 조회 | 기준정보 재사용, 선택 기간/사원 서버 필터, 상세의 필요 시 조회. 전월 복사에는 선택 사원의 전월 자료만 확보한다. |
| 휴가 상세 | 유형·내 신청 전체·승인 대상 전체·이력 조회로 현재 한 건을 찾음 | 단건 상세 계약을 정한 뒤 직접 조회. 유형은 재사용하고 처리 응답을 화면에 반영한다. |

근거 코드: [인증](../../backend/accounts/authentication.py), [현재 사용자](../../backend/accounts/views.py),
[사용자 직렬화](../../backend/accounts/serializers.py), [게시판 gateway](../../backend/board/infrastructure/workforce_gateways.py),
[개인정보 서비스](../../backend/workforce/application/personal_info.py),
[공통 화면 key](../../frontend/src/App.tsx), [인사 조회 hook](../../frontend/src/features/workforce/hooks.ts),
[사원 목록](../../frontend/src/features/workforce/screens/EmployeeListScreen.tsx),
[급여 조회 hook](../../frontend/src/features/payroll/hooks/useManagerData.ts), [휴가 조회](../../frontend/src/features/vacation/data.ts).

이미 구현된 최적화도 유지한다. 급여 명세 항목과 사원 표시는 일괄 조회하고,
게시글 작성자·댓글 수, 평가 사원·평가자와 평가 대상도 관련 데이터 묶음 조회가 있다.
모든 목록에 N+1이 있다고 가정해 일괄 리팩터링하지 않는다.
쿼리 수 회귀 검증은 1건과 다건을 비교하고 권한 결과도 함께 검증한다.
권한 정보는 요청 범위에서 재사용하며, 승인·확정 같은 쓰기 시점의 재판정과 트랜잭션을 생략하지 않는다.

근거: [Django 조회 최적화](https://docs.djangoproject.com/en/5.2/topics/db/optimization/).

## 3. 배포 전 사용 흐름 보완

### P0-01: 연결 확인이 업무 진입을 막고 입력 중 화면을 제거할 수 있음

- 근거: 당시 연결 hook(useConnection.ts, 이후 제거됨), [환경 기본값](../../frontend/src/config/environment.ts),
  [화면 연결](../../frontend/src/app/ModuleScreen.tsx), [health](../../backend/config/health.py).
- 기본 API 제한은 5초, health 주기는 10초다. 이전 대화의 2026-10-28 개발환경 health 실측은 약 5.6초였다.
  해당 기본값을 쓰면 성공 가능한 health도 브라우저에서 먼저 취소될 수 있다. 현재 로컬 환경 파일의 override는 이번에 확인하지 않았다.
- health는 DB → Redis → workforce를 순차 확인한다. 실패하면 프론트가 기존 health도 null로 바꾼다.
  인사·내 정보·급여·휴가의 조건부 렌더링이 입력 폼을 제거할 수 있다.
- 휴가는 `end_to_end`에 의존해 Redis 장애만으로도 차단되지만, 현재 휴가 업무 adapter에는 Redis 호출이 없다.
- 완료 조건: 업무 조회는 자기 API 결과로 판단, 공통 health는 상태 안내로 사용.
  일시 실패에도 입력·기존 데이터를 유지하고 업무별 필요한 의존성만 차단한다.
  health 요청 중첩 방지·결과 수명·재시도와 제한시간을 정리한다.
  Redis 연결은 매 health마다 새 client를 열고 닫는 대신 프로세스 범위 풀 재사용을 검토한다.
- 검증: health 6초 지연·Redis만 장애·입력 중 한 번 실패·복구 상황에서 조회/입력이 유지되고
  실제 업무 API 실패는 정확히 안내되는지 확인한다.

### P0-02: 저장 성공과 후속 조회 실패를 구분하지 못하는 흐름

- 근거: [급여 query](../../frontend/src/features/payroll/hooks/usePayrollQuery.ts),
  [급여 생성](../../frontend/src/features/payroll/screens/CreateScreen.tsx),
  [급여 항목](../../frontend/src/features/payroll/screens/ItemsScreen.tsx),
  [급여 확정](../../frontend/src/features/payroll/screens/ConfirmScreen.tsx),
  [요청 처리](../../frontend/src/features/profile/screens/ChangeReviewScreen.tsx).
- 급여 저장/확정 후 `reload()`가 실패해도 hook이 오류를 내부 상태로만 보관한다.
  화면은 `error && !data`일 때만 오류를 표시하므로 기존 data가 있으면 성공 메시지와 오래된 목록이 함께 남는다.
- 개인정보 처리 실패 후 재조회도 실패하면 최신 상태를 받지 못했는데도 “최신 상태를 다시 불러왔습니다”라고 표시한다.
- 쓰기 요청이 브라우저에서 시간 초과되어도 서버 트랜잭션이 취소되었다는 보장은 없다.
  현재 공통 오류에는 처리 결과 불명 상태를 구분하는 정보가 없다.
- 완료 조건: 처리 응답을 우선 반영, 후속 조회 실패는 “저장됨 / 목록 갱신 실패”로 분리해 재조회 버튼 제공.
  시간 초과 시 입력을 보존하고 요청·명세서의 최신 상태 확인으로 이어진 뒤 재처리를 안내한다.
  자동 쓰기 재전송은 피하고, 생성 중복 제약과 필요한 요청 식별·중복 방지 범위를 검토한다.
- 검증: 쓰기 200 후 GET 500, 쓰기 응답 지연 후 실제 저장됨, 다른 담당자의 선행 처리.

### P1-01: 홈·계정 관리가 메뉴에 있지만 업무를 완료할 수 없음

- 근거: [홈 등록](../../frontend/src/features/home/registration.ts), [시스템 등록](../../frontend/src/features/system/registration.ts),
  [dispatcher](../../frontend/src/app/ModuleScreen.tsx), [계정 API](../../backend/accounts/views.py).
- 로고·홈 메뉴는 준비 안내로 끝나고, 계정 관리도 placeholder다. 계정 API는 이미 있다.
- 권장: 이번 출시 홈은 기존 업무 링크 중심의 안내 또는 구현 화면으로 연결한다. 집계 API 확장은 필수가 아니다.
  계정 관리를 출시 메뉴로 유지하려면 기존 API의 목록·사원 연결·활성 상태·비밀번호 설정 흐름을 완성한다.
  다음 출시로 미루면 메뉴와 직접 진입에 일관된 미제공 안내를 적용한다.
- 계정 권한은 기존 HR 관리자 정책을 따른다. 임의로 새로운 시스템 관리자 역할을 만들지 않는다.
- 완료 조건: 노출 메뉴가 실제 완료 가능한 화면으로 이어지고 역할별 접근 제한이 서버와 맞는다.
  HR_MANAGER 없는 superuser 처리 차이는 기존 미결 사항으로 별도 결정한다.

### P1-02: 업무 오류를 잘못된 입력 필드에 연결하지 못함

- 근거: [workforce 오류 응답](../../backend/workforce/presentation/views.py), [공통 client](../../frontend/src/api/client.ts).
- 일부 도메인 오류는 `{detail, field: "email"}`인데 client는 `{email: ["..."]}`만 필드 오류로 해석한다.
  화면 상단 안내는 있지만 해당 입력에는 오류가 연결되지 않는다(UI-HR-03).
- 완료 조건: 기존 응답을 유지하며 client에서 정규화하거나 API 계약을 일관되게 정리한다.
  중첩 account 오류·비필드 오류·도메인 필드 오류를 보존하고 첫 오류 필드로 이동한다.

### P1-03: 평가 이력 오류를 ‘이력 없음’으로 표시하고 재시도 경로가 부족함

- 근거: [평가 작성/상세](../../frontend/src/features/evaluation/screens/FormScreen.tsx),
  [HR 평가 처리](../../frontend/src/features/evaluation/screens/HrScreen.tsx).
- `getEvaluationHistory(...).catch(() => [])`가 통신 실패·서버 오류·권한 오류를 모두 빈 이력으로 바꾼다.
  반려 사유·이전 처리를 확인해야 하는 상황에서 실제 상태를 오해할 수 있다.
- 작성 대상 조회 실패에는 메시지는 있지만 독립적인 재시도 버튼이 없고 빈 대상 안내가 함께 나타날 수 있다.
- 완료 조건: 상세·이력 오류를 분리하고 이력 재시도 제공. 권한 없음, 0건, 서버 실패를 구분한다.
  대상 조회도 빈 결과와 실패를 구분하고 입력값을 유지하며 재시도한다.

### P1-04: 급여 본인 생성이 입력 완료 후 서버에서 거절됨

- 근거: [급여 생성](../../frontend/src/features/payroll/screens/CreateScreen.tsx),
  [사원 선택](../../frontend/src/features/payroll/components/EmployeePicker.tsx),
  [급여 서비스](../../backend/payroll/application/service.py).
- 생성 화면은 전달된 `ownEmployeeNo`를 사용하지 않아 본인도 선택·금액 입력·제출할 수 있다.
  서버는 본인 급여 생성을 거절한다. 수정·확정 화면에는 이미 본인 처리 제한 안내가 있다.
- 완료 조건: 현재 서버 규칙에 맞춰 본인 생성 제한을 선택 시점에 알린다.
  자기거래 정책 자체의 제품 확정(PY-02)은 별도로 유지한다.

### P1-05: 미저장 입력 보호와 목록 복귀 맥락

- 근거: [전역 화면 key](../../frontend/src/App.tsx), [사원 상세](../../frontend/src/features/workforce/screens/EmployeeDetailScreen.tsx),
  [게시판 라우팅](../../frontend/src/features/board/BoardScreen.tsx), [게시판 목록](../../frontend/src/features/board/screens/BoardListScreen.tsx).
- 여러 입력 화면은 이동 시 로컬 state를 잃고 공통 미저장 변경 보호가 없다.
  게시판 검색은 로컬 state에만 있고 상세에서 목록으로 돌아오면 초기화된다.
  사원 상세의 목록 링크도 기존 검색/페이지 조건을 전달하지 않는다.
- 완료 조건: 작성 중 이동 시 사용자 선택으로 계속 작성/나가기 제공.
  목록 검색·페이지는 URL 또는 사용자 범위 state로 복구한다.
  개인정보·급여 입력을 임의로 localStorage에 장기 보관하는 방식은 사용하지 않는다.

### P2-01: 다운로드·권한 갱신의 일관성

- [엑셀 다운로드](../../frontend/src/api/payroll.ts)는 공통 client와 다른 fetch를 사용해 timeout과
  401/403 세션 재확인 알림을 공유하지 않는다. 다운로드 전용 transport로 동일한 복구 계약을 적용한다.
- [역할 관리](../../frontend/src/features/workforce/screens/RoleGrantScreen.tsx) 성공 후 역할 목록은 갱신되지만
  [세션](../../frontend/src/app/useSession.ts)의 `user.roles`는 자동 갱신되지 않는다.
  본인의 역할 변경·만료 후 메뉴가 늦게 바뀔 수 있으므로 적절한 세션 재검증 경로를 둔다.
- 서버의 역할·상태 판정은 계속 authoritative하게 유지한다.

## 4. 기존 정책·API 범위 결정이 필요한 보완

- UI-LV-01: 휴가 폼의 잔여일수·예정 승인자는 현재 안내문만 있다. 기존 잔여/승인선 port를 활용한
  읽기 API의 범위와 권한을 정하면 제출 전 조회 UX를 연결할 수 있다. 일수 자동 계산 규칙은 임의로 만들지 않는다.
- UI-LV-02: HR은 알려진 ID의 이력을 볼 수 있어도 내 신청/승인 목록 밖 현재 신청을 조회할 수 없다.
  현재 상태 단건 조회 권한을 정한 뒤 상세를 연결한다. 이력으로 현재 상태를 추정하지 않는다.
- BD-01~03, EV-01/02, HR-01~03, PY-01/02는 기존 미결이다. 특히 급여 반올림·지급일,
  HR 겸직 평가, 개인정보 특별 처리자 등은 화면 완성 과정에서 임의 변경하지 않는다.
- OPS-01과 빈 RDS baseline·기준정보 준비는 배포 검증의 별도 선행 조건이다.
  테스트 통과가 실제 PostgreSQL 스키마·데이터 준비를 보장하지 않는다.

기준: [미확정 정책](../specs/notion/05-open-policies.md),
[모듈 검토 의제](2026-10-14_module-review-agenda.md),
[이전 배포 준비 보고서](2026-10-28_documentation-deployment-readiness.md).

## 5. 권장 구현 순서와 출시 검수

1. P0 연결 확인 의존성·입력 보존·쓰기 결과/재조회 실패 구분부터 수정한다.
2. 개발 DB 풀과 인증·공지 자격·개인정보 처리함 쿼리를 개선하고 1건/다건 쿼리 수를 비교한다.
3. 기준정보/급여 조회 범위를 줄이고, 필드 오류·평가 이력·급여 본인 제한·미저장/목록 복귀 흐름을 완성한다.
4. 미완성 메뉴는 기존 API로 연결하거나 출시 노출에서 제외하고, 휴가 읽기 계약·기존 미결 정책을 결정한다.
5. 운영 환경과 동등한 staging에서 역할별 브라우저 검수를 수행한다.

출시 검수는 일반 사원·부서장·인사관리자·급여담당자·겸직·사원 미연결 계정을 포함한다.
각 업무의 성공, 400 입력 오류, 403 업무 권한, 세션 만료, 타인 선행 처리, 삭제된 대상,
느린 응답, 저장 성공 후 갱신 실패를 확인한다. 역할별 정상/거절 결과는 백엔드 테스트도 유지한다.
핵심 동선은 로그인 → 내 정보 수정 요청/취소/처리, 휴가 신청/승인/회수/재신청,
사원 등록/발령/퇴사/재입사, 게시글·댓글, 평가 작성/제출/반려/확정,
급여 생성/수정/확정/정정/명세서 다운로드다.

## 검증 기록·제한

- `uv run pytest -q`: **504 passed**, 메모리 SQLite·fake 사용.
- `uv run ruff check .`: 통과.
- `uv run python manage.py check --settings=config.settings.test`: 통과.
- `bun run test`: **53 passed**. 현재 주로 model/helper/API 계약·dispatcher 검사이며 브라우저 사용자 흐름 검증을 대신하지 않는다.
- `bun run lint`, `bun run build`: 통과.
- 합성 데이터 query probe: `/auth/me/` 6, 공지 자격 6, 개인정보 처리함 1건 6 / 10건 15 queries.
  첫 probe의 fixture에 requested_at이 누락되어 중단한 뒤 값을 보완하여 정상 재측정했다.
- `git diff --check`: 통과. 기존 사용자 변경은 보존한다.
- 모델 변경이 없어 migration 생성/드리프트 검사를 추가 실행하지 않았다.
- 이번에는 공유 PostgreSQL·Redis·RDS에 접속/쓰기/migration/seed를 하지 않았다.
  앞선 대화의 개발환경 시간 수치는 과거 측정이며 이번 query probe의 실행시간으로 환산하지 않는다.
- 실제 로그인 브라우저 검수·운영 부하/풀 성능·PostgreSQL 쿼리 계획은 이번에 검증하지 않았다.
- canonical 명세·가이드·목차는 변경하지 않았다. 본 문서는 제품 정책 승인이 아닌 후속 구현 제안이다.


## 후속 구현 기록

이 문서는 최초 검토 결과를 보존한다. 전시·연결 UI 제거와 역할별 UX 보완 이후, 개발 연결 풀과
인증·공지 자격·개인정보 처리함 쿼리 최적화는
[성능 보완 보고서](./2026-10-29_database-query-improvements.md)에 구현·검증 결과를 기록했다.
