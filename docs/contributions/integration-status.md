# 기여 문서 통합 현황

- 최신 검토일: 2026-10-14, dev 4f77219
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
