# Workforce 명세 구현 대응표

- Notion 테이블 결정안: <https://app.notion.com/p/3d78eced448d81e99cd6fb0d87399979>
- Notion 테이블 명세: <https://app.notion.com/p/3d78eced448d8124b3b4d00cd2c0b5f3>
- 점검일: 2026-09-19

## 현재 구현

- Person과 Employee를 1:N으로 연결해 `HR-006` 재입사 신규 사번을 수용한다.
- 사번은 PK로 유지하고 변경 API를 제공하지 않는다(`HR-007`).
- 이메일 UNIQUE, 퇴사 상태/퇴사일 일관성, 부서 계층 순환, 재직 부서장을 검증한다.
- 역할은 EmployeeRole의 부여·해제 시각으로 판정하며 미래 부여는 활성 권한이 아니다.
- 휴가 승인자는 본인 외 재직 부서장, 없으면 단일 활성 HR 휴가 승인담당자 순서로 결정한다.
- workforce 도메인 정책은 순수 Python `domain/`, 포트와 유스케이스는 `application/`,
  Django ORM·gateway·signal·admin은 `infrastructure/`, DRF API는 `presentation/`으로
  분리했다. 루트 `models.py`와 `admin.py`는 Django 자동 탐색을 위한 re-export 진입점이다.
- 역할 부여·회수는 presentation에서 ORM을 직접 변경하지 않고 application command를 거친다.
- architecture test가 domain/application의 바깥 계층 import를 차단한다.

## 후속 구현

- `FN-HR-001`~`FN-HR-005`, `FN-HR-011`: 본인 정보 범위와 개인정보 변경 요청 API
- `FN-HR-006`~`FN-HR-010`: 등록·퇴사·재입사·기간 중복 없는 인사이력 유스케이스
- Person/Employee 생성과 Account 연결을 묶는 transaction use case
- 개인정보 마스킹·암호화·감사로그 및 보존/파기 정책
- 실제 PostgreSQL의 nullability, FK 삭제 정책, UNIQUE/배타 제약 read-only 대조

공유 DB에 적용하기 전에는 별도 staging에서 migration을 리허설하고 승인받는다.
