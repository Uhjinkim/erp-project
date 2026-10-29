# profile / jyoun 기여 문서

- 대상 모듈: `profile` (F2 내 정보·수정 요청)
- 작업 브랜치: `jyoun` (백엔드·사원·조직 메뉴·공용 문서 반영 후보는 [workforce 기여 문서](../../workforce/jyoun/README.md))
- 기준 브랜치: `dev`, origin/dev `220a290` 병합
- 상태: 구현·프론트 자동 검증 완료, 실제 서버·브라우저 검증 대기
- 결정일: 2026-10-27 (사용자 결정)

## 기능 범위

| 화면 | 메뉴명 | 구현 | 기능·규칙 ID |
| --- | --- | --- | --- |
| my-profile | 내 인사정보 | 보기 화면의 `수정` 버튼으로 같은 화면에서 수정 모드 전환. `수정완료` → 확인창 → 수정 요청 제출 | FN-HR-001·002·003, HR-002 |
| change-history | 내 수정 요청 이력 | 기존 기능 유지. "새 변경 요청" 버튼을 "내 정보 수정"으로 바꾸고 my-profile로 이동 | FN-HR-005·011 |
| change-queue | 개인정보 수정 요청 처리함 | 문구만 변경 | FN-HR-004 |
| change-review | 개인정보 변경 승인·반려 | 문구만 변경 | FN-HR-004 |

- 제거: contact-edit(연락처·주소 직접 수정), change-request(민감 정보 변경 요청). my-profile 수정 모드로 합쳤다.
  등록 화면 수는 36개에서 34개가 됐다.
- 개발용 "공통 컴포넌트 전시" 링크를 인사 탭(내 정보·사원·조직)에서 숨겼다(`App.tsx`).
- 제외 범위: 처리함 메뉴의 역할별 노출, 처리자 규칙(workforce 기여 문서의 미결정 사항).

## 설계 결정

- 관련 규칙·기능 ID: `HR-002`, `FN-HR-001`~`FN-HR-005`, `FN-HR-011`
- 수정 모드(`components/ProfileEditForm.tsx`):
  - 연락처·주소·사내 이메일·은행 코드는 현재 값으로 채운다.
  - 계좌번호는 원래 번호를 입력칸에 띄우지 않는다. 마스킹된 현재 값을 안내하고, 바꿀 때만 새로 입력받는다.
  - `toEditPayload`는 바뀐 항목만 보낸다. 연락처·주소를 비우면 빈 문자열(미등록으로 지움)을 보낸다.
    계좌를 바꾸면 은행 코드와 계좌번호를 함께 보낸다.
  - `validateEdit`는 다음만 안내한다. 최종 판단은 서버가 한다.
    - 변경 없음
    - 이메일 공백·형식
    - 은행 코드·계좌번호 짝
- 대기 요청이 있으면 `수정` 버튼을 막고, 내 수정 요청 이력에서 기존 요청을 취소하도록 안내한다.
- 제출 후 `my-profile?saved=request`로 돌아가 "인사관리자가 승인하면 반영됩니다" 안내를 표시한다.
- 직접 수정 API 클라이언트 `updateMyContact`를 제거하고, `ApprovalRequiredValues` 타입에 `phone`·`address`를 추가했다.

## 인터페이스와 데이터 영향

- API·권한 변경: workforce 기여 문서 참고(본인 PATCH 제거, 수정 요청에 연락처·주소 추가).
- Query 키: my-profile `saved=contact` → `saved=request`. 나머지는 그대로다.
- 스키마·migration 변경: profile 프론트엔드 자체는 없다(workforce 0007 필요).
- 환경변수·인프라 영향: 없음.

## 검증

- 실행한 테스트: `bun test ./tests` 53 pass, `bun run lint`, `bun run build` 통과.
  - 수정 모드 초기값(계좌 원문 제외), 변경 항목만 전송, 연락처 지움, 이메일 소문자화, 계좌 짝, 검증 메시지.
- 남은 검증: 일반 사원 세션에서 수정 → 요청 제출 → 이력 확인·취소, 인사관리자의 처리함 승인·반려 후
  내 정보 반영. 대기 요청 중 버튼 비활성, 좁은 화면 배치, 키보드 조작.

## 공용 문서 반영 후보

- Notion 원문: workforce 기여 문서의 HR-002·FN-HR-002~005·011 제안과 같다.
- 저장소 명세·README: `docs/guides/frontend-foundation-contracts.md` profile 행·query 계약,
  `docs/guides/frontend-module-delivery.md` F2 화면 배정표(workforce 기여 문서 목록 참고).
