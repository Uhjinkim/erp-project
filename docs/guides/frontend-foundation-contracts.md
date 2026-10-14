# 프론트엔드 공통 토대 사용 계약

- 토대 구현일: 2026-10-13
- 현재 연결 계약 확인일: 2026-10-14
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

## 2. 현재 연결된 화면과 후속 작업

2026-10-14 dev 4f77219의 registration·공개 진입점·기여 문서를 대조했다.
“연결”은 화면 구현이 있다는 뜻이며 제품 정책 승인·시안 검수·실제 서버 검증 완료를 뜻하지 않는다.

| 모듈 | 공개 진입점·현재 화면 | 남은 확인 |
| --- | --- | --- |
| profile | ProfileScreen: my-profile, contact-edit, change-request, change-history, change-queue, change-review | HR-01~03, 실제 처리자·경합 검증 |
| workforce | WorkforceScreen: employee-list, employee-detail, employee-create, retire, rehire, role-grant, org | UI-HR-01 시안 대조, UI-HR-03 필드 오류, HR/OPS 의제 |
| vacation | VacationPanel: leave-apply, leave-mine, leave-detail, leave-queue, leave-approve, leave-recall, leave-resubmit | UI-LV-01/02 조회 API 공백, 실제 서버 검증 |
| board | BoardScreen: notice-list, board-list, board-write | BD-01~03, 브라우저 성공·오류·권한 검증 |
| evaluation | EvaluationModule: evaluation-team, evaluation-form, evaluation-hr, evaluation-mine | EV-01/02 추가 정책, 실제 환경 검증 |
| payroll | PayrollScreen: payroll-periods, payroll-create, payroll-item, payroll-confirm, payslip | PY-01/02, 실제 지급일·출력 검증 |
| system | system-health 연결; account-admin 준비 중 | 계정 관리·확정 권한에 따른 운영 동선 |
| home | home·manager-home 준비 중 | 집계 API와 업무 카드 |

ModuleScreen은 위 공개 진입점에 route/user/연결 상태를 전달한다. 다른 feature의 내부 화면을
공용 셸에서 import하지 않는다. 구형 BoardPanel·WorkforcePanel·EvaluationPanel·PayrollPanel과
EmployeeInfoCard·PersonalInfoRequests는 삭제돼 현재 계약의 진입점이 아니다.

### 화면별 query 계약

| 모듈 | 현재 query 사용 |
| --- | --- |
| profile | my-profile `saved=contact`; change-history `status`, `saved=request`; change-queue `saved=approved/rejected`; change-review `requestId` 필수 |
| workforce | employee-list `view=retired`, `q`, `dept`, `status`, `page`; 퇴사자 필터 `name`, `empNo`, `dept`, `from`, `to`, `page`; 상세 `empNo` 필수, `tab=history/roles`; retire/rehire/role-grant `empNo` 없으면 대상 검색; org `tab=positions` |
| vacation | 상세·승인·회수·재신청 `requestId`; 목록 `status`, `type`, `q`, `from`, `to`, `order`, `page`; 개발 인증에서만 `employeeNo` |
| board | notice-list/board-list `postId` 있으면 같은 게시판의 글 보기; board-detail·notice-write 별도 메뉴 없음. 기본 진입 notice-list |
| evaluation | form `evalId` 수정 또는 `empNo`, `year` 생성; HR 화면 `evalId`; 팀 연도 선택은 화면 상태 |
| payroll | 생성·항목·확정 `period=YYYY-MM`; 항목 `statementId`; 기본 진입 payslip |

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
컴포넌트 전시는 개발 환경에서만 `#/design-system/gallery`로 연다. 합성 예시이며 실제 업무 API를
호출하는 액션은 없다. 운영 환경에서는 전시 라우트를 제공하지 않는다.

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

기존 사원 관리 패널은 과도기적으로 본인 정보·변경 요청 UI도 포함한다. F2·F3가 후속 화면 분리
PR의 순서를 합의한다. 같은 파일을 동시에 이동하거나 수정하지 않는다.

## 5. 인증·연결·오류 계약

`useSession`은 checking/authenticated/anonymous/expired/unavailable/development를 구분한다.
미인증은 로그인으로, 인증 서버 장애는 재시도 안내로 표시한다. 업무 API의 401/403은 공통 client가
재확인을 요청하고 `/api/auth/me/`가 실제 미인증인 경우에만 만료로 전환한다. 업무 403 자체는
모듈에서 오류로 표시한다. 로그인 성공 시 현재 hash 주소를 유지한다.

로그아웃은 서버 성공을 확인한 후 화면을 비운다. 실패를 성공으로 표현하지 않는다. 만료·사용자
변경 시 셸·모듈 트리를 교체하여 이전 사용자 상태를 제거한다. 개발 사원 전환도 휴가 트리를 교체한다.

`useConnection`은 health 폴링·수동 확인·개발 오프라인 전환을 제공한다. 오래된 응답을 무시하고
언마운트 시 폴링을 제거한다. 일반 기존 패널은 backend 연결을, 휴가는 기존 end_to_end 연결
조건을 사용한다. health 성공은 해당 업무 권한이나 데이터 준비 완료를 보증하지 않는다.

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
