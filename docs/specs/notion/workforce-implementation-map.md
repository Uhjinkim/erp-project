# Workforce 명세 구현 대응표

- Notion 테이블 결정안: <https://app.notion.com/p/3d78eced448d81e99cd6fb0d87399979>
- Notion 테이블 명세: <https://app.notion.com/p/3d78eced448d8124b3b4d00cd2c0b5f3>
- 점검일: 2026-10-14 (dev 4f77219 코드·기여 대조; 공유 DB·Notion 재확인 아님)

## 현재 구현

- Person과 Employee를 1:N으로 연결해 `HR-006` 재입사 신규 사번을 수용한다.
- 사번은 PK로 유지하고 변경 API를 제공하지 않는다(`HR-007`).
- 이메일 UNIQUE, 퇴사 상태/퇴사일 일관성, 부서 계층 순환, 재직 부서장을 검증한다.
- 역할은 EmployeeRole의 부여·해제 시각으로 판정하며 미래 부여는 활성 권한이 아니다.
- 휴가 승인자는 본인 외 재직 부서장, 신청자가 부서장이면 직계 상위 재직 부서장,
  결정 불가 시 단일 활성 HR 휴가 승인담당자 순서로 결정한다.
- workforce 도메인 정책은 순수 Python `domain/`, 포트와 유스케이스는 `application/`,
  Django ORM·gateway·signal·admin은 `infrastructure/`, DRF API는 `presentation/`으로
  분리했다. 루트 `models.py`와 `admin.py`는 Django 자동 탐색을 위한 re-export 진입점이다.
- 역할 부여·회수는 presentation에서 ORM을 직접 변경하지 않고 application command를 거친다.
- architecture test가 domain/application의 바깥 계층 import를 차단한다.

## 기존 기능의 부분 구현 확인

- FN-HR-001: 본인 상세 조회 경로가 있고 사원 상세는 본인/HR로 제한한다.
- FN-HR-002: phone·address 직접 수정 경로가 있다. 내선번호 범위는 HR-03 검토 대상이다.
- FN-HR-003~005·FN-HR-011: 대기 요청 생성·승인·반려·취소·조회 경로가 있다.
  기존 요청 테이블과 다른 구조 및 추가 처리자 규칙이 있어 전체 준수 완료로 표시하지 않는다.
- HR-007: 사원 수정 경로에서 다른 사번을 보내면 거절한다.
- 상세·본인 응답의 계좌 보호와 변경 이력 요구는 HR-02 해결 후 완료 판단한다.
- 사원 목록 HR 제한은 유지한다. 평가 targets·급여 employees로 전체 목록 의존을 제거해
  INT-01 구현 충돌은 해결했다. 실제 비HR 화면 검증은 후속이다.

[모듈 담당자 의제](../../reports/2026-10-14_module-review-agenda.md)를 확인한다.

## 2026-10-14 기존 기능 구현 보완

| 기능 | 현재 구현 | 기준·미완료 구분 |
| --- | --- | --- |
| FN-HR-006 | onboarding domain/application, ORM UoW·계정 gateway; 신규 사번·역할·계정·최초 이력 동시 등록 | HR-007/008 유지, 미래 입사·비밀번호·직접 사번 경로는 HR-03/OPS-01 |
| FN-HR-007/008 | lifecycle terminate·terminated API; 퇴사 후 인증 차단·기록 보존 | HR-004/005/009 유지; 예약/취소 등은 범위 미결 |
| FN-HR-009 | 동일 Person의 새 Employee와 선택 계정 생성, Person 잠금 | HR-006/007 유지; 세부 날짜/정보 갱신은 현재 구현 계약 |
| FN-HR-010 | 기간 중복 없는 발령, 최근 진행 이력 정정/취소·부서장 해제/복원·전후 기록 | emp_history_changes 구현, 정정·취소 운영 조건은 HR-03 검토 |
| F2/F3 UI | profile 6개·workforce 7개 화면 | HR 처리함 공백 해소(UI-HR-02), 시안 대조(UI-HR-01)·실제 서버 검증 대기 |

등록·계정 연결 transaction use case와 FN-HR-006~010을 미구현 목록에서 제외한다.
API 계약은 [06. API 명세](./06-api-specification.md), 현재 추가 이력 정의는
[08. 테이블 명세](./08-table-specification.md), 정책 차이는
[최신 의제](../../reports/2026-10-14_module-review-agenda.md)를 따른다.

## 후속 구현

- `HR-012` 보존·파기, 계좌 보호 요구 미완료(HR-02)
- 변경 요청 테이블 차이(HR-01), 추가 승인선·입력 정책(HR-03)
- 평가·급여 전용 대상자 API의 실제 비HR 브라우저 확인(INT-01 구현 해결 후 검증)
- 개인정보 마스킹·암호화·감사로그 및 보존/파기 정책
- 실제 PostgreSQL의 nullability, FK 삭제 정책, UNIQUE/배타 제약 read-only 대조

공유 DB에 적용하기 전에는 별도 staging에서 migration을 리허설하고 승인받는다.
