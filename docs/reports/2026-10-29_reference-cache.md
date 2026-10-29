# 기준 목록 Redis/Valkey 캐시 · 2026-10-29

- 요청: 기존 Redis를 업무 캐시에 사용하는 변경을 가능한 범위에서 구현.
- 기준: dev의 기존 변경 사항을 보존. 신규 의존성·모델·migration·프론트 변경 없음.
- Notion 원문 조회·수정 없음. 기존 API 응답·업무 정책·세션 저장 방식 유지.

## 적용 범위

- workforce의 부서·직급·역할 코드 목록: 쿼리 문자열이 없는 목록 응답만 캐시.
- vacation의 활성 유형 목록: 공통 메타데이터를 캐시하고 Decimal을 복원.
- 역할 코드 캐시는 사원 역할 부여/권한 캐시가 아니다. 인증·권한은 DRF에서 매 요청 검사.
- 사원 재직·잔여일수·승인·급여·명령용 휴가 유형 단건 조회는 최신 DB 사용.
- presentation/infra에서 공유 infra 캐시를 사용하며 domain/application 의존성 변화 없음.

## 일관성과 장애 처리

저장·삭제 신호는 transaction.on_commit에서 UUID 세대 키를 회전한다. 동시 조회가 이전
세대에 값을 채워도 새 세대에서는 읽지 않는다. 목록 채우기도 커밋 후 실행해 롤백 데이터가
공유 캐시에 노출되지 않는다. 목록은 JSON 원시 값이며 개인별 응답은 저장하지 않는다.
부서장 사원 삭제의 SET_NULL도 부서 목록을 무효화한다.

표시 목록은 기본 180초, 최대 300초 유지한다. 이전 세대 목록은 TTL로 정리되며 세대 키는
자원별 1개다. 외부 SQL/QuerySet.update/bulk 작업은 신호가 없고 무효화 실패 시에도 이전
목록이 TTL까지 보일 수 있다. 강한 일관성이 필요한 업무 판정에는 캐시를 사용하지 않는다.

Redis 오류는 DB 조회로 대체하며 5초간 읽기 시도를 생략한다. 연결·읽기 제한시간은 각각
0.2초, 자동 재시도 0회, 연결 풀 최대 8개/프로세스다. 첫 조회에는 여러 Redis 명령이 있으므로
전체 요청의 0.2초 완료를 보장하지 않는다. 로그에는 예외 종류만 남기며 URL·값은 남기지 않는다.

## 설정과 운영

운영 기본 활성, 개발 기본 비활성. 개발에서 켜려면 backend 환경변수에
REFERENCE_CACHE_ENABLED=true를 설정 후 사용자가 관리하는 서버를 재시작한다.
REFERENCE_CACHE_URL은 REDIS_URL을 기본 사용하고 TLS는 rediss://다.
REFERENCE_CACHE_KEY_PREFIX는 기본 erp:<환경>:reference:v1이며 배포별 고유값을 권장한다.
TTL/timeout/URL/prefix는 backend 환경변수 예제·루트 README·배포 가이드에 기록했다.

Valkey RBAC는 해당 키 prefix에 GET/SET(NX/EX 포함), 기존 PING 및 필요한 연결 명령을
허용해야 한다. 별도 DB 컨테이너나 캐시 초기화는 추가하지 않았다. 실제 개발 환경변수,
서버 프로세스, 공유 DB/Redis, AWS 설정에는 조작·쓰기·flush·migration을 수행하지 않았다.
GitHub Actions/Secrets Manager 실행 배포 자동화 구현은 이번 캐시 변경의 범위가 아니다.

## 검증

- 신규 회귀 17개 통과: 목록 반복 조회, 인증·쓰기 권한, 저장·삭제 무효화, 롤백, 동시 채우기,
  캐시 장애·읽기 생략, 재적재, DB 오류 전파, 설정 범위, 사원별 잔여·재직의 최신성.
- 부서·직급·역할 목록의 대상 DB 쿼리: 최초 1회 → 반복 0회. 인증 등 전체 요청 쿼리와 구분.
- 휴가 유형 repository의 대상 DB 쿼리: 최초 1회 → 반복 0회; 명령용 단건 조회는 1회 유지.
- SQLite와 로컬 메모리 캐시 및 Redis 오류 모의만 사용. 실제 Redis/Valkey 성능 실측 아님.
- 전체 backend `uv run pytest -q`: 561 passed (35.80s).
- `uv run ruff check .`: 통과.
- 테스트 설정 `python manage.py check`: 문제 없음.
- `git diff --check`: 통과. 모델 변경이 없어 migration 생성·적용은 수행하지 않았다.
- 프론트 변경이 없어 프론트 검증은 이번 범위에서 재실행하지 않았다.

운영 배포 전 실제 TLS/RBAC·리소스 예산과 목록 수정 후 갱신은 staging에서 확인해야 한다.
