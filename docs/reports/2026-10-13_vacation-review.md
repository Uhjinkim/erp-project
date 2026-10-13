# 휴가 모듈 명세·구현 검토

- 검토일: 2026-10-13
- 기준: `dev`, 검토 시작 시 작업 트리 변경 없음
- 범위: `backend/vacation`, 휴가 승인선에 연결되는 workforce 코드, 인증·설정, 관련 테스트
- 제품 기준: 저장소 Notion 스냅샷 `02-business-rules.md`, `03-feature-specification.md`, `04-detailed-features.md`
- 구현 기준: `06-api-specification.md`, `08-table-specification.md`, 2026-09-18·19 작업 보고서
- Notion 원문 직접 조회, 공유 PostgreSQL·Redis 접속 및 변경은 수행하지 않았다.
- 애플리케이션 코드는 수정하지 않았으며 이 보고서만 추가했다.

## 결론

기존 테스트는 통과하지만 LV-001 잔여일수 제한, LV-004 부서장 승인선,
LV-008 주요 변경 내용 보존이 구현에서 충족되지 않는다. 사유 길이의 저장 제약 불일치와
존재하지 않는 유형의 오류 응답도 수정이 필요하다. API·테이블 문서에는 현재 코드와 다른
설명이 있으며, API 문서가 현재 동작을 설명한다는 이유로 제품 규칙 충돌이 해소되지는 않는다.

## 확인된 오류·명세 충돌

### V-01 · 높음 · 잔여일수 누적 제한을 우회할 수 있음

- 기준: LV-001, FN-LV-001, FN-LV-007.
- 근거: [service.py](../../backend/vacation/application/service.py)의 `request_vacation`,
  `resubmit`, `approve`, `_ensure_balance`와
  [workforce_gateways.py](../../backend/vacation/infrastructure/workforce_gateways.py)의 `DjangoLeaveBalanceGateway`.
- 잔여일수는 신청·재신청 전에 읽기만 한다. 승인 시 잔여일수 재검증·차감이 없고,
  회수 시 복원도 없다. 잔여 행을 잠그거나 기존 신청·승인 사용량을 합산하는 경로도 없다.
- SQLite에서 DB 어댑터로 잔여 1일인 사원의 1일 신청 두 건을 생성하고 모두 승인했다.
  승인 합계는 2일인데 `remaining_days`는 여전히 1일이었다. 동시 요청 없이도 재현된다.
- 수정 방향: 차감/예약 시점과 회수·반려·취소의 복원 정책을 결정하고 동일 트랜잭션에서
  잔여 행 잠금·검증·변경 및 이력을 처리한다. 요청 행만 잠그는 것으로는 해결되지 않는다.
- 외부 DB trigger 또는 별도 잔여 관리 작업의 존재는 확인하지 않았다. 저장소 구현에는 없다.

### V-02 · 높음 · 부서장 신청에서 상위 부서장 승인을 건너뜀

- 기준: LV-004는 상위 부서장 우선, 결정 불가 시 인사관리자 승인이다.
- 근거: [services.py](../../backend/workforce/application/services.py)의 `resolve_vacation_approver`,
  [gateways.py](../../backend/workforce/infrastructure/gateways.py)의 `department_head`,
  [policies.py](../../backend/workforce/domain/policies.py)의 `choose_vacation_approver`.
- 자기 부서장이 신청자이면 곧바로 `HR_LEAVE_APPROVER` fallback으로 이동한다.
  `Department.parent`가 존재하지만 승인자 탐색에서 사용하지 않는다.
- 재직 중 상위 부서장이 있고 HR fallback 담당자가 없는 조직을 SQLite에 구성했을 때,
  승인자 결과는 상위 부서장이 아닌 `None`이었다. 해당 부서장의 신청은 거절된다.
- API 문서 6.4와 2026-09-19 보고서는 현재 fallback 동작을 설명하지만 LV-004와 충돌한다.
  `HR_MANAGER`와 별도 `HR_LEAVE_APPROVER`의 제품상 관계도 정리해야 한다.
- 수정 방향: workforce 승인자 조회 포트를 통해 상위 조직을 탐색하고, fallback 적용 조건과
  인사 승인 담당자 역할을 제품 기준에 맞춘다.

### V-03 · 높음 · 정정 전후 주요 내용을 이력에서 복원할 수 없음

- 기준: LV-008은 처리자·시각·사유뿐 아니라 주요 변경 내용도 기록하도록 요구한다.
- 근거: [service.py](../../backend/vacation/application/service.py)의 `resubmit`, `_record`,
  [entities.py](../../backend/vacation/domain/entities.py)의 `VacationHistory`,
  [models.py](../../backend/vacation/infrastructure/models.py)의 `LeaveRequestHistoryModel`.
- 재신청은 유형·기간·사용일수·승인자·신청 사유를 현재 행에 덮어쓴다.
  이력에는 이전/다음 상태, 처리자, 사유, 시각만 저장한다.
- SQLite에서 기간과 사용일수를 변경해 재신청한 뒤 확인했다. 이전 기간·사용일수를
  보존하는 필드나 별도 저장 경로가 없어 이력 API로 변경 내용을 복원할 수 없다.
- 수정 방향: 변경 전후 값 또는 버전별 스냅샷을 도메인·DTO·ORM·API에 함께 반영한다.
  현재 테이블 명세 자체도 LV-008 요구를 표현하지 못한다.

### V-04 · 중간 · 긴 신청 사유가 PostgreSQL 저장 시 실패할 수 있음

- 근거: [serializers.py](../../backend/vacation/presentation/serializers.py)의
  `VacationRequestInputSerializer.reason`에는 길이 제한이 없다. 신청 사유는 TextField지만,
  `_record`는 같은 문자열을 이력의 `reason` CharField(max_length=255)에 저장한다.
- 256자 사유가 serializer 검증을 통과하고, 저장 대상 이력 필드가 255자 제한임을 확인했다.
  신청과 재신청 모두 같은 경로를 사용한다.
- 실제 PostgreSQL 컬럼이 명세의 varchar(255)라면 저장 오류가 발생한다. 해당 오류는
  VacationError로 변환되지 않아 통제된 400 대신 서버 오류가 될 수 있다. 트랜잭션은 롤백된다.
- SQLite는 varchar 길이를 강제하지 않으므로 기존 API 성공 테스트로 이 오류를 검출할 수 없다.
  공유 PostgreSQL에서 직접 재현하지 않았다.
- 수정 방향: 신청 사유와 변경 사유의 의미·허용 길이를 정리하고 입력·이력 저장 제약을 일치시킨다.

### V-05 · 중간 · 없는 휴가 유형이 잘못된 오류로 응답됨

- 기준: API 명세 6.9는 없는 유형을 404 `type_not_found`로 정의한다.
- 근거: `request_vacation`·`resubmit`은 유형 존재 확인보다 잔여 검증을 먼저 수행한다.
  DB 잔여 어댑터는 유형과 잔여 행이 모두 없으면 0을 반환한다.
- DB 어댑터로 없는 유형을 신청하자 `VacationTypeNotFoundError` 대신
  `InsufficientLeaveDaysError`가 발생했다. 뷰 매핑상 400 `insufficient_leave_days`가 된다.
- 수정 방향: 유형 존재를 먼저 검증한 뒤 해당 유형의 잔여 정책을 검사한다.

### V-06 · 낮음 · 개발 모드 유형 조회에서 재직 검증 누락

- 기준: API 명세의 유형 조회 권한은 식별된 재직 사원이다.
- 근거: [views.py](../../backend/vacation/presentation/views.py)의 `VacationTypeListView`는
  사번 파싱만 수행하고 `list_types`는 `_ensure_active`를 호출하지 않는다.
- 개발 사원 설정을 비운 상태에서 존재하지 않는 사번 헤더로 유형 목록을 요청해 200을 확인했다.
- 운영 세션 모드는 인증 계층에서 재직 사원을 검증하므로 동일한 운영 인증 우회로 단정하지 않는다.
- 수정 방향: 개발/DB 모드 모두 동일한 재직 조건을 적용하고 서비스 권한 계약을 명확히 한다.

## 추가 정책·문서 확인 사항

1. **자기 승인 가능 경로**: 신청자가 부서장이면서 유일한 HR_LEAVE_APPROVER이면 fallback이
   신청자 자신을 반환한다. 도메인 approve도 신청자와 승인자가 동일한 상황을 막지 않는다.
   순수 정책 재현으로 확인했다. 현재 명세에 독립적인 자기 승인 금지 규정은 없으므로
   별도의 확정 위반으로 계산하지 않는다. LV-004 승인선 수정과 함께 제품 결정을 기록해야 한다.
2. **잔여 정보 누락 처리 문서 불일치**: API 6.4는 잔여 정보가 없으면 검사를 생략한다고 설명한다.
   실제 DB 모드는 차감형 휴가에서 0일로 처리해 거절하며, 개발 모드만 None을 반환해 생략한다.
   두 모드의 차이와 비차감형 유형 예외를 명시해야 한다.
3. **사원 FK 매핑 차이**: 테이블 명세의 leave_requests.emp_no·approver_no,
   leave_request_history.actor_emp_no는 employees FK로 표시되지만 모델·초기 migration state는
   IntegerField다. 공유 DB의 실제 FK 존재 여부는 미확인이다. Django 삭제 보호와 테스트에서는
   해당 참조 무결성이 표현되지 않으므로 레거시 스키마 조사 후 의도적인 매핑 여부를 정리해야 한다.
4. **재신청 승인선 표현 차이**: 상세 명세 FN-LV-007 종료 조건은 기존 승인선이라고 쓰고,
   처리 설명과 API 6.7·구현은 현재 조직 기준으로 승인자를 다시 결정한다.
   조직 변경 시 기존 승인자를 유지할지 재배정할지 명확히 해야 한다.
5. 기간 중복, 휴일·근무일 계산, 유형별 사용일수 자동 산정은 현재 구현에 없다.
   과거 보고서에서도 후속 정책으로 남겼으므로 이번 검토에서는 확정 규칙 위반으로 분류하지 않았다.

## 정상 확인 사항

- domain/application은 Django·ORM에 의존하지 않고 포트를 통해 외부 기능을 참조한다.
- 요청·상태 변경과 이력 저장은 동일 Unit of Work 트랜잭션 안에서 처리된다.
- 상태 변경은 요청 행에 select_for_update를 적용한다.
- 본인 대기 신청 취소, 현재 승인자 승인·반려, 기존 승인자 회수,
  회수 후 본인 재신청 제한은 LV-005~LV-007의 기본 흐름과 일치한다.
- DB 식별 모드는 세션 연결 사원을 사용하고 개발 사번 헤더를 신뢰하지 않는다.

## 검증 결과와 한계

- 기존 휴가 domain/service/API: 6건 통과.
- 기존 accounts/workforce 연동 및 health/API 준비 상태: 22건 통과.
- 임시 합성 재현: 7건 통과. 위 결함이 현재 구현에서 발생함을 확인하는 테스트이며
  수정 완료를 의미하지 않는다. 임시 파일은 실행 후 삭제했다.
- Ruff: vacation 및 기존 휴가 테스트 검사 통과.
- Django system check: config.settings.test에서 통과.
- 모든 DB 재현은 인메모리 SQLite, 나머지는 순수 Python 또는 serializer 검사였다.
- 전체 백엔드 테스트, frontend 검증, migration drift 검사는 실행하지 않았다.
  코드·모델·마이그레이션 변경은 없으며 공유 PostgreSQL의 길이 제약·FK·trigger·배포 상태는 미확인이다.
- 공유 DB·Redis 변경, migration 적용, Notion 갱신, 외부 메시지 전송은 수행하지 않았다.

## 권장 처리 순서

1. V-01 잔여 차감·예약 정책 및 원자적 처리, V-02 상위 승인선 처리.
2. V-03 이력 구조 보완과 기존 데이터 보존 계획.
3. V-04 사유 길이 정합성, V-05 오류 매핑, V-06 재직 검증 회귀 테스트.
4. 모드별 API 문서와 제품 규칙·테이블 명세의 차이 정리.
   공유 DB 스키마 변경은 환경·권한 확인 및 별도 승인 후 진행한다.
