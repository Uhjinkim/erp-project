# 사원·조직 메뉴 노출과 개인정보 수정 요청 흐름 결정 · 2026-10-27

## 결정

사용자 요청에 따라 아래 정책을 저장소 문서와 코드에 반영했다. Notion 원문은 갱신하지 않았으며
Notion 반영은 문서 담당자가 한다.

1. **사원·조직 메뉴 노출**: 사원·조직(workforce) 메뉴는 활성 `HR_MANAGER` 역할이 있는 계정에게만 보인다.
   그 외 사용자에게는 메뉴를 숨기고, URL로 직접 들어와도 화면을 그리지 않는다. 사원 목록·상세 API의
   서버 권한 검사(HR-001)는 그대로 유지한다.
2. **명칭 변경**: "개인정보 변경 요청"과 "승인형 개인정보 변경 요청"을 "개인정보 수정 요청"으로 통일한다.
   화면명도 "개인정보 수정 요청 처리함", "내 수정 요청 이력"으로 바꾼다. 승인·반려 탭(change-review)의
   이름과 기능 FN-HR-004의 이름은 "개인정보 변경 승인·반려"로 한다(현재 탭 이름 "개인정보 요청 승인·반려").
3. **내 정보 수정 흐름**: 내 정보(my-profile)에 `수정` 버튼을 두고, 같은 화면에서 연락처·주소·사내 이메일·
   급여계좌를 바로 편집한다. `수정완료`를 누르면 바뀐 항목만 개인정보 수정 요청(`대기`)으로 제출한다.
   인사관리자가 승인하면 반영되고 반려하면 기존 값이 유지된다. 연락처·주소의 직접 반영은 없앤다.
   별도 메뉴였던 contact-edit·change-request는 my-profile 수정 모드로 합친다. 처리함(change-queue)과
   승인·반려 화면(change-review)은 유지한다.

## 반영한 문서

| 문서 | 반영 내용 |
| --- | --- |
| [02. 비즈니스 규칙](../specs/notion/02-business-rules.md) | HR-002를 "모든 본인 수정은 수정 요청 후 인사관리자 승인"으로 변경, HR-003·011·012 명칭 |
| [03. 기능 명세](../specs/notion/03-feature-specification.md) | FN-HR-002 내 정보 수정, FN-HR-003~005·011 명칭 |
| [04. 상세 기능](../specs/notion/04-detailed-features.md) | FN-HR-002 상세 신설, FN-HR-003 진입 조건을 `수정완료`로 변경 |
| [05. 미확정 정책](../specs/notion/05-open-policies.md) | 명칭 |
| [06. API 명세](../specs/notion/06-api-specification.md) | 7.1 본인 PATCH 제거, 수정 요청 본문에 `phone`·`address` |
| [08. 테이블 명세](../specs/notion/08-table-specification.md) | workforce 0007 컬럼 추가 기록 |
| [workforce 구현 대응표](../specs/notion/workforce-implementation-map.md) | FN-HR-002·003 현재 구현, 0007 공유 DB 적용 대기 |
| [프론트엔드 공통 계약](../guides/frontend-foundation-contracts.md) | 메뉴 노출 정책, profile·workforce 화면 행 |
| [모듈 배정 안내](../guides/frontend-module-delivery.md) | F2·F3 경계, 화면 배정표, 모듈별 지시 |

기여 문서(`docs/contributions/`)와 과거 보고서는 당시 기록이므로 수정하지 않았다.

## 구현

- backend(workforce)
  - 수정 요청 값(`ApprovalRequiredValues`)에 `phone`·`address`를 추가했다. 연락처·주소의 빈 문자열은
    미등록으로 지우는 요청이며 승인 시 `None`으로 반영한다. 이메일·은행 코드·계좌는 비울 수 없다.
  - 본인 직접 수정(`PATCH /api/workforce/employees/me/`, `update_own_contact`, `update_contact` 포트)을
    제거했다. PATCH는 405다.
  - migration `0007_personal_info_request_contact`: `personal_info_change_requests`에
    `previous_phone`·`previous_address`·`requested_phone`·`requested_address`(NULL 허용) 추가.
    공유 DB에는 적용하지 않았다.
  - 처리자 판정(HR 요청자의 특별 처리자)은 바꾸지 않았다(아래 확인 필요).
- frontend
  - `ModuleRegistration.requiredRole`과 `visibleModules(user)`를 추가했다. workforce는
    `requiredRole: "HR_MANAGER"`이며 셸 메뉴와 화면 해석(App)에서 함께 걸러진다. WorkforceScreen도 모든
    화면에서 `HR_MANAGER` 역할을 다시 확인한다. `isHRManager`는 superuser 예외 없이 역할만 본다.
  - profile 메뉴에서 contact-edit·change-request를 제거하고 my-profile에 `수정` 버튼과 수정 모드
    (`ProfileEditForm`)를 추가했다. 계좌번호는 원문을 입력칸에 띄우지 않고 바꿀 때만 새로 입력받는다.
    대기 요청이 있으면 `수정` 버튼을 막고 내 수정 요청 이력에서 취소하도록 안내한다.
  - 메뉴명: 내 수정 요청 이력, 개인정보 수정 요청 처리함, 개인정보 변경 승인·반려.

## 검증

- backend: `ruff check .`, `manage.py check`, `pytest`(502 passed), `makemigrations --check --dry-run`(No changes).
  migration 생성 시 로컬 PostgreSQL 연결이 없어 이력 일관성 검사 경고만 출력됐다(DB 접속·쓰기 없음).
- frontend: `bun test ./tests`(49 pass), `bun run lint`, `bun run build` 통과.
- 실제 서버·브라우저에서 일반 사원·인사관리자 세션으로 메뉴 노출, 수정 요청 제출·승인·반려를 확인하지 않았다.

## 확인 필요

- superuser 노출: 이번 결정은 "인사관리자 계정만"이다. `HR_MANAGER` 역할이 없는 superuser에게도
  사원·조직 메뉴를 숨길지 확인해야 한다(현재 API는 superuser를 HR 관리자로 허용한다).
- 인사관리자 본인 요청의 처리자: 현재 구현은 HR 요청자의 특별 처리자 판정이 있고 HR-03 의제에 있다.
  "승인은 인사관리자"와 본인 승인 금지를 어떻게 조합할지 확정해야 한다.
- 처리함 메뉴 노출: change-queue·change-review를 내 정보 메뉴에서 인사관리자에게만 보일지 결정해야 한다.
- 대기 요청 1건 제한: 현재는 대기 요청이 있으면 `수정` 버튼을 막고 취소를 안내한다. 1건 제한 자체는
  HR-03 미확정이다.
