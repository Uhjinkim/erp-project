# profile / feature/workforce-ui-screens 기여 문서

- 대상 모듈: `profile` (F2 내 정보·변경 요청)
- 작업 브랜치: `feature/workforce-ui-screens` (workforce F3 작업과 같은 브랜치, 기여 초안은 모듈별로 분리)
- 기준 브랜치: `dev`, origin/dev `67403ce`에서 시작
- 상태: 구현·프론트 자동 검증 완료, 실제 서버·브라우저 통합 검증 대기
- 구현·저장소 확인일: 2026-10-14

## 기능 범위

| 화면 | 구현 | 기능·규칙 ID |
| --- | --- | --- |
| my-profile | 보기 전용(수정·요청 버튼 없음). 인사정보·연락처·이메일·계좌, 계좌 기본 마스킹, 대기 요청 안내, 수정 메뉴 안내 문구 | FN-HR-001, HR-001 |
| contact-edit | 연락처·주소 전용 수정 페이지. 변경 없으면 저장 비활성, 저장 후 my-profile로 복귀하며 완료 안내 | FN-HR-002, HR-002 |
| change-request | 현재 값(계좌 마스킹) + 바꿀 항목만 입력 → 확인창 → 제출 후 change-history로 이동. 대기 요청이 있으면 폼 대신 안내 | FN-HR-003, HR-003 |
| change-history | 내 요청 목록, 상태 필터, 반려 사유, 대기 요청 취소 확인창 | FN-HR-005, FN-HR-011, HR-011 |
| change-queue | 서버가 반환한 처리 가능 대기 요청(오래된 순), 처리 화면 이동 | FN-HR-004 |
| change-review | 요청 상세, 전·후 비교, 승인·반려(선택 사유) 확인창, 처리 후 처리함 복귀 | FN-HR-004, HR-003 |

- 사용자 요청에 따라 기존 "한 화면 안의 편집 폼"을 조회 화면과 수정 페이지로 분리했다. my-profile은 보기 전용이며
  contact-edit·change-request는 왼쪽 메뉴에서 진입한다.
- 제외 범위: 내선번호·부서 등 인사정보 수정(HR 업무, workforce), 개인정보 이력 보존·파기(HR-012, HR-02 의제).

## 설계 결정

- Query 키: my-profile `saved=contact`, change-history `status`·`saved=request`, change-queue `saved=approved|rejected`,
  change-review `requestId`(필수). 상태 필터는 서버 `status` 파라미터로 조회한다.
- 본인 정보와 대기 요청 조회는 profile 진입 동안 유지한다. 연락처 저장 응답은 재조회 없이 반영하고, 요청 제출·취소 후 대기 요청을 다시 조회한다.
- 처리함은 HR 역할로 화면을 막지 않는다. HR 본인의 요청은 HR인 부서장이 처리할 수 있으므로 서버의 `processable=true` 결과만 표시한다.
  처리 버튼은 서버 응답의 `can_process`와 `대기` 상태일 때만 보인다. 처리 실패 시 요청을 다시 조회해 최신 상태를 보여 준다.
- 계좌: 본인 화면은 기본 마스킹 + 본인이 펼칠 때만 원문. 목록·이력은 항상 마스킹. 처리 화면의 요청 값은 서버가 처리자에게
  원문을 줄 때만 원문으로 표시하며, 이전 값은 서버가 마스킹한 값을 그대로 쓴다(HR-02).
- 한 번에 대기 요청 1건, 현재 값과 동일 금지, 이메일 중복은 서버가 최종 판정한다. 프론트는 빈 요청·은행/계좌 짝·이메일 형식만 안내한다.
- 모든 처리는 동기 잠금 + pending으로 연속 실행을 막고 실패 시 입력을 유지한다.
- 공통 UI만 소비했고 공용 컴포넌트·토큰·client는 수정하지 않았다. 다른 feature 내부 코드를 import하지 않는다
  (workforce와 비슷한 조회 hook을 각 모듈 내부에 둠, 승격은 두 소비 사례 검토 후 F0 판단).

## 인터페이스와 데이터 영향

- API·권한·스키마·migration·환경변수·의존성 변경 없음. 공유 PostgreSQL·Redis 접속 없음.
- `api/profile.ts`: 기존 `GET /api/workforce/personal-info-requests/{id}/`용 `getChangeRequest` 추가.
- 삭제: `components/EmployeeInfoCard.tsx`, `components/PersonalInfoRequests.tsx`(모든 사용처를 새 화면으로 교체).

### 공용 파일 변경(F0 검토 요청)

- `app/ModuleScreen.tsx`: profile 6개 화면 전체를 `ProfileScreen(route)`으로 연결.
- `tests/module-screen.test.ts`: profile을 진입점 분기·세션 필요 회귀 대상에 추가, 미구현 예시를 system account-admin으로 교체.
- 삭제 요청: `styles/legacy.css`의 `.personal-info-editor`, `.personal-info-forms`, `.change-request-list`, `.change-request-item`,
  `.change-summary`, `.reject-reason`, `.employee-info__*` 등 개인정보 패널 선택자. `.two-columns`, `.helper`, `.reason`처럼
  다른 기존 패널과 공유될 수 있는 선택자는 F0가 사용처를 확인한 뒤 정리한다.

## 검증

- `bun run test`: 8개 파일 46개 통과. 신규 `tests/profile.test.ts` — 링크, 계좌 마스킹(서버 마스킹 값 보존), 상태 파싱,
  연락처 변경 판정·전송 형식, 변경 요청 검증·입력 항목만 전송.
- `bun run lint`, `bun run build`: 통과.
- 합성 데이터 서버 렌더링 점검(임시, 커밋하지 않음): my-profile 기본·대기 요청 상태, contact-edit, change-request, 전후 비교.
- 남은 검증: 실제 세션으로 일반 사원(수정·요청·취소), HR(처리함 승인·반려), HR 본인 요청의 부서장 처리, superuser,
  대기 요청 중복·이메일 중복 거부, 처리 경합(다른 처리자가 먼저 처리), 확인창 포커스 복귀를 브라우저에서 확인해야 한다.

## 공용 문서 반영 후보

- frontend-foundation-contracts.md 2절 profile 행: 6개 화면 연결 완료, 수정은 별도 페이지(contact-edit·change-request)로 분리.
- HR-01~03 의제는 이번 UI 작업으로 결정하지 않았다. 기존 API 동작을 그대로 표시한다.
