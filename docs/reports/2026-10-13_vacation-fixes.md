# 휴가 모듈 오류 수정 보고서

- 작업일: 2026-10-13
- 브랜치: dev
- 요청: 휴가 모듈 검토에서 발견한 오류 수정
- 검토 근거: [검토 보고서](./2026-10-13_vacation-review.md), LV-001·LV-004·LV-008,
  저장소 API·테이블 명세. Notion 원문 재조회·수정은 수행하지 않았다.

## 변경 결과

| 검토 항목 | 수정 |
| --- | --- |
| V-01 잔여 제한 | 승인 시 재검증·차감, 회수 시 실제 차감분 복원 |
| V-02 승인선 | 소속 부서장 신청 시 직계 상위 부서장 조회 후 HR fallback |
| V-03 정정 이력 | 변경 전후 유형·기간·사용일수·승인자·사유·승인 정보 스냅샷 저장·응답 |
| V-04 사유 길이 | 신청·재신청 사유 최대 255자를 serializer에서 검증 |
| V-05 유형 오류 | 잔여 검사 전에 유형 검증하여 없는 유형의 404 응답 보장 |
| V-06 재직 검증 | 유형 조회도 서비스에서 재직 검증 |

## 잔여일수 처리

기존 제품 규칙은 잔여 초과 금지와 승인 시 유효함을 정의하지만 예약 시점은 정의하지 않는다.
이번 구현의 기본안은 승인 시 차감·회수 시 복원이다. 대기 신청은 예약하지 않는다.
따라서 두 건의 신청이 각각 잔여 범위 안이면 둘 다 대기가 될 수 있지만, 실제 승인 합계는
사용 가능한 잔여일수를 넘을 수 없다. 취소·반려는 대기 상태에서만 가능하므로 환급하지 않는다.

DB 모드는 승인 시 잔여 행에 select_for_update를 적용하고 동일 트랜잭션에서
잔여·신청·이력을 저장한다. 잔여 부족이나 이력 저장 실패 시 전체 변경을 롤백한다.
개발 모드는 설정을 수정하지 않고, 승인된 balance_deducted 신청 합계를 설정 일수에서 뺀다.
개발 승인·회수는 유형 행을 잠가 승인 사용량 갱신을 직렬화한다.

`deduct_days=0`인 유형은 DB 모드에서 차감하지 않는다. `use_days`는 실제 신청 사용일수이며
기본 차감 단위를 추가로 곱하는 정책은 도입하지 않았다.

## 스키마·배포 영향

- 생성: vacation migration `0003_leaverequesthistorymodel_after_values_and_more`.
- leave_request_history에 nullable JSON before_values·after_values 추가.
- leave_requests에 balance_deducted boolean 추가. 기존 행은 false.
- 기존 이력의 스냅샷은 null이며 소실된 정정 내용을 추정하거나 복구하지 않는다.
- 기존 승인 건은 이번 코드로 차감한 사실이 없으므로 회수 시 자동 환급하지 않는다.
  공유 DB의 기존 잔여 계산·외부 trigger·운영 처리 방식은 배포 전 확인해야 한다.
- migration 0003은 실제 DDL이다. 새 코드를 사용하려면 대상 환경에서 먼저 스키마를 준비해야 한다.
  공유 환경 migration 적용은 수행하지 않았다. 실제 PostgreSQL 스키마·trigger·FK는 미확인이다.

## 아키텍처·범위

domain/application은 Django·ORM에 의존하지 않는다. 잔여 차감·복원은 추상 포트를 통해
인프라 어댑터에 맡기고, 상태·이력 트랜잭션은 기존 Unit of Work가 관리한다.
상위 승인자 조회는 workforce application 포트를 확장했으며 인사정보 수정 기능의 승인선은 변경하지 않았다.
작업 도중 나타난 프론트엔드 변경과 기존에 준비된 검토 보고서는 유지했다.

별도 자기 승인 금지 정책, 사원 FK 전환, 휴가 중복·휴일·반차 계산 정책은 이번 수정에 포함하지 않는다.
HR_MANAGER와 HR_LEAVE_APPROVER의 역할 구분은 기존 구현을 유지한다.
이 사항은 확정 오류와 구별하여 원 검토 보고서에 남겼다.

## 검증

- 전체 백엔드 pytest: 325건 통과.
- 신규 회귀 테스트: 19건. 잔여 초과 승인 거절, 회수 후 재사용, 승인·회수 이력 실패 롤백,
  비차감 유형, 기존 승인 건 회수, 개발 잔여 합산, 권한 밖 처리, 취소·반려,
  상위 승인선, 정정 이력 API, 없는 유형 404, 사유 경계, 유형 조회 재직 검증 포함.
- `uv run ruff check .`: 통과.
- `uv run python manage.py check --settings=config.settings.test`: 통과.
- migration 모듈을 활성화한 인메모리 SQLite 설정에서 makemigrations check·dry-run: 변경 없음.
  테스트 기본 설정의 MIGRATION_MODULES=None을 그대로 쓰지 않고 실제 migration state를 검사했다.
- SQLite에서 0002의 역사적 모델로 합성 승인·이력 행을 만든 뒤 0003을 적용하여
  상태·이력 보존, balance_deducted=false, 스냅샷 null을 확인했다.
- SQLite sqlmigrate SQL을 검토했다. PostgreSQL SQL 실행·동시 세션 잠금 통합 검증은 수행하지 않았다.
- 검증은 순수 Python·인메모리 SQLite만 사용했다. 공유 DB·Redis 변경 없음.
- frontend 변경은 별도 작업이므로 이 작업에서 frontend 검증을 수행하지 않았다.

## 문서 영향

저장소 API 명세의 승인선·잔여 동작·사유 길이·이력 응답과 테이블 명세·명세 인덱스를 갱신했다.
저장소 코드 확인일과 Notion 원문 확인일을 구분했으며 원문 갱신이나 공유 DB 배포 완료로 표시하지 않았다.

## 공유 개발 DB 적용 완료 · 2026-10-13 후속 작업

위 수정·검증 단계의 “공유 DB 미적용” 기록 이후, 사용자가 마이그레이션 적용을 지시하고
대상 `erp_dev.public`을 확인했다. 연결 계정의 대상 테이블 소유 역할 접근을 읽기 전용으로 확인했다.

- 적용 전 vacation 0001·0002 적용 기록 및 세 신규 열이 없음을 확인했다.
- PostgreSQL sqlmigrate 결과는 JSONB 두 열, boolean NOT NULL 열(default false 후 기본값 제거) 추가였다.
- MigrationExecutor 계획이 vacation 0003 단독임을 검사하고 정확히 그 migration만 실행했다.
  다른 앱의 migration·post_migrate 처리·시드 실행은 수행하지 않았다.
- 트랜잭션에 lock_timeout 10초·statement_timeout 60초를 설정했다. 오류 없이 커밋했다.
- 적용 트랜잭션에서 신청·이력 행 수 보존, 기존 balance_deducted=false,
  기존 before_values·after_values=null과 migration 기록 1건을 확인했다.
- 커밋 후 별도 읽기 전용 연결에서 0003 적용 기록과 세 열의 타입·nullability를 재확인했다.
- 직원·계좌 등 개인 데이터는 출력하지 않았다. 잔여일수 재산정·업무 데이터 수정, Redis 변경은 수행하지 않았다.
- 이번 적용은 공유 개발 DB에 한정된다. 운영 환경 적용이나 기존 잔여 계산·trigger의 전체 조사 완료를 뜻하지 않는다.
