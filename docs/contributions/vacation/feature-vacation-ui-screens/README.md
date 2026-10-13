# vacation / feature/vacation-ui-screens 기여 문서

- 대상 모듈: vacation (F4)
- 작업 브랜치: feature/vacation-ui-screens
- 기준 브랜치: dev, origin/dev의 2c11c9c에서 시작
- 상태: 구현·프론트 검증 완료, 실제 서버 통합 검증 대기
- 구현·저장소 확인일: 2026-10-13

## 기능 범위

| 화면 | 구현 | 기능 ID |
| --- | --- | --- |
| leave-apply | 유형·기간·일수·사유 입력, 필드 오류, 제출 결과 요약, 새 신청 | FN-LV-001 |
| leave-mine | 내 신청 현황·검색·정렬·페이지, 상세 및 취소 진입 | FN-LV-002, FN-LV-003 |
| leave-detail | 현재 신청 요약, 가능한 처리, 변경 이력과 전후 비교 | FN-LV-008 |
| leave-queue | 서버가 반환하는 내 승인 대상, 상태 검색, 처리 진입 | FN-LV-004 |
| leave-approve | 지정 승인자의 대기 신청 승인·반려 확인창 | FN-LV-005 |
| leave-recall | 지정 승인자의 승인 신청 회수, 필수 사유 | FN-LV-006 |
| leave-resubmit | 회수된 본인 신청의 값 복원·수정·재신청 | FN-LV-007 |

요청 ID 없이 승인·회수·재신청 화면을 열면 처리 가능한 목록을 보여준다.
취소는 내 신청 목록에서 상세 화면으로 진입한 후 확인창에서 처리한다.
잔여일수 조회, 승인 예정자 미리보기, 임의 신청의 현재 상세 조회 API 추가는 이번 범위에 없다.

## 설계 결정과 컴포넌트 소유권

- 기준: frontend-module-delivery.md, frontend-foundation-contracts.md의 F4 경계 및
  frontend/mockups/graphite-wireframes/wireframes.js의 Graphite 시안. 이전의 신청 폼·현황 통합 패널을 화면별로 분리했다.
- Button, 필드, Alert, Badge, Card, DetailList, Table, EmptyState, ErrorState, Spinner,
  ConfirmDialog는 기존 디자인시스템을 사용한다. 공통 컴포넌트·토큰·셸 계약을 새로 정의하지 않는다.
- RequestForm은 신청·재신청에서 재사용한다. RequestList는 본인·승인·작업 선택 목록에서 재사용한다.
  RequestSummary, RequestActions, RequestHistory와 데이터 훅·표시/검색 함수는 휴가 내부 소유다.
  휴가 상태·이력·규칙은 디자인시스템으로 승격하지 않는다.
- 공용 ModuleScreen 변경은 모든 vacation 등록 화면에 screenId/search를 전달하는 한 줄의 통합이다.
  다른 모듈의 라우트·코드·API를 수정하지 않았다.
- 상세 주소는 #/vacation/leave-detail?requestId=12 형태다. 목록의 status/type/q/from/to/order/page는
  hash query에 저장한다. 필터·정렬·10행 페이지는 현재 조회된 배열 안에서 수행한다.
  전체 조직 조회나 서버 페이지네이션이라고 표시하지 않는다. 상태 요약은 필터 전 조회 목록의 건수다.
- 개발 사원 전환은 development 인증 모드에서만 제공하고 employeeNo query를 휴가 링크에 유지한다.
  session 모드에서는 query를 신원으로 사용하지 않는다. 사원 미연결·오프라인에서는 폼을 노출하지 않는다.
- 대기 본인 취소, 지정 승인자의 대기 승인·반려, 지정 승인자의 승인 회수, 회수된 본인 재신청을
  안내한다(LV-005~007). HR 역할만으로 처리 버튼을 추가하지 않는다. 서버가 권한·상태·잔여를 최종 강제한다.
- 사용 일수는 API의 0.01~9.99 범위와 소수 둘째 자리, 사유는 255자를 검사한다.
  휴일·반차·기간별 일수·자기 승인 금지 정책을 만들지 않는다. 일시는 로컬 입력을 ISO로 전송한다.
- 중복 제출은 mutation의 동기 잠금과 pending 비활성으로 막는다. 실패 시 입력·사유를 유지한다.
  화면·신원 변경 후 도착한 응답은 사용하지 않는다. 처리 성공 후 현재 목록과 이력을 다시 조회한다.
- 상세의 내 신청·승인 대상·이력 요청은 독립적으로 처리한다. 일부 조회가 실패해도 접근 가능한 결과를 숨기지 않는다.
  이전 이력의 null/missing 스냅샷은 현재 데이터로 복원하지 않는다. 비교 가능한 기록만 변경 항목을 표시한다.

## 인터페이스와 데이터 영향

- 기존 /api/vacations/의 types, requests, approvals, history, cancel, approve, reject, recall,
  resubmit만 사용한다. session cookies/CSRF와 개발용 X-Employee-No는 기존 transport에 맡긴다.
- UI 타입은 decimal의 숫자·문자 응답을 허용하고 optional nullable before_values/after_values를 추가한다.
  값이 없는 기존 서버 이력도 표시할 수 있다. 차감 반영 여부는 반환된 스냅샷만 표시한다.
- API·백엔드 권한·DB 모델·migration·환경변수·의존성 변경 없음.
- 작업 시작 시 존재한 백엔드 휴가 수정, 보고서 및 공용 명세 변경은 별도 작업으로 보존한다.
  이 프론트 커밋에 포함하지 않는다. 공유 PostgreSQL/Redis에 접속·DDL·데이터 변경을 하지 않았다.

## 검증

- bun run test: 15개 통과. ID 파싱, 담당자·상태별 작업, 재신청 시각 복원,
  입력 범위, 검색·정렬, 구형 이력, 전후 비교, 부분 조회 실패를 검증한다.
- ./scripts/docs-workflow.sh check: 최신 origin/dev(795f2eb) 기준 공용 문서 범위 검사 통과.
- bun run lint / bun run build: 통과. strict TypeScript 및 production 번들 생성 확인.
- Air 브라우저에서 전 요청을 합성 fetch로 대체하여 실제 세션 모드의 사원/승인자 UI 확인:
  신청 POST → 상세 → 취소 POST, 대기 승인 POST, 승인 회수 POST(빈 사유 차단),
  신청자 재신청 PUT(0.50일·사유 수정), 반려 POST의 400 오류·입력 유지·재시도 성공.
  실제 DB에 처리 요청을 보내지 않았다.
- 상태 필터 적용 시 URL과 행 갱신, 변경 이력의 상태·사유·전후 표,
  확인창 Escape 닫기와 원래 버튼의 포커스 복귀를 확인했다.
- dev 통합 검증: 사용자 push 지시에 따라 2026-10-13 최신 origin/dev(2f81f90)에 휴가 기능을 병합했다.
  별도 작업 트리에서 통합하여 원래 작업 트리의 미커밋 백엔드·공용 문서 변경을 보존했다.
  기존 dev의 ModuleScreen에 중복된 implemented 선언과 삭제된 EvaluationPanel/PayrollPanel 참조가 있어
  모듈 공개 진입점 기준으로 정리했다. 게시판·평가·급여의 모든 등록 화면과 휴가 7개 화면,
  세션 필요 조건, 미구현 화면 안내를 회귀 테스트로 확인했다. 통합 상태에서 전체 테스트 26개,
  lint, build가 통과했다. 원래 작업 트리의 백엔드 수정은 이 통합에 포함하지 않았다.
- 남은 검증: 실제 세션·개발 인증 및 공유 서비스가 준비된 별도 환경에서
  실제 승인선·잔여 검증·권한 오류·동시 상태 변경·이력 저장 결과를 통합 검증해야 한다.
  이번 브라우저 검증은 백엔드 규칙 또는 실제 데이터의 정확성을 증명하지 않는다.

## UI-LV-01 · 시안의 잔여·승인 예정 정보

- 상태: 제품 결정 필요
- 주 담당 모듈: vacation / 협업 모듈: workforce, 공통 transport
- 유형: 요구 미완료
- 관련 규칙·기능 ID: LV-001, LV-004, FN-LV-001, FN-LV-007
- 확정 기준: 저장소 기능 명세와 06-api-specification.md, 2026-10-13 코드 확인.
  Notion 원문은 이번 작업에서 직접 재검증하지 않았다.
- 현재 동작·근거: 잔여 조회·승인 예정자 API 없음. 화면에는 서버 확인/신청 시 지정으로 표시하며 예시 숫자·이름을 넣지 않는다.
- 영향: 신청 전 수치·담당자 미리보기 불가.
- 작업 항목·결정 요청: 문서 담당자와 제품 담당자가 조회 API 범위·권한·반환 계약을 확정하면 연결한다.
- 완료 기준: 확정 API의 권한·빈 잔여·승인선 미결정·서버 오류 검증, 명세 및 시안 반영.
- 검증 결과: 현재 API 범위로 폼·서버 결과 표시는 검증 완료. 수치 미리보기 미구현.
- 공유 인프라 영향: 없음.

## UI-LV-02 · 인사관리자의 임의 신청 현재 상세

- 상태: 제품 결정 필요
- 주 담당 모듈: vacation / 협업 모듈: accounts
- 유형: 요구 미완료
- 관련 규칙·기능 ID: FN-LV-008
- 확정 기준: 저장소 API 명세·history 접근 권한 및 현재 vacation presentation 코드, 확인일 2026-10-13.
- 현재 동작·근거: 상세 GET 없음. 본인/지정 승인 대상 밖의 HR은 알려진 ID의 history를 볼 수 있으나
  현재 신청 DTO를 조회할 수 없다. 현재 상세를 이력에서 추정하지 않고 이력과 제한 안내를 보여준다.
- 영향: HR 전용 검색·현재 상세 전체 조회가 제공되지 않는다.
- 작업 항목·결정 요청: 임의 신청 현재 조회/검색 API를 추가할지와 권한 범위를 제품·백엔드 담당자가 확정한다.
- 완료 기준: 확정 권한, 없는 ID, 조직 밖 접근, 현재/이력 값 구분 테스트와 공용 API 명세 반영.
- 검증 결과: 부분 실패 및 null 스냅샷 회귀 테스트 통과. HR 실제 API 통합은 미검증.
- 공유 인프라 영향: 없음.

## 공용 문서 반영 후보

문서 담당자는 병합 후 frontend-module-delivery.md와 frontend-foundation-contracts.md의
F4 완료 상태·실제 내부 컴포넌트·query 계약을 반영하고, dated report에 검증과 API 제약을 기록한다.
공용 명세 변경은 UI-LV-01/02 결정 후 수행한다. Notion 원문과 다른 확정 정책을 이번 UI에 도입하지 않았다.
위 의제는 문서에 기록했으며 외부 담당자에게 메시지를 발송하지 않았다.
