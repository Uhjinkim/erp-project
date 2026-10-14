# workforce / feature/workforce-ui-screens 기여 문서

- 대상 모듈: `workforce` (F3 사원·조직)
- 작업 브랜치: `feature/workforce-ui-screens`
- 기준 브랜치: `dev`, origin/dev `67403ce`에서 시작
- 상태: 구현·프론트 자동 검증 완료, 실제 서버·브라우저 통합 검증 대기
- 구현·저장소 확인일: 2026-10-14

## 기능 범위

| 화면 | 구현 | 기능·규칙 ID |
| --- | --- | --- |
| employee-list | 사원 목록(이름·이메일·사번, 부서, 재직 상태 서버 필터), 퇴사자 조회 탭(이름·사번·부서·퇴사일 기간) | HR-001, FN-HR-008, HR-005 |
| employee-detail | 요약·인적사항·연락처, 계좌 기본 마스킹·전체 보기, 인사이력·변경 기록, 발령 등록, 최근 이력 정정·취소, 역할 이력 | HR-001, FN-HR-010, HR-010 |
| employee-create | 인적사항·고용·연락처·역할·계정 동시 등록, 결과 요약(사번·계정·역할) | FN-HR-006, HR-007, HR-008 |
| retire | 대상 검색 → 퇴사일 입력 → 확인창 → 결과 | FN-HR-007, HR-004, HR-005, HR-009 |
| rehire | 퇴사자 검색 → 이전 고용 요약 → 재입사 폼(인적사항은 입력 시에만 갱신) → 새 사번 결과 | FN-HR-009, HR-006, HR-007 |
| role-grant | 대상 검색 → 활성 역할 외 부여, 활성 역할 회수 확인창, 부여·회수 이력 | 역할 독립 합산, HR_LEAVE_APPROVER 1인 제한(서버) |
| org | 부서 탭(추가·수정·상위 부서·부서장), 직급 탭(추가·수정·정렬 순서) | 부서 계층 순환·부서장 소속 검증(서버) |

- 제외 범위: 부서·직급 삭제(참조 무결성 정책 미확인), 계정 CRUD(F8), 본인 정보·변경 요청·HR 처리함(F2),
  사원 정보 일반 수정 폼(이메일은 HR-003 승인 절차 전용, 일반 PATCH로 인사 업무를 대체하지 않음).

## 설계 결정

- 기준 문서: frontend-module-delivery.md의 F3 행·추가 지시, frontend-foundation-contracts.md의 공통 UI·라우팅 계약.
- **시안 미확인**: Graphite 시안(`frontend/mockups/`)은 `.gitignore` 대상이며 이 작업 PC에 없었다.
  화면 ID·묶음은 배정표를 따랐고 배치는 공통 UI와 휴가·급여 모듈의 기존 구성을 따랐다. 시안 대조가 필요하다(UI-HR-01).
- 화면 주소와 query 키
  - `employee-list`: `view=retired`, `q`, `dept`, `status`, `page` / 퇴사자 `name`, `empNo`, `dept`, `from`, `to`, `page`
  - `employee-detail`: `empNo`(필수), `tab=history|roles`
  - `retire`·`rehire`·`role-grant`: `empNo`(없으면 대상 검색 목록), `org`: `tab=positions`
  - 필터는 서버 query로 전달하고, 20행 페이지는 반환된 배열 안에서만 나눈다(서버 페이지네이션 아님).
- 화면 노출: HR_MANAGER 또는 superuser에게 사원 6개 화면을 안내하고, 그 외 사용자에게는 내 인사정보 이동을 안내한다.
  org는 인증 사용자 모두 조회, 편집 버튼은 HR에게만 표시한다. 최종 권한은 API가 판정하며 403은 화면 오류로 표시한다.
- 퇴사·재입사·발령·역할은 서버의 전용 처리 API 한 번으로 실행한다. 프론트에서 여러 PATCH로 업무 트랜잭션을 만들지 않는다.
- 모든 처리 버튼은 동기 잠금 + pending으로 연속 실행을 막고 실패 시 입력을 유지한다. 성공 후 관련 목록을 다시 조회한다.
  화면 전환 후 도착한 이전 응답은 버린다. 부서·직급·역할 마스터는 모듈 진입 동안 유지하고 조직 변경 후 다시 조회한다.
- 날짜·금액은 서버 형식(YYYY-MM-DD, decimal 문자열)으로 전송한다. 퇴사일·발령일 입력은 오늘 이하, 입사일 이상으로 안내만 하고
  최종 검증은 서버가 한다. 서버 rule violation은 `{detail, field}` 형식이라 메시지는 상단 Alert로 표시된다.
- 계좌번호는 상세에서 기본 마스킹하고 HR이 명시적으로 펼칠 때만 원문을 표시한다(HR-02 보호 방향, 정책 확정 아님).
  신규 등록 결과·처리 화면 요약에는 계좌를 표시하지 않는다. 초기 비밀번호는 응답·화면에 다시 표시하지 않는다.
- 내부 구성: `WorkforceScreen`(진입·분기), `screens/*`, `components/`(EmployeeLookup, EmploymentFormFields,
  HistoryPanel, EmployeeSummary, Pager, QueryFallback), `hooks.ts`, `model.ts`, `workforce.module.css`.
  공통 UI는 Button·필드·Alert·Badge·Card·DetailList·Table·Tabs·Modal·ConfirmDialog·EmptyState·ErrorState·Spinner만 소비했다.
  공용 컴포넌트·토큰·셸·client는 수정하지 않았다.

## 인터페이스와 데이터 영향

- API·권한 변경: 없음. 기존 `/api/workforce/` employees(list·retrieve·terminated·terminate·history·history/changes·
  history/{id}/correct·cancel·roles·roles/{id}/revoke), persons/{id}/rehire, new-hires, departments, positions, roles만 사용한다.
- `api/workforce.ts`: `loadWorkforce`를 제거하고 위 엔드포인트별 함수로 교체했다. 다른 모듈의 호출은 없었다(INT-01 확인).
- `types/workforce.ts`: 기존 EmployeeSummary·EmployeeDetail 등은 유지하고 이력·역할·등록·퇴사자 DTO를 추가했다(F2가 참조 유지).
- 기존 `components/WorkforcePanel.tsx` 삭제. `EmployeeInfoCard`·`PersonalInfoRequests`는 profile 재구현과 함께 삭제했다(profile 초안 참고).
- 스키마·migration·환경변수·의존성 변경 없음. 공유 PostgreSQL·Redis에 접속하지 않았다.

### 공용 파일 변경(F0 검토 요청)

- `app/ModuleScreen.tsx`: workforce 전체 등록 화면을 `WorkforceScreen`으로 연결(휴가·급여와 같은 진입점 통합).
- `tests/module-screen.test.ts`: workforce를 진입점 분기 회귀 대상에 추가하고 미구현 placeholder 예시를 profile change-queue로 교체.
- 삭제 요청: `styles/legacy.css`의 `.workforce-panel`, `.workforce-toolbar`, `.workforce-grid`, `.employee-list`,
  `.employee-item`, `.department-list`, `.department-item`, `.department-form` 선택자는 더 이상 사용되지 않는다.

## 검증

- `bun run test`: 7개 파일 40개 통과. 신규 `tests/workforce.test.ts` — HR 노출 판정, ID 파싱, query 링크, 계좌 마스킹,
  최근 이력 판정, 활성 역할 제외, 페이지 범위, 등록·재입사 폼 검증/전송 형식, 필드 오류 매핑, 엔드포인트·메서드·본문.
- `bun run lint`, `bun run build`: 통과.
- 합성 데이터 서버 렌더링 점검(임시 스크립트, 커밋하지 않음): 조직 표·직급 표·재입사 폼·등록 결과·비HR 안내 렌더링 확인.
- 남은 검증: 실제 브라우저에서 HR·비HR·복수 역할·superuser 세션으로 목록→상세→발령/정정/취소, 등록, 퇴사, 재입사,
  역할 부여·회수, 조직 편집의 성공·서버 거부·403·만료·연결 실패, dialog 포커스 복귀, 좁은 화면 표 스크롤을 확인해야 한다.
  실제 DB 쓰기 검증은 대상 환경·권한 승인 후 수행한다.

## UI-HR-01 · 시안 대조 미수행

- 상태: 조사 필요
- 주 담당 모듈: workforce / 협업: 디자인 담당
- 유형: 환경 확인
- 현재 동작·근거: `frontend/mockups/`는 gitignore 대상이며 작업 PC에 없었다. 화면 배치는 공통 UI 기준으로 구성했다.
- 작업 항목: 확정 시안을 받아 7개 화면의 배치·문구·표 열을 대조하고 차이를 수정한다.
- 결정 요청: 없음(시안 파일 공유 필요).

## UI-HR-02 · HR 개인정보 처리함의 화면 공백

- 상태: 검증 완료(같은 브랜치에서 해소)
- 주 담당 모듈: profile(F2) / 협업: workforce
- 결과: workforce에서 제거한 HR 처리함은 profile의 `change-queue`·`change-review`로 이 브랜치에서 함께 구현했다.
  상세는 [profile 기여 초안](../../profile/feature-workforce-ui-screens/README.md)을 따른다.

## UI-HR-03 · 서버 rule violation의 필드 연결

- 상태: 제안
- 주 담당 모듈: workforce backend / 협업: F0 client
- 유형: 구현 연동
- 현재 동작·근거: `rule_violation_response`는 `{"detail": ..., "field": "term_date"}`를 반환하며 client의 fieldErrors는 배열 값만 읽는다.
  따라서 퇴사일·발령일·이메일 등 도메인 오류는 필드 옆이 아니라 상단 Alert로 표시된다. DRF serializer 오류는 필드에 연결된다.
- 작업 항목: 백엔드가 `{field: [message]}`를 함께 반환하거나 F0 client가 `field` 키를 지원하는 방안 중 하나를 선택한다.

## 공용 문서 반영 후보

- Notion 원문: 변경 없음.
- frontend-foundation-contracts.md 2절 workforce 행: 7개 화면 연결 완료, 후속 작업은 시안 대조(UI-HR-01).
- frontend-module-delivery.md: F3 화면 query 키 계약을 기록.
- 위 의제는 문서에만 기록했으며 담당자에게 메시지를 보내지 않았다.
