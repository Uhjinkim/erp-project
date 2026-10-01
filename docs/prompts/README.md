# 사원조회 모듈화 프롬프트 모음

`workforce` 앱의 "사원조회" 기능을 범위별로 나눠 구현하기 위해 작성한 프롬프트
모음이다. 각 파일은 실행 시점에 그대로 복사해서 사용할 수 있는 완결된 프롬프트이며,
구현이 끝난 항목은 실제로 어떻게 구현됐는지를 파일 하단에 기록한다.

- [01-본인-정보-조회.md](01-본인-정보-조회.md) — `FN-HR-001`, 완료 (`workforce`
  domain/application/infrastructure 계층으로 모듈화까지 완료)
- [02-퇴사자-조회.md](02-퇴사자-조회.md) — 인사관리자 전용, 미착수
- [03-사원-디렉토리-검색.md](03-사원-디렉토리-검색.md) — Notion 미확정 신규 항목, 미착수

## 배경

- 관련 스펙: `docs/specs/notion/03-feature-specification.md`,
  `docs/specs/notion/05-open-policies.md`,
  `docs/specs/notion/workforce-implementation-map.md`
- 대상 앱: `backend/workforce/` (DDD 계층 구조는 `backend/vacation/`을 표준으로 따름)
- 작업 보고서: `docs/reports/2026-09-22_사원_본인정보_조회_모듈화_작업_보고서.md`
