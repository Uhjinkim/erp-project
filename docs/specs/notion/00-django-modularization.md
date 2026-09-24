# 00. Django 모듈화 전략: DDD + 클린 아키텍처

- Notion 원문: <https://app.notion.com/p/3da8eced448d81519b49f8d1edf23eda>
- 원문 최종 수정: 2026-09-13
- 저장소 확인: 2026-09-19

## 핵심 결정

Django app을 휴가, 인사, 게시판, 급여, 평가 같은 바운디드 컨텍스트로 나누고,
각 app 내부를 다음 네 계층으로 구분한다.

- `domain/`: 순수 Python 엔티티, 값 객체, 정책, 예외, 저장소 인터페이스
- `application/`: 유스케이스와 입출력 DTO; 추상 포트에만 의존
- `infrastructure/`: Django ORM, 저장소와 외부 시스템 어댑터
- `presentation/`: DRF serializer, view, URL; 조립·호출·응답 변환 담당

의존성은 바깥에서 안쪽으로 향한다. `domain/`은 Django를 import하지 않으며,
`application/`은 구체 infrastructure 구현을 import하지 않는다. Serializer는 입력
형태만 검증하고 업무 규칙은 domain/application에서 처리한다. Signal에 핵심 업무
흐름을 숨기지 않는다.

테스트는 domain → application(fake port) → infrastructure/presentation 순서로 구성한다.
