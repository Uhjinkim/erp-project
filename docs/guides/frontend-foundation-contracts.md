# 프론트엔드 공통 토대 사용 계약

- 토대 구현일: 2026-10-13
- 현재 연결 계약 확인일: 2026-10-29
- 기준: dev, [모듈 배정 안내서](./frontend-module-delivery.md)
- 범위: 공통 UI·앱 조립·모듈 진입점. 39개 업무 화면 전체의 완성을 뜻하지 않는다.

## 1. 실행과 화면 주소

일반 개발은 루트 start-dev 스크립트를 사용한다. UI만 검수할 때는 frontend에서 `bun run dev`를
실행한다. 프론트 포트·API 프록시·인증 환경변수는 기존 설정을 유지한다.

주소는 `#/모듈ID/화면ID`다. 예: `#/vacation/leave-apply`,
`#/vacation/leave-detail?requestId=12`. 상세 식별자·필터는 `Route.search`를 URLSearchParams로
읽는다. 각 기능이 실제로 사용할 키·필수 여부는 모듈 작업 카드에 기록한다. 화면 ID는 기본적으로 Graphite
와이어프레임 ID를 따른다. 게시판의 현재 메뉴 분리는 2절의 실제 계약을 따른다. 로그인·세션 만료는 라우트가 아니라 인증 상태로 표시한다.

- `app/routing.ts`: Route, parseRoute, routeHref, findScreen의 순수 계약
- `app/useRoute.ts`: hashchange 구독. 링크 이동·뒤로가기·새로고침 때 URL을 유지
- `features/<module>/registration.ts`: 담당 모듈의 화면 이름·메뉴·기본 진입 화면
- `app/modules.ts`: 모듈 등록 조립. F0 소유
- `app/ModuleScreen.tsx`: 실제 진입 컴포넌트 연결. F0 소유

신규 화면 담당자는 자신의 registration과 공개 진입점만 작성하고 F0에 조립 변경을 요청한다.
다른 모듈의 screens·hooks·components를 직접 import하지 않는다. 전체 화면 등록은 인증 사용자의
내비게이션 골격이며, 시안의 역할 필터를 제품 권한표로 옮기지 않았다. 업무 API가 실제 접근 권한을
검사하고 기능 담당자가 확인된 정책에 따라 메뉴·액션 노출을 구체화한다.

### 업무 시간대

업무 시각과 오늘 날짜는 `src/utils/dateTime.ts`의 Asia/Seoul 기준을 사용한다.
한국어 locale 지정만으로 시간대가 고정되지는 않는다. API의 offset/UTC 시각은 서울 시간으로
표시하고, 시간대 없는 휴가 입력은 +09:00으로 해석해 UTC ISO로 전송한다. 기기 시간대는
업무 기준으로 사용하지 않는다. 날짜만 있는 생년월일·입사일 등의 값에는 시각 변환을 적용하지 않는다.

## 2. 현재 연결된 화면과 후속 작업

2026-10-29 dev 작업 트리의 registration·공개 진입점·기여 문서를 대조했다.
“연결”은 화면 구현이 있다는 뜻이며 제품 정책 승인·시안 검수·실제 서버 검증 완료를 뜻하지 않는다.

| 모듈 | 공개 진입점·현재 화면 | 남은 확인 |
| --- | --- | --- |
| profile | ProfileScreen: my-profile(수정 모드 포함), change-history, change-queue, change-review | HR-01~03, 실제 처리자·경합 검증 |
| workforce | WorkforceScreen: employee-list, employee-detail, employee-create, retire, rehire, role-grant, org | UI-HR-01 시안 대조, UI-HR-03 필드 오류, HR/OPS 의제 |
| vacation | VacationPanel: leave-apply, leave-mine, leave-detail, leave-queue, leave-approve, leave-recall, leave-resubmit | UI-LV-01/02 조회 API 공백, 실제 서버 검증 |
| board | BoardScreen: notice-list, board-list, board-write | BD-01~03, 브라우저 성공·오류·권한 검증 |
| evaluation | EvaluationModule: evaluation-team, evaluation-form, evaluation-hr, evaluation-mine | EV-01/02 추가 정책, 실제 환경 검증 |
| payroll | PayrollScreen: payroll-periods, payroll-create, payroll-item, payroll-confirm, payslip | PY-01/02, 실제 지급일·출력 검증 |
| system | 배포 등록 제외 | 기존 account-admin 준비 중 화면은 구현 후 연결 |
| home | 배포 등록 제외 | 집계 API·업무 카드 구현 후 연결 |

ModuleScreen은 위 공개 진입점에 route/user를 전달한다. 다른 feature의 내부 화면을
공용 셸에서 import하지 않는다. 구형 BoardPanel·WorkforcePanel·EvaluationPanel·PayrollPanel과
EmployeeInfoCard·PersonalInfoRequests는 삭제돼 현재 계약의 진입점이 아니다.

### 화면별 query 계약

| 모듈 | 현재 query 사용 |
| --- | --- |
| profile | my-profile `saved=request`; change-history `status`, `saved=request`; change-queue `saved=approved/rejected`; change-review `requestId` 필수 |
| workforce | employee-list `view=retired`, `q`, `dept`, `status`, `page`; 퇴사자 필터 `name`, `empNo`, `dept`, `from`, `to`, `page`; 상세 `empNo` 필수, `tab=history/roles`; retire/rehire/role-grant `empNo` 없으면 대상 검색; org `tab=positions` |
| vacation | 상세·승인·회수·재신청 `requestId`; 목록 `status`, `type`, `q`, `from`, `to`, `order`, `page`; 개발 인증에서만 `employeeNo` |
| board | notice-list/board-list `postId` 있으면 같은 게시판의 글 보기; board-detail·notice-write 별도 메뉴 없음. 기본 진입 notice-list |
| evaluation | form `evalId` 수정 또는 `empNo`, `year` 생성; HR 화면 `evalId`; 팀 연도 선택은 화면 상태 |
| payroll | 생성·항목·확정 `period=YYYY-MM`; 항목 `statementId`; 기본 진입 payslip |

사원 상세·인사 이력은 필수 `empNo`가 있는 대상별 화면이므로 사이드바와 메뉴 검색에서 제외한다.
사원 목록의 이름 링크 등 사원을 지정한 링크와 상세 화면의 인사 이력 탭으로 진입한다.

목록 검색/페이지가 모두 서버 query라는 뜻은 아니다. workforce/profile은 서버 필터를 사용하며
workforce의 20행 페이지는 반환 배열 안에서 나눈다. vacation은 조회 배열의 필터·정렬·10행 페이지,
board는 조회 배열의 공지/일반·검색 분리다. 상세 query나 메뉴 변경은 모듈 기여 문서와
이 계약에 함께 기록한다. 원래 Graphite 39장은 디자인 분석 기준이며 현재 등록/구현 수와 별개다.

INT-01 사원 조회 의존과 UI-HR-02 처리함 연결은 구현으로 해결했다. 다른 HR·BD·EV·PY·OPS 및
UI 의제는 [최신 검토 의제](../reports/2026-10-14_module-review-agenda.md)를 따른다.

## 3. 공통 UI 사용

`components/ui`에서 import한다. 업무 API·권한·상태 전이는 UI 컴포넌트에 넣지 않는다.

| 컴포넌트 | 주요 props·동작 |
| --- | --- |
| Button | variant: primary/secondary/ghost/danger, size: regular/small, pending, disabled, 기본 type=button |
| IconButton | Button 계약 + 필수 label로 접근 가능한 이름 제공 |
| TextInput·Textarea·Select | label, hint, error, 네이티브 props와 ref. label·설명·오류 ID 자동 연결 |
| Checkbox | label과 네이티브 checked/onChange |
| FormField | 커스텀 필드를 위한 label·id·hint·error·required·children 연결 |
| Badge·Alert | tone: neutral/info/success/warning/error. 업무 상태 → tone은 모듈이 결정 |
| Spinner·Skeleton | label로 로딩 상태 설명 |
| EmptyState·ErrorState | title·children, action 또는 onRetry |
| Card·Section | title·children, Card의 actions 슬롯 |
| PageHeader | title·description·actions. 셸에서 기본 제공하며 feature가 h1을 중복 생성하지 않음 |
| DetailList | key·label·value 목록. 업무 필드 결정은 소비 모듈 |
| Table | 필수 caption과 네이티브 table children. th scope·row key·정렬은 소비 모듈 |
| Tabs | label·items(value/label)·value·onChange·선택 패널 children. 방향키/Home/End 지원 |
| Modal·Drawer | open·title·onClose·children·actions·busy. 네이티브 dialog로 포커스 제한·복귀·Escape 처리 |
| ConfirmDialog | Modal 계약 + onConfirm·confirmLabel·danger |

Modal은 busy 상태에서 닫기·Escape를 막는다. 작업 실행 중 버튼 비활성·중복 요청 방지는 모듈이
담당한다. 불필요한 네트워크 재시도나 업무 확인 절차를 기본 UI가 자동 수행하지 않는다.
배포 준비에 따라 컴포넌트 전시 화면과 `#/design-system/gallery` 진입점을 제거했다.
업무 화면에서 사용하는 공통 UI 컴포넌트는 유지한다.

## 4. 스타일과 이관 소유권

- `styles/tokens.css`: 표면·본문·경계·액션·위험·포커스 색, 간격, 글자, 레이어 토큰. 외부 폰트
  의존성을 추가하지 않고 시스템 글꼴을 사용한다. Graphite의 축소 글자 크기는 복사하지 않았다.
- `styles/base.css`: 최소 reset·focus. 새 기능은 CSS Modules와 토큰을 사용한다.
- `styles/legacy.css`: 기존 패널 스타일을 `.legacy-module`의 CSS @scope에 격리했다.
  기존 패널을 이관할 때 래퍼를 유지하고, 전환이 끝난 선택자만 F0에 삭제 요청한다.
- `styles/print.css`: 기존 급여 인쇄 규칙. body 기반 인쇄 동작을 위해 scope 밖에 유지한다.
- `components/layout/AppShell`: 어두운 상단·아이콘 레일·밝은 메뉴·본문. 720px 이하에서 메뉴를
  접고 상단의 화면 메뉴 버튼으로 연다. 표·긴 본문이 캔버스에 잘리지 않도록 고정 비율을 사용하지 않는다.

CSS @scope와 네이티브 dialog를 지원하는 최신 브라우저를 기준으로 했다. 팀의 대상 브라우저
버전이 다르면 이관 또는 폴리필 범위를 공통 변경으로 검토한다.

이번 토대에서 이관한 파일은 다음과 같다.

- App의 휴가 → `features/vacation/VacationPanel.tsx`, `api/vacation.ts`, `types/vacation.ts`
- workforce API의 본인 정보·변경 요청 → `api/profile.ts`
- workforce 타입의 변경 요청 DTO → `types/profile.ts`. EmployeeDetail 등 사원 DTO는 원래 경로 유지
- 기존 업무 패널은 원래 components 경로에 유지하고 각 feature/index.ts에서 공개 진입점을 제공

본인 수정 요청 UI는 profile, 사원·조직 관리는 workforce가 소유한다.
공유 타입이나 라우팅을 바꿀 때는 F0와 변경 범위를 합의한다.

## 5. 인증·연결·오류 계약

`useSession`은 checking/authenticated/anonymous/expired/unavailable/development를 구분한다.
미인증은 로그인으로, 인증 서버 장애는 재시도 안내로 표시한다. 업무 API의 401/403은 공통 client가
재확인을 요청하고 `/api/auth/me/`가 실제 미인증인 경우에만 만료로 전환한다. 업무 403 자체는
모듈에서 오류로 표시한다. 로그인 성공 시 현재 hash 주소를 유지한다.

로그아웃은 서버 성공을 확인한 후 화면을 비운다. 실패를 성공으로 표현하지 않는다. 만료·사용자
변경 시 셸·모듈 트리를 교체하여 이전 사용자 상태를 제거한다. 개발 사원 전환도 휴가 트리를 교체한다.

공통 연결 상태 UI·health 폴링·수동 확인·개발 오프라인 전환을 제거했다. 업무 화면은
health 결과를 기다리지 않고 해당 API를 호출하며 모듈별 오류·재시도를 표시한다. 인증 서버
장애·세션 확인은 기존 useSession 계약을 유지한다. 백엔드 health API는 운영 진단용으로 유지한다.

`requestJson`의 쿠키·CSRF·타임아웃·상대 API 주소를 유지한다. ApiError는 message·status·
unavailable에 더해 fieldErrors를 제공한다. 폼은 fieldErrors의 서버 키를 각 필드 error에 연결한다.
각 모듈이 별도 fetch 래퍼를 복제하지 않는다. 앱 조립·client·세션/연결·공용 스타일·의존성은 F0가 소유한다.

## 6. 검증

frontend에서 실행한다.

```bash
bun run test
bun run lint
bun run build
```

테스트 러너는 기존 Bun 내장 기능을 사용하며 새 의존성은 추가하지 않았다. tests 디렉터리는 앱
TypeScript 빌드 범위 밖이다. 라우트 소유권·직접 URL·상세 query, CSRF·204·필드 오류·403 재확인
이벤트·가용성 오류를 검증한다. 실제 UI·인증 상태 전환·업무 처리는 합성 응답 브라우저 검증도
수행한다. 확인 결과와 실제 서버 미검증 범위는 [토대 구현 보고서](../reports/2026-10-13_frontend-foundation.md)에 기록했다.

## 2026-10-29 배포 메뉴·수정 계약

workforce는 활성 HR_MANAGER 또는 superuser에게 메뉴와 직접 URL 화면을 연다.
2026-10-29 사용자 선택으로 기존 서버의 superuser 예외와 일치시켰다.
profile은 4개 화면이며 my-profile의 수정완료가 수정 요청을 만든다.
연락처·주소도 승인 후 반영한다. 계좌번호 원문은 수정 폼에 채우지 않는다.
평가 저장·제출 실패 시 입력값을 유지하고 HR의 본인 평가에는 처리 버튼을 숨긴다.
평가 targets는 일괄 조회로 팀 크기에 따른 질의 증가를 방지한다(회귀 테스트 상한 15회).

2026-10-29 실제 세션·CSRF와 격리 SQLite API를 사용한 역할별 브라우저 결과는
[배포 전 역할 검수](../reports/2026-10-29_role-browser-release-review.md)에 기록했다.

현재 배포 등록은 6개 모듈·30개 화면이다. 홈·시스템은 등록하지 않고 브랜드 링크는 내 정보로 이동한다.
개인정보 처리함은 HR_MANAGER 또는 superuser, 평가 관리는 HR_MANAGER, 급여 관리는
PAYROLL_MANAGER에게 표시한다. 급여 서비스는 superuser만으로 관리 권한을 부여하지 않으므로
프론트도 동일하게 안내한다. 부서장은 인증 응답의 is_department_head로 구분하며, 평가 진입은
부서장→팀 평가, HR→평가 관리, 그 외→내 평가다. 겸직 부서장은 팀 평가부터 진입한다.

신청·평가의 상세·처리 화면은 독립 메뉴에서 숨기고 목록의 대상별 링크로 연다. 이전 작성자·승인자의
직접 링크는 유지하고 실제 권한·상태는 서버가 검사한다. 권한 없는 관리 URL은 접근 안내와
해당 모듈의 이용 가능한 진입 링크를 표시한다. 프로필 처리함의 개별 처리 가능 여부도 서버 기준이다.
급여 생성은 본인 선택지·금액 입력·저장을 사전 차단하며 조회 필터에서는 본인도 조회할 수 있다.
보완·재검수 결과는 [배포 UX 보완](../reports/2026-10-29_release-ux-improvements.md)을 따른다.

메뉴 검색은 왼쪽 탐색 영역 최상단에 검색 아이콘·입력창으로 배치한다. 모듈 제목과 메뉴 목록은
그 아래에 이어진다. 시각 라벨은 입력 안내로 줄이되 연결된 접근성 label·포커스 표시는 유지한다.
검색 범위는 현재 역할에 노출되는 활성 모듈 메뉴이며 모바일에서는 화면 메뉴를 열어 사용한다.
검증 범위는 [상태 점검·메뉴 배치 보완](../reports/2026-10-29_health-timeout-menu-layout.md)에 기록했다.


## 업무 아이콘·선택 상태

아이콘은 lucide-react의 named import를 사용한다. 외부 폰트·CDN은 사용하지 않는다.
ModuleRegistration.icon과 screens[].icon은 문자열 대신 LucideIcon 컴포넌트 타입이다.
신규 화면 등록 시 동작 의미에 맞는 icon도 지정한다. AppShell은 모듈 24px·하위 메뉴 18px·
검색/유틸리티 16px로 렌더링한다. 아이콘에 aria-hidden을 지정하고 링크/버튼의 이름은 유지한다.

선택은 현재 Route와 aria-current를 기준으로 계산한다. 모듈과 하위 메뉴의 선택 상태는
배경·왼쪽 표시선·아이콘 색·선 두께(기본 2, 선택 2.5)로 표현한다. hover가 선택 배경을 덮지
않도록 구분한다. 아이콘만으로 상태나 업무 이름을 전달하지 않는다.
의미별 매핑과 검수는 [Lucide 적용 기록](../reports/2026-10-29_lucide-business-icons.md)을 따른다.


## 반응형 본문·표 배치

AppShell 본문은 내비게이션을 제외한 영역 안에서 최대 1280px로 제한한다. 큰 화면의 설명·
긴 글은 72ch 안에서 읽고, DetailList는 데스크톱 항목명 6~8rem/값 가변 폭, 600px 이하에서는
항목명과 값을 위아래로 배치한다. 새 화면의 grid 자식은 min-width:0과 줄어들 수 있는 트랙을
사용해 내부 표의 최소 폭이 페이지 전체로 전파되지 않도록 한다.

공통 Table은 36rem, 급여명세 전용 표는 28rem의 읽기 가능한 최소 폭을 유지하고 내부 영역에서
가로 스크롤한다. 스크롤 영역은 이름과 키보드 포커스를 제공한다. thead와 tbody의 금액 열은
같은 amount 클래스로 오른쪽 정렬한다. 일반 열은 왼쪽 정렬하고 정렬 버튼의 추가 좌우 여백을
없앤다. 숨김 라벨이 스크롤 영역 밖에 절대 배치되지 않도록 스크롤 래퍼를 위치 기준으로 둔다.

검수 화면·크기·한계는 [반응형 배치 검토](../reports/2026-10-29_responsive-layout-review.md)를 따른다.


### 2026-10-29 휴가 신청 잔여일수

신청·재신청은 기존 유형 요청에 `include_balance=true`를 붙여 본인 유형별 잔여를 함께 받는다.
다른 휴가 화면은 기존 유형 조회를 유지한다. 유형 변경·일수 입력은 네트워크 요청 없이 표시를
갱신하며 모바일에서도 유형 선택 바로 아래에 잔여, 새로고침, 부족 안내를 제공한다.
`remaining_days` 문자열/`null`/필드 누락을 각각 일수/제한 없음/확인 불가로 구분하고,
새로고침 실패는 기존 값을 최신으로 제시하지 않는다. 새로고침 실패·복구에도 폼 입력을 유지한다.
서버 잔여 검증과 승인 시 차감을 최종 판단으로 유지한다. 상세 검증은
[보고서](../reports/2026-10-29_vacation-request-balances.md)를 따른다.

잔여 없는 기존 유형 데이터가 화면에 남으면 1회 자동 재조회하고, 최신 유형 props도 즉시 반영한다.
정상 초기 응답에는 추가 조회가 없다. 잔여 포함 요청에 필드가 없는 서버 응답은 명시적 계약 오류로
안내하며 0/null과 구분한다. 자동 재조회 실패는 반복하지 않고 수동 재시도로 복구한다.


2026-10-29 반차 보완: 유형의 `balance_type_id`가 신청 유형과 다르면 공유 잔여 안내를 제공한다.
현재 HALF는 ANNUAL 잔여를 공유하며 같은 일수를 표시한다. 유형 변경 시 서버의 양수
`deduct_days`를 사용 일수 기본값으로 반영한다(반차 0.50, 연차 1.00). 일정·사유는 유지한다.
기존 신청의 최초 수정 진입에서는 저장된 `use_days`를 유지한다. 유형 변경에 별도 요청은 없다.
