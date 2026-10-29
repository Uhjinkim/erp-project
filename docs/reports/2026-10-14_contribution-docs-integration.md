# 기여 문서 재검토 · 유지·변경·충돌 분류

- 검토일: 2026-10-14
- 기준: dev를 origin/dev에서 fast-forward pull한 4f77219
- 대상: board, evaluation, payroll, workforce 백엔드·프론트, profile, vacation의 기여 문서와 현재 코드
- 비교 기준: 저장소 Notion 스냅샷 01~08, 공통 토대 계약, 2026-10-12 의제
- Notion: 이번에는 원문 조회·수정을 하지 않았다. 스냅샷의 원문 확인일은 유지한다.
- 분류: 유지 = 기존 기준과 일치, 변경 = 기존 기능의 구현·계약 갱신, 충돌 = 제품 기준과 차이 또는 미해결 요구.
  구현 사실을 공용 API에 기록하는 것과 추가 정책을 승인하는 것은 구분한다.

## 모듈별 대조표

| 모듈·관련 ID | 유지 | 변경·공용 반영 | 충돌·보류 |
| --- | --- | --- | --- |
| workforce · HR-001, HR-006~010, FN-HR-006~010 | 본인/HR 조회, 재입사 신규 사번, 이메일 중복·기간 중복 방지 | 통합 신규 등록, 퇴사·퇴사자 조회·재입사, 발령·최근 정정·취소 API 및 화면; emp_history_changes와 사번 발급 구현 | HR-01 정본 요청 테이블, HR-03 추가 운영 정책; 직접 사번 입력과 시퀀스, 일반 PATCH의 상태·소속 우회, 모델/DB nullability |
| profile · HR-002~003, HR-011~012 | 직접 수정과 승인형 변경 분리, 대기 본인 취소 | 보기 전용 my-profile, 별도 수정/요청, 내 이력·처리함·처리 화면 6개; UI-HR-02 공백 해소 | 특별 처리자·대기 1건·이메일 동기화는 HR-03; 암호화·보존/파기는 HR-02 미완료 |
| vacation · LV-001~008, FN-LV-001~008 | 지정 승인자·대기 취소·회수 후 재신청 | 7개 화면, 잔여 승인 차감/회수 복원, 상위 승인자 조회, null 호환 전후 스냅샷 | 신청 전 잔여/승인 예정 API와 HR 임의 현재 상세 없음(UI-LV-01/02); 예약 시점·기존 승인 잔여 정합성은 기존 제한 유지 |
| board · BD-001~008, FN-BD-001~007 | 일반/공지, 제목 100자, 작성 자격, 유형·분류 수정 금지 | 공지·일반·작성 메뉴 3개, 목록의 postId 상세, can_edit/can_delete·comment_count 응답, 자격 조회 | 부서 분류 제외·복수 역할 분류 선택(BD-01), 댓글(BD-02), 경영담당자 타인 삭제(BD-03 신설) |
| evaluation · EV-001~005, FN-EV-001~004 | 자기평가 금지, 서버 등급, HR 확정, 확정 본인 조회 | 4개 화면, 전용 targets API로 HR 목록 의존 제거(INT-01) | HR 겸직 작성 금지(EV-01), 제출·반려·제외·재배정 등 추가 상태·운영 기준(EV-02) |
| payroll · PY-001~009, FN-PY-001~007 | 담당자 관리·본인 조회, 확정 취소 후 수정, 저장 상태 2개·이력 이벤트 | 5개 화면, 전용 employees API(INT-01), 지급일 입력·수정, 확정 xlsx·브라우저 PDF 저장 | PY-009 최종 올림 미충족(PY-01); 25일·자기거래·확정 건 공개·이력 공개 제한(PY-02) |
| F0 · 모듈 경계/라우팅 | 공통 UI·client 소비, 기능 내부 소유 | 모든 업무 모듈 공개 진입점 연결, 삭제된 패널 설명 정정 | 시안 대조 미수행(UI-HR-01 등), field 오류 형식(UI-HR-03), backdrop prop·legacy CSS 정리는 미처리 |

## 해결된 구현과 통합 근거

- INT-01: HR 전용 전체 사원 조회 권한을 유지하면서 평가 targets와 급여 employees를 분리했다.
  비HR 부서장/급여담당자는 업무 대상만 조회한다. 내 평가 결과는 일반 사원 목록을 요청하지 않는다.
  현재 코드와 권한 회귀 테스트를 확인했다. 실제 공유 환경 브라우저 검증은 남았다.
- UI-HR-02: workforce에서 분리한 개인정보 처리함은 profile의 change-queue/change-review로 연결된다.
  라우터 회귀 테스트로 등록 화면 진입을 확인했다. 특별 처리자 정책 확정은 별개다.
- 공통 셸: ModuleScreen의 모듈 공개 진입점과 registration이 일치한다. 구형 패널 참조를
  공용 토대 사용 계약에서 제거했다. 게시판 메뉴 변경은 기여 문서의 2026-10-14 기록과 현재 등록을 대조했다.
- 인사 신규 유스케이스: 기존 FN-HR-006~010을 API·화면에 매핑했다. 오늘 이전 퇴사/발령,
  최근 이력만 정정 등 구체 운영 기준은 현재 구현으로 기록하며 Notion 확정 규칙에 추가하지 않는다.
- 휴가 정정 스냅샷: 이전 보고서·현재 코드에서 LV-008 수정과 null 호환을 확인했다.
  API/테이블 문서에 이미 반영된 내용은 유지했다.

## 공용 반영 경로

- 06-api-specification.md: 기존 기본 경로 유지, 누락된 HR 생애주기·이력과 업무 대상자 조회,
  게시판 응답 자격 필드, 지급일/엑셀 계약을 보완. 댓글·평가 확대 동작은 보류 구현 참고로 구분한다.
- 08-table-specification.md: workforce 0005·0006 구현과 emp_history_changes 컬럼을 보완.
  employee_change_requests 정본을 personal_info_change_requests로 교체하거나 기존 테이블을 삭제하지 않는다.
- workforce-implementation-map.md: 완료된 등록·퇴사·재입사·발령·UI를 반영하고 오래된 후속 구현 설명 정정.
- frontend-foundation-contracts.md / frontend-module-delivery.md: 현재 화면·공개 진입점·query 계약 반영.
- 05-open-policies.md, contribution integration-status, 모듈별 integration-review: 미결 의제와 분류를 연결.
- 02·03·04·07의 제품 규칙·기능 ID·확정 논리 구조는 유지한다. 추가 정책을 임의로 확정하지 않는다.
- 원본 기여 README·세부 문서·과거 보고서는 수정·삭제하지 않는다. 보류가 남아 삭제하지 않는다.

## 미해결 항목 처리

[최신 모듈 의제](./2026-10-14_module-review-agenda.md)에 해결 상태·근거·다음 결정과 완료 기준을 기록했다.
과거 기여 문서의 “사용자/담당자 결정” 문구는 조사 근거이며 이 통합에서 제품 승인으로 자동 채택하지 않았다.
과거 공유 DB 적용 기록은 모듈·날짜별 자기 보고이며 이번에 DB를 재확인한 결과가 아니다.
담당자 메시지 발송, schema 변경·데이터 수정·migration 실행은 하지 않았다.

## 검증

- 최신 frontend bun run test: 48개 통과(8개 파일). 라우팅·모듈 진입·UI 모델·transport 회귀 포함.
- INT-01 관련 API 3개: 비HR 부서장 targets, 일반 사원 확정 평가 조회, 비HR 급여담당자 employees 통과.
  config.settings.test의 SQLite를 사용해 공유 인프라에 쓰지 않았다.
- 변경 문서 19개 상대 링크 107개 존재 확인, 6개 모듈 공개 진입점·registration과 workforce 0005/0006 파일 참조 확인, git diff --check 통과.
- dev의 승인된 공용 문서 통합이므로 feature 브랜치 전용 문서 범위 검사는 적용하지 않는다.
- 코드·dependency·migration 파일 변경 없음. 전체 backend/frontend lint·build는 문서 변경이라 재실행하지 않았다.
- 미검증: 실제 PostgreSQL·Redis, 최신 Notion, 실제 브라우저·시안 전체 대조, 보류 정책 수용 여부.
