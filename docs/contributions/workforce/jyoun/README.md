# workforce / jyoun 기여 문서

- 대상 모듈: `workforce` (백엔드 개인정보 수정 요청, F3 사원·조직 메뉴 노출)
- 작업 브랜치: `jyoun` (profile 화면 변경은 [profile 기여 문서](../../profile/jyoun/README.md)에 분리)
- 기준 브랜치: `dev`, origin/dev `220a290` 병합
- 상태: 구현·자동 검증 완료, 실제 서버·브라우저 검증과 Notion·공용 문서 반영 대기
- 결정일: 2026-10-27 (사용자 결정)

## 기능 범위

- 구현 범위:
  - 사원·조직(workforce) 메뉴는 활성 `HR_MANAGER` 역할 계정에게만 노출한다. 다른 사용자는 주소로 직접
    들어와도 화면을 그리지 않는다. 사원 목록·상세 API의 서버 권한 검사(HR-001)는 그대로 둔다.
  - 개인정보 수정 요청 항목에 연락처(`phone`)·주소(`address`)를 추가했다. 연락처·주소도 인사관리자가
    승인해야 반영된다(HR-002 변경).
  - 본인 직접 수정 경로 `PATCH /api/workforce/employees/me/`를 제거했다.
  - 용어를 "개인정보 변경 요청"에서 "개인정보 수정 요청"으로 바꿨다. 승인·반려 기능(FN-HR-004)과 탭
    이름은 "개인정보 변경 승인·반려"로 한다.
- 제외 범위:
  - 수정 요청 처리자 판정(HR 요청자의 특별 처리자)은 바꾸지 않았다(HR-03, 아래 미결정 사항).
  - 공유 PostgreSQL에 migration을 적용하지 않았다.

## 설계 결정

- 관련 규칙·기능 ID: `HR-001`, `HR-002`, `HR-003`, `HR-011`, `HR-012`, `FN-HR-002`~`FN-HR-005`, `FN-HR-011`
- 도메인·애플리케이션 결정:
  - `ApprovalRequiredValues`에 `phone`·`address`를 추가했다. `None`은 "수정하지 않음", 연락처·주소의
    빈 문자열은 "미등록으로 지움"이다. 승인 시 `changes()`가 빈 문자열을 `None`으로 바꿔 반영한다.
  - 사내 이메일·은행 코드·계좌번호는 비울 수 없다. 지움 요청과 기존 미등록 값은 같은 값으로 보아
    "현재 값과 다른 값을 입력하세요"로 거절한다.
  - `validate_self_editable_fields`, `SELF_EDITABLE_FIELDS`, `PersonalInfoService.update_own_contact`,
    `PersonalInfoRepository.update_contact` 포트를 제거했다.
  - 프론트 메뉴 노출은 `ModuleRegistration.requiredRole`과 `visibleModules(user)`로 셸 메뉴와 화면
    해석(App)에 함께 적용한다. `isHRManager`는 superuser 예외 없이 `HR_MANAGER` 역할만 본다.

## 인터페이스와 데이터 영향

- API·권한 변경:
  - `PATCH /api/workforce/employees/me/` 제거(405). `GET`은 그대로다.
  - `POST /api/workforce/personal-info-requests/` 본문에 `phone`, `address` 추가. 생략·`null`은 수정하지
    않음, 빈 문자열은 미등록으로 지움. 응답의 `previous`·`requested`에도 두 항목이 들어간다.
  - 오류 문구의 "변경 요청"을 "수정 요청"으로 바꿨다.
- 스키마·migration 변경:
  - `workforce/migrations/0007_personal_info_request_contact.py`: `personal_info_change_requests`에
    `previous_phone`(20), `previous_address`(255), `requested_phone`(20), `requested_address`(255) 추가.
    모두 NULL 허용이다.
  - 백엔드를 배포하기 전에 0007을 먼저 적용해야 한다. 적용 전에는 수정 요청 조회·생성이 실패한다.
    staging 리허설 후 공유 DB에 적용한다(OPS-01).
  - 이 테이블은 Notion의 `employee_change_requests`와 다른 구조로, 정본 구조 검토(HR-01)가 아직 남아 있다.
- 환경변수·인프라 영향: 없음.

## 검증

- 실행한 테스트 (origin/dev `220a290` 병합 후):
  - backend: `ruff check .`, `manage.py check`, `pytest` 503 passed, `makemigrations --check --dry-run`
    No changes. migration 생성 때 로컬 PostgreSQL 연결이 없어 이력 일관성 경고만 나왔다(DB 접속·쓰기 없음).
  - frontend: `bun test ./tests` 53 pass, `bun run lint`, `bun run build` 통과.
  - 추가·수정 테스트: 연락처·주소 수정 요청이 승인 후에만 반영되고 빈 값은 미등록이 됨, 본인 PATCH 405,
    지움 요청 검증, `previous` 응답 항목, HR_MANAGER 역할 전용 메뉴 노출(superuser·급여담당자·미로그인 숨김).
- 남은 검증:
  - 일반 사원·인사관리자 세션으로 실제 서버·브라우저에서 메뉴 노출, 수정 요청 제출·승인·반려 확인
  - 0007 staging 리허설과 공유 DB 적용

## 미결정 사항

- superuser 노출: `HR_MANAGER` 역할이 없는 superuser에게도 사원·조직 메뉴를 숨겼다. 서버 API는
  superuser를 HR 관리자로 허용하므로, 이 차이를 유지할지 확인이 필요하다.
- 인사관리자 본인 요청의 처리자: 현재는 HR인 소속 부서장, 없으면 superuser가 처리한다. "승인은
  인사관리자"와 본인 승인 금지를 어떻게 조합할지 결정이 필요하다(HR-03).
- 처리함·승인 메뉴 노출: change-queue·change-review는 지금 모든 사용자의 내 정보 메뉴에 보인다.
  인사관리자에게만 보일지 결정이 필요하다.
- 대기 요청 1건 제한: 화면은 대기 요청이 있으면 `수정` 버튼을 막는다. 1건 제한 자체는 HR-03 미확정이다.

## 공용 문서 반영 후보

- Notion 원문 (02 비즈니스 규칙, 03 기능 명세, 04 상세 기능):
  - **HR-002 개인정보 수정 권한 분리** — 사원은 내 정보에서 연락처·주소·사내 이메일·급여계좌를 수정하고,
    수정완료 시 개인정보 수정 요청으로 제출한다. 수정 내용은 인사관리자가 승인해야 반영되며 반려되면
    기존 값을 유지한다. 부서·직급·재직상태 등 핵심 인사정보는 인사관리자만 변경한다.
  - HR-003·HR-011: "승인형 개인정보 변경 요청" → "개인정보 수정 요청".
  - HR-012: 제목 "개인정보 수정 이력 보존". 본문 예시는 "연락처·주소·사내 이메일·급여계좌 수정 요청 등".
  - 기능명:
    - FN-HR-002 내 정보 수정
    - FN-HR-003 개인정보 수정 요청 제출
    - FN-HR-004 개인정보 변경 승인·반려
    - FN-HR-005 개인정보 수정 요청 결과·이력 조회
    - FN-HR-011 대기 개인정보 수정 요청 취소
  - FN-HR-002 상세 신설
    - Actor: 사원
    - 진입: 내 정보에서 `수정` 버튼
    - 입력: 연락처·주소·사내 이메일·급여계좌 중 바꿀 항목
    - 처리: 같은 화면에서 편집한다. 즉시 반영하지 않고 `수정완료` 때 바뀐 항목만 FN-HR-003으로 제출한다.
    - 종료: 요청이 `대기`가 되거나, 수정을 취소해 보기 모드로 돌아간다.
  - FN-HR-003 상세의 진입 조건을 "내 정보 수정 모드에서 `수정완료`를 누른 경우"로 바꾼다.
  - 05 미확정 정책: "개인정보 변경 요청 상태" → "개인정보 수정 요청 상태".
- 저장소 명세·README:
  - `docs/specs/notion/06-api-specification.md` 7.1
    - 제목을 "본인 인사정보와 개인정보 수정 요청"으로 바꾼다.
    - PATCH 행을 지우고, GET 행에 "본인 직접 수정(PATCH)은 없음(405)"을 적는다.
    - 수정 요청 본문 설명을 위 API 변경으로 바꾼다.
  - `docs/specs/notion/08-table-specification.md` 변경 요청 행: 0007 컬럼 추가를 기록한다.
  - `docs/specs/notion/workforce-implementation-map.md`
    - FN-HR-002: 수정 모드와 수정 요청 제출, PATCH 제거
    - FN-HR-003: 요청 항목 5개(0007)
    - 후속 구현: 0007 공유 DB 적용
  - `docs/guides/frontend-foundation-contracts.md`
    - 메뉴 노출 정책: workforce는 `requiredRole: HR_MANAGER`, profile 수정은 승인 후 반영
    - profile 행: 화면 4개, my-profile에 수정 모드
    - query 계약: my-profile `saved=contact` → `saved=request`
  - `docs/guides/frontend-module-delivery.md`
    - F2 이름: "내 정보·수정 요청"
    - F3 경계: HR_MANAGER 전용 메뉴
    - 화면 배정표: contact-edit·change-request는 my-profile 수정 모드로 통합. change-queue는 "개인정보
      수정 요청 처리함", change-review는 "개인정보 변경 승인·반려"
    - F2·F3 모듈별 지시도 이에 맞게 고친다.
  - `docs/specs/notion/05-open-policies.md`: 위 명칭 변경.
