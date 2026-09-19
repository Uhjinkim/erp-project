# Notion 모듈화 전략 분석 및 Workforce 개선 보고서

- 작업일: 2026-09-19
- 기준: Notion `ERP 프로젝트`의 DDD + 클린 아키텍처, 01~05 명세, 테이블 결정안
- 데이터 안전: 공유 PostgreSQL/Redis 쓰기 작업 없음

## 원문 분석 결론

Notion 전략의 핵심은 Django app 자체를 업무 바운디드 컨텍스트로 보고, app 내부에서
domain/application/infrastructure/presentation 책임을 분리하는 것이다. 특히 domain의
Django 비의존, application의 포트 의존, view의 조립 책임, serializer의 전송 형식 검증
범위가 강한 규칙이다.

기존 workforce는 Django 모델, ORM 조회, 권한 판정, 승인자 정책이 평면 파일에 섞여 있었다.
또한 Person–Employee가 1:1이라 재입사 시 새 사번을 발급한다는 `HR-006`과 구조적으로
충돌했고, 미래 시점 역할도 일부 응답에서 활성 권한처럼 보일 수 있었다.

## 반영 사항

- 순수 Python 정책과 예외를 `workforce/domain/`으로 분리
- application 포트와 승인자 결정·역할 부여·회수 유스케이스 추가
- Django ORM 모델·gateway·signal·admin을 `workforce/infrastructure/`로 분리
- DRF serializer·permission·view·URL을 `workforce/presentation/`으로 분리
- Django 자동 탐색이 요구하는 루트 `models.py`, `admin.py`만 얇은 진입점으로 유지
- accounts와 vacation은 application service와 infrastructure gateway를 조립해 연동
- Person–Employee를 1:N으로 변경해 재입사 지원
- Employee 이메일 UNIQUE와 소문자 정규화
- 퇴사 상태와 퇴사일의 일관성 검증
- 부서장 FK 삭제 정책을 `SET NULL`로 명세와 정렬
- 역할의 부여·해제 시각을 반영해 실제 활성 권한만 판정·노출
- 재입사와 미래 역할에 대한 회귀 테스트 추가

## 남은 범위

현재 개선은 workforce의 4계층 구조와 이미 노출된 인증·조직·휴가 연동의 정합성에
집중했다. 개인정보 변경 요청, 본인 정보 범위, 사원 등록/퇴사/재입사 transaction,
인사이력 기간 중복은 별도 유스케이스와 API로 구현해야 한다. 실제 PostgreSQL 제약은
read-only introspection 및 staging migration 리허설 전에 확정하지 않는다.

## 검증

- Django system check 통과
- Ruff 통과
- migration state 차이 없음
- Backend 19 tests 통과
- Frontend ESLint 및 production build 통과
- Git whitespace 검사 통과
