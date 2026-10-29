# 기여 문서 통합 현황

- 최신 검토일: 2026-10-28, dev 5dc4415
- 직전 검토일: 2026-10-14, dev 4f77219
- 이전 검토일: 2026-10-12 (부분 통합 기록 보존)

| 기여 묶음 | 공용 반영한 변경 | 남은 충돌 | 검토 파일 |
| --- | --- | --- | --- |
| workforce 백엔드 | 등록·퇴사·재입사·발령/정정/취소 API, identity·추가 이력 구현 | HR-01~03, OPS-01·CRUD 우회/시퀀스 | [검토](./workforce/feature-workforce-employee-info/integration-review.md) |
| workforce UI | 7개 화면과 query 계약 | 시안·오류 계약·실제 세션 | [검토](./workforce/feature-workforce-ui-screens/integration-review.md) |
| profile UI | 6개 화면·조회/수정 분리·처리함 연결 | HR-01~03·실제 처리자 | [검토](./profile/feature-workforce-ui-screens/integration-review.md) |
| vacation | 7개 화면, 기존 잔여·승인선·스냅샷 수정 기록 유지 | UI-LV-01/02·실제 잔여/권한 검증 | [검토](./vacation/feature-vacation-ui-screens/integration-review.md) |
| board | 3개 메뉴·조회 상태·권한/자격 응답 | BD-01~03 | [검토](./board/board/integration-review.md) |
| evaluation | 전용 targets·4개 화면 | EV-01/02 | [검토](./evaluation/bae/integration-review.md) |
| payroll | 전용 employees·5개 화면·지급일/xlsx 계약 | PY-01/02 | [검토](./payroll/sylee/integration-review.md) |

INT-01의 HR 전체 사원 목록 의존과 UI-HR-02의 처리함 공백은 구현으로 해결하고 공용 계약에 반영했다.
각 모듈의 제품 정책 전체·실제 공유 환경·디자인 검증 완료를 뜻하지 않는다.
해결된 내용과 미결 항목이 한 기여 묶음에 함께 있어 원본 README·세부 문서·과거 보고서는 유지한다.
검토 결과는 별도 integration-review.md에 기록한다.

- [최신 분류·통합 보고서](../reports/2026-10-14_contribution-docs-integration.md)
- [최신 미결 의제](../reports/2026-10-14_module-review-agenda.md)
- [2026-10-12 통합 보고서](../reports/2026-10-12_contribution-docs-integration.md)
- [2026-10-12 의제](../reports/2026-10-12_module-review-agenda.md)
- [의제 공유 양식](../guides/module-review-agenda.md)

## 2026-10-28 추가 통합

workforce/jyoun·profile/jyoun의 2026-10-27 사용자 결정을 코드와 대조해 반영했다.
연락처·주소 승인 요청 전환, 본인 PATCH 제거(405), 수정 요청 5개 항목, workforce 0007,
profile 4개 화면과 HR_MANAGER 전용 workforce 메뉴가 대상이다.
평가 targets 일괄 조회와 실패 입력 유지·본인 평가 HR 액션 숨김도 현재 구현 계약에 기록했다.
기존 EV-01/02·HR-01/02 및 HR-03의 미결 항목은 유지한다.
원본 기여 문서는 보존하며 Notion 조회·수정은 연결 부재로 수행하지 못했다.
[최신 통합·배포 준비 보고서](../reports/2026-10-28_documentation-deployment-readiness.md)를 따른다.

## 2026-10-29 배포 UI 정리·역할 검수

공통 컴포넌트 전시·연결 상태 UI와 health 폴링을 제거했다. 격리 SQLite와 실제 세션 API를
사용한 역할별 브라우저 검수 결과·미완성 동선·검증 한계는
[역할별 검수 보고서](../reports/2026-10-29_role-browser-release-review.md)를 따른다.
권한 정책 확정·공유 환경 검증·배포 완료를 뜻하지 않는다.


역할별 메뉴·기본 진입과 급여 자기 처리 사전 차단을 보완하고 미완성 홈·계정 관리 메뉴를 배포 등록에서
제외했다. 2026-10-29 사용자 선택에 따라 superuser의 사원·조직 UI 접근을 기존 서버 권한과
일치시켰다. [보완·재검수 보고서](../reports/2026-10-29_release-ux-improvements.md)를 따른다.


## 2026-10-29 연결 재사용·반복 질의 보완

개발 PostgreSQL 풀과 인증·공지 자격·개인정보 처리함의 반복 조회 감소를 구현했다.
응답·처리자 정책·스키마는 유지하며 목록 캐시를 명령 권한으로 재사용하지 않는다.
[성능 보완 보고서](../reports/2026-10-29_database-query-improvements.md)에 쿼리 회귀·524개 테스트와
실제 터널 연결 거부로 미완료한 실측을 구분해 기록했다. 공유 서비스 쓰기·배포는 수행하지 않았다.

- 연결 실패 후속: 개발 접속/풀 대여 기본값을 10초/15초로 보정하고 통합 서버 기동과 실제 DB 세션 재사용을 확인했다. Redis 상태 점검 제한에 따른 실패는 별도 잔여 사항이다. [검증 기록](../reports/2026-10-29_database-query-improvements.md#6-연결-실패-후속-수정)

- 개발 Redis 상태 점검 10초 대기·메뉴 검색 상단 배치와 실측/브라우저 검증: [보완 기록](../reports/2026-10-29_health-timeout-menu-layout.md).

- Lucide 업무/하위 메뉴 아이콘·선택 상태 적용과 브라우저 검수: [적용 기록](../reports/2026-10-29_lucide-business-icons.md).

- 모바일/데스크톱 본문 폭·표 정렬·가로 넘침 수정과 17개 화면×6개 폭 검수: [배치 검토](../reports/2026-10-29_responsive-layout-review.md).


- 휴가 신청·재신청 화면에 유형별 잔여일수 표시, 입력 유지 새로고침, 부족 안내를 추가했다.
  기존 유형 요청에 본인 잔여를 함께 받고 DB/개발 어댑터는 일괄 조회한다.
  [구현·검증 기록](../reports/2026-10-29_vacation-request-balances.md).

- 휴가 잔여 확인 불가 후속: 이전 유형 데이터의 자동 1회 재조회와 최신 props 반영,
  서버 잔여 필드 누락의 명시적 오류를 보완했다. 정상 요청 수 유지, 프론트 61개 테스트와
  합성 브라우저 복구 검증은 위 휴가 잔여 보고서에 기록했다.

- 사용자 확정에 따라 반차와 연차의 잔여를 공유하도록 조회·검증·승인 차감·회수 복원과 신청 UI를
  일치시켰다. [반차 보완 기록](../reports/2026-10-29_half-day-annual-balance.md).

- 배포 화면의 서버 구현 설명·내부 규칙 번호·반복 안내를 정리하고 실제 오류/처리 결과와 중요한
  확인 문구는 유지했다. [문구 정리 기록](../reports/2026-10-29_release-copy-cleanup.md).

- SSH 반복 종료/API 호출 연관 제보: 실제 health API 6회·SSH PID 유지 확인, 원격 로그 인증 제한과
  다음 실행용 선택 진단 로그 옵션을 [진단 기록](../reports/2026-10-29_ssh-tunnel-diagnostics.md)에 남겼다.

- 휴가 신청 기본값을 현지 오늘 09:00~18:00으로 설정하고 시작 09:00 이전 입력 차단,
  초 선택 제거·전송 초 00 고정을 적용했다. [시간 입력 보완 기록](../reports/2026-10-29_vacation-request-time-defaults.md).

- 브라우저 시간대에 의존하던 휴가 입력/전송과 업무 이력 표시·오늘 날짜를 Asia/Seoul로 통일했다.
  [시간대 확인·검증 기록](../reports/2026-10-29_seoul-business-time.md).

- 사번이 필요한 사원 상세·인사 이력은 사이드바/메뉴 검색에서 제외하고 사원 목록의 대상 링크와
  상세 내 이력 탭 진입을 유지했다. 라우팅 테스트·프론트 lint/build 통과. API/DB 변경 없음.

- Ubuntu 26.04.1 빈 EC2의 OS/rootless Docker·IAM/Secret·GitHub OIDC·SSM 검증과 최초 DB 준비를
  [AWS 배포 안내](../guides/github-actions-aws-deployment.md)에 정리했다. 파일 없는 Secret 주입/Actions
  자동화는 미구현으로 구분했다. 원격 작업 없음. [검증 기록](../reports/2026-10-29_aws-deployment-guidance.md).
