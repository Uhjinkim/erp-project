# Notion ERP 명세 인덱스

이 디렉터리는 Notion `ERP 프로젝트`의 확정 명세를 구현 관점에서 추적하기 위한
Markdown 스냅샷이다. Notion이 원문(source of truth)이며, 코드 변경 시 관련 문서와
구현 대응표를 함께 갱신한다.

## 설계 명세 스냅샷

- [00. Django 모듈화 전략](./00-django-modularization.md)
- [01. 개요·Actor·상태](./01-overview-actors-states.md)
- [02. 비즈니스 규칙](./02-business-rules.md)
- [03. 기능 명세](./03-feature-specification.md)
- [04. 핵심 기능 상세](./04-detailed-features.md)
- [05. 미확정 정책](./05-open-policies.md)
- [06. API 명세](./06-api-specification.md)
- [07. 테이블 설계 결정안](./07-table-design-decisions.md)
- [08. 테이블 명세](./08-table-specification.md)

## 구현 대응 문서

- [Workforce 명세 구현 대응표](./workforce-implementation-map.md)

## 기여 문서 부분 통합

- [2026-10-12 통합 보고서](../../reports/2026-10-12_contribution-docs-integration.md)
- [모듈 담당자 검토 의제](../../reports/2026-10-12_module-review-agenda.md)
- [의제 공유 양식](../../guides/module-review-agenda.md)

02·03·04 원문 확인일: 2026-10-12. 다른 스냅샷의 확인일은 각 문서의 메타데이터를 따른다.
추가 정책·충돌 항목은 통합하지 않았으며, 현재 구현 기록은 제품 정책 승인·배포 완료를 의미하지 않는다.

06·08은 2026-10-12 Notion 부분 반영과 재조회 확인을 완료했다. 반영 범위는 통합 보고서를 따른다.

2026-10-13 휴가 코드 수정에 따른 06·08 저장소 변경은
[수정 보고서](../../reports/2026-10-13_vacation-fixes.md)를 따른다. Notion 원문 갱신은 수행하지 않았다.
공유 개발 DB `erp_dev.public`에는 2026-10-13 사용자 대상 확인 후 vacation 0003을 적용했다.

로컬에 남아 있던 휴가 수정과 원격 dev의 다른 모듈을 함께 반영한 결과는
[2026-10-13 원격·로컬 통합 확인](../../reports/2026-10-13_dev-local-integration.md)에 기록한다.


## 2026-10-14 기여 문서 구현 통합

dev 4f77219를 기준으로 [유지·변경·충돌](../../reports/2026-10-14_contribution-docs-integration.md)을
분류했다. 해결된 업무 대상 조회·화면 진입, 누락된 HR 생애주기/이력 API와 현재 테이블 구현을
06·08·workforce 대응표 및 공용 토대 계약에 반영했다. 02·03·04·07의 원문 정책은 유지했다.
[최신 미결 의제](../../reports/2026-10-14_module-review-agenda.md)와
[기여 통합 현황](../../contributions/integration-status.md)을 함께 확인한다.
이번에는 Notion 원문을 조회·수정하지 않았으며 원문 확인일을 최신 코드 확인일로 바꾸지 않았다.
