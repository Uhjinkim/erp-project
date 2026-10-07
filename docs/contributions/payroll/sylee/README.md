# payroll / sylee 기여 문서

- 대상 모듈: `payroll`
- 작업 브랜치: `sylee`
- 기준 브랜치: `dev`
- 상태: 작성 중
- 최종 갱신: 2026-10-06

## 이 폴더에 대하여

급여 모듈 작업 중 공용 문서에 직접 반영했던 내용을 2026-10-06에 이 폴더로 옮겼다. 공용
문서(루트 `README.md`, `docs/specs/notion/02`~`05`·`README.md`,
`docs/specs/notion/payroll-implementation-map.md`, `docs/reports/`의 급여 보고서)는
`dev`와의 병합 기준 커밋(`c15b78e`) 상태로 되돌렸다. 앞으로 급여 작업의 문서 변경은 이
폴더에만 기록한다.

- `README.md`(이 문서): 범위, 확정한 결정, API·스키마 영향, 공용 문서 반영 후보
- `implementation-map.md`: 급여 명세 구현 대응표(원래 `docs/specs/notion/payroll-implementation-map.md`)
- `reports/`: 날짜별 작업 보고서

## 기능 범위

- 구현 범위: `FN-PY-001`~`FN-PY-007` — 급여 생성(구성항목 동시 입력 가능), 구성항목
  입력·수정, 확정, 확정취소, 재확정, 사원별 급여 조회(급여담당자), 본인 급여명세 조회,
  변경 이력 조회. React 급여 화면(급여명세서 형식, 부서→사람·정산월·상태 필터, 미작성
  사원 목록, 상단 경고창).
- 제외 범위: 4대보험 요율·소득세 자동 계산(금액은 급여담당자가 입력), 급여명세서
  출력·PDF, 급여 공지(`FN-BD-007`) 연동, 공휴일 데이터 시드, 주민등록번호 표시,
  구성항목 관리 화면(필요한 항목만 migration으로 추가).

## 설계 결정

- 관련 규칙·기능 ID: `PY-001`~`PY-009`, `FN-PY-001`~`FN-PY-007`
- 저장 구조: 공유 DB에 이미 있는 `payrolls`, `payroll_details`, `payroll_items`,
  `payroll_history`를 state-only migration으로 매핑한다. `payroll_public_holidays`만
  신규 테이블이다. (처음에는 이 legacy 테이블을 놓치고 새 테이블로 설계했다가
  2026-09-23에 바로잡았다.)
- 상태: `작성중`/`확정` 두 가지만 저장한다. 확정취소·재확정은 이력 action으로 구분한다.
  `payroll_history.action` CHECK 허용값은 `확정`/`확정취소`/`재확정`/`수정`뿐이라 급여
  생성은 이력에 남기지 않는다.
- 금액: `payrolls`의 CHECK가 `net_pay = total_pay - total_deduct`를 강제하므로 차인지급액에
  별도 올림을 적용하지 않는다. `PY-009`의 원 단위 올림이 필요한 외화 환산 입력은 아직
  지원하지 않으며, 생기면 입력 시점에 처리해야 한다.
- 정산일자: 매월 25일, 토·일요일이거나 등록된 공휴일이면 직전 평일(2026-09-22 급여 담당자
  결정). Notion에는 "정산일자 미확정"으로 남아 있다.
- 구성항목: 지급 — 기본급, 상여, 고정수당, 초과근무수당 / 공제 — 국민연금, 건강보험
  (장기요양보험 포함), 고용보험, 소득세(지방소득세 포함). 산재보험은 사업주 부담이라
  제외했다. 특수 상황용 항목은 미리 늘리지 않고 실제로 필요할 때만 추가한다
  (2026-10-06 담당자 결정).
- 권한:
  - 생성·구성항목 수정·확정·확정취소는 `PAYROLL_MANAGER`만 가능(`PY-001`).
  - 급여담당자는 본인 급여를 생성·수정·확정·확정취소할 수 없다 — 다른 급여담당자가
    처리한다(2026-10-06 담당자 결정, 자기거래 방지). 조회는 허용한다.
  - 일반 사원은 본인 급여만, 그리고 `확정`된 것만 조회한다(`PY-008`, 2026-10-06 결정 —
    작성중 초안은 사원에게 노출하지 않는다).
- 이력(2026-10-06):
  - 최신순으로 반환한다.
  - 처리자(이름)와 사유는 급여담당자만 볼 수 있다. 일반 사원은 상태(action)와 날짜만 받는다.
  - 구성항목 수정 사유는 한글 항목명과 정수·천 단위 쉼표 금액으로 기록한다
    (예: `기본급 2,300,000원, 국민연금 103,500원`). 확정 사유는 `차인지급액 N원 확정`.
- 화면 표기: 모든 금액은 정수·천 단위 쉼표로 표시한다. 오류는 상단에 고정되는 경고창으로
  알린다.
- 급여명세서(2026-10-07): 금액이 없거나 0인 항목은 행 자체를 표시하지 않는다. 표시 순서는
  지급 — 기본급·고정수당·초과근무수당·상여, 공제 — 국민연금·건강보험·고용보험·소득세.
  입력 폼도 같은 순서를 쓴다.
- 이력 표시(2026-10-07): 첫 줄에 `상태 / 수정일자 / 담당자`, 다음 줄에 사유·변경 내용을
  표시한다. 일반 사원은 `상태 / 날짜`만 보인다.

## 인터페이스와 데이터 영향

- API·권한 변경(`/api/payroll/`, 세션 인증 필수):
  - `GET components/` — 활성 구성항목 목록
  - `GET statements/` — 본인 급여(확정 건만). `?emp_no=<사번>` 또는 `?all=true`는
    급여담당자 전용(작성중 포함)
  - `POST statements/` — 급여 생성(급여담당자, 본인 제외). 본문 `emp_no`, `year`,
    `month`, 선택 `items[{component_code, amount}]`
  - `GET statements/{id}/` — 상세(본인은 확정 건만, 급여담당자는 전체)
  - `PUT statements/{id}/items/` — 구성항목 교체(급여담당자, 본인 제외, 작성중만)
  - `POST statements/{id}/confirm/`, `POST statements/{id}/cancel-confirmation/`
    (급여담당자, 본인 제외, 확정취소는 `reason` 필수)
  - `GET statements/{id}/history/` — 급여담당자: `action`, `changed_at`,
    `actor_employee_no`, `actor_name`, `reason` / 일반 사원: `action`, `changed_at`만
  - 급여 응답에는 `employee: {emp_no, name, position_name}`이 포함된다(workforce 조회는
    `WorkforceGateway.employee_displays` 포트를 거친다).
- 스키마·migration:
  - `payroll/0001_initial` — legacy 4개 테이블 상태 등록(DDL 없음)
  - `payroll/0002_public_holiday` — `payroll_public_holidays` 신규 생성
  - `payroll/0003_seed_components` — 기본 구성항목 6건 시드
  - `payroll/0004_seed_bonus_component` — 상여(`BONUS`) 시드
  - `payroll/0005_seed_income_tax_component` — 소득세(지방소득세 포함)(`INCOME_TAX`) 시드
  - `workforce/0003_payroll_manager_role` — `PAYROLL_MANAGER` 역할 시드
- 공유 개발 DB 적용 현황: 0001~0003과 workforce 0003은 2026-09-23, 0004·0005는 2026-10-06에
  각각 사용자 승인 후 적용했다(현재 활성 구성항목 8건).
- 공유 DB 데이터 참고: 사용자가 테스트로 만든 2026년 9월분 급여가 있다(정리 여부 미정).
  2026-10-06 이전에 기록된 이력 사유는 영문 코드·소수점 형식(`BASE_PAY=2300000.00`)으로
  남아 있으며, 새 형식으로 바꾸려면 데이터 수정 승인이 필요하다.
- 환경변수·인프라 영향: 없음.

## 검증

- 실행한 테스트(2026-10-06, `origin/dev` 병합 후): `uv run pytest`(88건 통과 — 급여 51건,
  게시판 37건), `uv run ruff check .`, `uv run python manage.py check`,
  `uv run python manage.py makemigrations --check --dry-run`, `bun run lint`, `bun run build`,
  `.\scripts\start-dev.ps1 -Check`, `.\scripts\docs-workflow.ps1 check`(통과)
- `origin/dev` 병합 시 `INSTALLED_APPS`, URL, 테스트 `MIGRATION_MODULES`, 프론트엔드 모듈
  전환에서 급여·게시판 등록이 겹쳐 충돌했고, 양쪽을 모두 유지하는 방식으로 해결했다.
- 남은 검증:
  - 로컬 개발 서버(`start-dev.ps1`, `--noreload`) 재시작 후 브라우저에서 상여·소득세 입력,
    급여명세서 표시, 상태 필터, 이력 표시 수동 확인

## 공용 문서 반영 후보

문서 담당자 검토용이며, 이 브랜치에서는 공용 문서를 직접 수정하지 않는다.

- Notion 원문: `PY-001`~`PY-009`, `FN-PY-001`~`FN-PY-007` 상세와 정산일자 결정,
  "급여담당자 본인 급여 처리 금지", "사원은 확정 급여만 조회", "이력 상세는 급여담당자만"
  결정을 반영할지 확인 필요(Notion MCP 인증 불가 — 담당자에게 직접 전달).
- `02-business-rules.md`: 급여 절을 요약 한 줄에서 `PY-001`~`PY-009` 개별 규칙으로 확장
  (원문은 급여 담당자가 2026-09-22에 전달한 Notion 내보내기 기준).
- `03-feature-specification.md`: `FN-PY-001`~`FN-PY-007` 표(기능·수행 주체·관련 규칙) 추가.
- `04-detailed-features.md`: `FN-PY-001` 급여 정산 생성, `FN-PY-001` 금액 계산 세부 기준,
  `FN-PY-004` 급여 확정 취소 상세 추가.
- `05-open-policies.md`: 미해결 안건 "급여 정산일자"를 확정 반영 사항(매월 25일, 휴일이면
  직전 평일)으로 이동.
- `06-api-specification.md`: 위 급여 API 절 추가.
- `08-table-specification.md`: 급여 4개 테이블이 Django state-only 모델로 연결되었음,
  CHECK 허용값(`작성중`/`확정`, `지급`/`공제`, `확정`/`확정취소`/`재확정`/`수정`),
  신규 `payroll_public_holidays`, `payroll_items` 시드 8건 반영.
- 루트 `README.md`: 저장소 구조에 `payroll/` 추가, "인증과 업무 모듈"에 급여 절(API,
  `PAYROLL_MANAGER` 권한, 정산일자) 추가. 과거 이 브랜치가 적었던 "급여 테이블은 공유 DB에
  없는 새 테이블"이라는 문장은 틀린 내용이므로 반영하지 않는다.
- `docs/specs/notion/README.md`: 급여 구현 대응표를 공용 경로에 둘지 문서 담당자가 결정.

## 미결 사항

- 기존 이력 사유 데이터를 새 형식으로 바꿀지
- 국내 공휴일 데이터 확보 방식
- 주민등록번호 등 민감정보를 급여명세서에 표시할지(현재 저장 필드 없음)
