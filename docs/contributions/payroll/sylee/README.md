# payroll / sylee 기여 문서

- 대상 모듈: `payroll`
- 작업 브랜치: `sylee`
- 기준 브랜치: `dev`
- 상태: 작성 중
- 최종 갱신: 2026-10-13

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
  사원 목록, 상단 경고창). 지급일 지정·수정, 확정 급여명세서 PDF(브라우저 인쇄)·엑셀 저장.
- 프론트엔드 화면(2026-10-13, 공통 토대 기준 재구성): F7 배정 화면 5개(`payroll-periods`,
  `payroll-create`, `payroll-item`, `payroll-confirm`, `payslip`)를 `features/payroll/`의
  공통 UI 기반 화면으로 나눴다. 기존 `components/PayrollPanel.tsx`는 삭제했다.
- 제외 범위: 4대보험 요율·소득세 자동 계산(금액은 급여담당자가 입력), 서버에서 생성하는
  PDF 파일, 급여 공지(`FN-BD-007`) 연동, 공휴일 데이터 시드, 주민등록번호 표시,
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
  - 구성항목 수정 사유는 한글 항목명과 정수·천 단위 쉼표 금액으로 기록한다. 확정 사유는
    `차인지급액 N원 확정`.
  - 수정 사유는 변경 하나당 한 줄로 기록한다(2026-10-13 담당자 결정, 이전에는 쉼표 구분).
    순서는 지급일 변경, 지급 항목, 공제 항목이며, 각 묶음 안은 급여명세서 순서를 따른다.
    예: `지급일 2026-09-25 → 2026-09-24` / `기본급 2,300,000원` / `국민연금 103,500원`.
    화면은 줄바꿈을 그대로 표시한다. 이전에 쉼표로 기록된 이력은 그대로 남는다.
- 화면 표기: 모든 금액은 정수·천 단위 쉼표로 표시한다. 오류는 상단에 고정되는 경고창으로
  알린다.
- 급여명세서(2026-10-07): 금액이 없거나 0인 항목은 행 자체를 표시하지 않는다. 표시 순서는
  지급 — 기본급·고정수당·초과근무수당·상여, 공제 — 국민연금·건강보험·고용보험·소득세.
  입력 폼도 같은 순서를 쓴다.
- 이력 표시(2026-10-07): 첫 줄에 `상태 / 수정일자 / 담당자`, 다음 줄에 사유·변경 내용을
  표시한다. 일반 사원은 `상태 / 날짜`만 보인다.
- 급여 대상자 조회(2026-10-12): workforce의 사원 목록 API가 `HR-001`에 따라 인사관리자
  전용이 되면서(PR #5), 인사관리자가 아닌 급여담당자는 급여 화면에서 403("이 작업을 수행할
  권한이 없습니다.")을 받고 대상자를 고를 수 없었다. workforce 권한을 넓히지 않고, 급여
  모듈 전용 `GET /api/payroll/employees/`(급여담당자만, 사번·이름·부서·직급·재직 여부만
  반환, 연락처 제외)를 추가했다. workforce 조회는 `WorkforceGateway.list_payroll_targets`
  포트를 거친다.
- 지급일(2026-10-12): 생성 시 비워 두면 정산일자 정책으로 자동 지정하고, 값을 주면 그
  날짜를 쓴다. 작성중 상태에서는 구성항목 편집과 함께 바꿀 수 있고, 확정 상태에서는
  바꿀 수 없다(`PY-005`, 확정취소 후 수정). 변경은 `수정` 이력에
  `지급일 2026-09-25 → 2026-09-24` 줄로 기록한다. 지급일 범위 제한(정산월 안이어야 하는지
  등)은 규칙이 없어 두지 않았다.
- 급여명세서 내려받기(2026-10-12): 확정된 급여만 가능하다. 엑셀은 백엔드가 `openpyxl`로
  화면과 같은 양식(0원 항목 제외, 같은 순서)의 `.xlsx`를 만들고, 본인 또는 급여담당자만
  받을 수 있다. PDF는 브라우저 인쇄 대화상자의 "PDF로 저장"을 쓰며, 인쇄 시 선택한
  명세서만 출력된다.
- 표시 순서의 기준을 백엔드로 옮겼다(`payroll.domain.policies.PAYSLIP_ORDER`): API가
  구성항목 목록과 급여 항목을 이 순서로 내려주고, 화면과 엑셀이 같은 순서를 쓴다.
- 화면 구성(2026-10-13 담당자 결정):
  - 급여 정산 기간 목록: 정산월별 대상·작성중·확정·미작성 **건수만** 표시(금액 합계 없음).
    기간 테이블이 없으므로 기존 급여를 연·월로 묶고, 현재 월은 급여가 없어도 표시한다.
    미작성은 현재 재직 사원 기준이다.
  - 급여 정산 생성: 기존 "급여 관리 - 급여 생성"을 옮겼다. 저장 버튼은 "작성중으로 저장"이며
    성공 시 항목 화면·확정 화면 이동 링크를 보여준다. 선택한 정산월의 미작성 사원 목록을
    옆에 두어 선택하면 폼이 채워지고 폼 위치로 이동한다(기존 "미작성" 필터 대체).
    사람을 고르거나 정산월을 바꿀 때 그 사람의 직전 월 급여가 있으면 구성항목 금액을 불러와
    채운다(지급일은 불러오지 않음). 없으면 금액 칸을 비운다(2026-10-13 담당자 요청).
  - 사원별 정산 항목: 부서·사람·정산월·상태 필터, 목록, 작성중 급여의 지급일·구성항목
    편집. 확정 급여는 보기와 PDF·엑셀 저장만 한다.
  - 급여 확정·정정: 확정과 확정취소는 **이 화면에만** 둔다. 확정은 확인 창, 확정취소는 사유
    입력 창(`window.prompt` 대체)을 쓰고, 취소 후 항목 화면으로 가는 정정 링크를 보여준다.
  - 이력: 항목·확정 화면의 각 급여에서 오른쪽 Drawer로 연다. 내 급여명세에서는 기존처럼
    본인용(상태·날짜만) 이력을 연다. Drawer 바깥(어두운 영역)을 누르면 닫힌다.
  - 내 급여명세: 기존 "내 급여"를 옮겼다. 월 목록과 선택한 명세서, PDF·엑셀 저장. 급여
    모듈의 기본 진입 화면이다(일반 사원이 다수이므로).
  - 급여담당자 전용 4개 화면은 다른 사용자에게 "급여담당자 전용" 안내를 보여준다. 표시만
    제한하며 실제 권한은 API가 판정한다.
  - 화면 주소 query: `period=YYYY-MM`(생성·항목·확정), `statementId`(항목).

## 인터페이스와 데이터 영향

- API·권한 변경(`/api/payroll/`, 세션 인증 필수):
  - `GET components/` — 활성 구성항목 목록(급여명세서 표시 순서)
  - `GET employees/` — 급여 대상자 목록(급여담당자 전용, 2026-10-12 추가):
    `emp_no`, `name`, `dept_no`, `dept_name`, `position_name`, `is_active`
  - `GET statements/` — 본인 급여(확정 건만). `?emp_no=<사번>` 또는 `?all=true`는
    급여담당자 전용(작성중 포함)
  - `POST statements/` — 급여 생성(급여담당자, 본인 제외). 본문 `emp_no`, `year`,
    `month`, 선택 `items[{component_code, amount}]`, 선택 `payment_date`(생략 시 자동)
  - `GET statements/{id}/` — 상세(본인은 확정 건만, 급여담당자는 전체)
  - `GET statements/{id}/excel/` — 확정 급여명세서 `.xlsx`(본인 또는 급여담당자,
    작성중이면 400, 2026-10-12 추가)
  - `PUT statements/{id}/items/` — 구성항목 교체, 선택 `payment_date` 변경(급여담당자,
    본인 제외, 작성중만)
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
- 의존성(2026-10-12): 백엔드에 `openpyxl` 3.1.5 추가(`uv add`, `pyproject.toml`·`uv.lock`
  갱신). 팀원은 병합 후 `uv sync`가 필요하다. 스키마 변경·migration은 없다.

## 검증

- 2026-10-13 프론트엔드 화면 재구성·추가 수정: `bun run test`(13건 통과, 급여 기간 집계·
  미작성·부서 분류·직전 월 찾기 테스트 추가), `bun run lint`, `bun run build`,
  `uv run pytest`(306건 통과), `uv run ruff check .` 통과. 브라우저 확인은 하지 못했다.

- 실행한 테스트(2026-10-12): `uv run pytest`(전체 279건 통과, 급여 대상자 조회 회귀 테스트·
  지급일·엑셀 테스트 포함), `uv run ruff check .`, `uv run python manage.py check`,
  `uv run python manage.py makemigrations --check --dry-run`, `bun run lint`, `bun run build`.
  공유 개발 DB에서 급여 대상자 조회를 읽기 전용으로 실행해 정상 동작을 확인했다.
- 이전 검증(2026-10-06, `origin/dev` 병합 후): 88건 통과, `start-dev.ps1 -Check`,
  `docs-workflow.ps1 check` 통과
- `origin/dev` 병합 시 `INSTALLED_APPS`, URL, 테스트 `MIGRATION_MODULES`, 프론트엔드 모듈
  전환에서 급여·게시판 등록이 겹쳐 충돌했고, 양쪽을 모두 유지하는 방식으로 해결했다.
- 남은 검증:
  - 로컬 개발 서버(`start-dev.ps1`, `--noreload`) 재시작 후 브라우저에서 인사관리자가 아닌
    급여담당자 계정으로 급여 생성, 지급일 수정, PDF 인쇄·엑셀 저장, 상태 필터, 이력 표시
    수동 확인

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
- 모듈 간 사원 조회 방식(workforce 담당자와 협의 필요): workforce의
  `frontend/src/api/workforce.ts`에 "다른 모듈의 호출 방식은 결정 대기 중"이라는 메모가
  있다. 급여는 HR-001을 넓히지 않도록 자기 모듈에 업무에 필요한 최소 필드만 내려주는
  대상자 API를 두는 방식을 택했다. 다른 모듈(평가·휴가 등)도 같은 문제를 겪는다면 이 방식을
  공용 원칙으로 정할지 문서 담당자·workforce 담당자의 결정이 필요하다.
- `08-table-specification.md`: 급여 4개 테이블이 Django state-only 모델로 연결되었음,
  CHECK 허용값(`작성중`/`확정`, `지급`/`공제`, `확정`/`확정취소`/`재확정`/`수정`),
  신규 `payroll_public_holidays`, `payroll_items` 시드 8건 반영.
- 루트 `README.md`: 저장소 구조에 `payroll/` 추가, "인증과 업무 모듈"에 급여 절(API,
  `PAYROLL_MANAGER` 권한, 정산일자) 추가. 과거 이 브랜치가 적었던 "급여 테이블은 공유 DB에
  없는 새 테이블"이라는 문장은 틀린 내용이므로 반영하지 않는다.
- `docs/specs/notion/README.md`: 급여 구현 대응표를 공용 경로에 둘지 문서 담당자가 결정.
- F0(공통 토대) 검토 요청(2026-10-13):
  - `frontend/src/app/ModuleScreen.tsx`: 급여 화면 연결을 위해 이 브랜치에서 최소 수정했다
    (담당자 승인). `PayrollPanel` 대신 `route.moduleId === "payroll"`이면 `PayrollScreen`에
    route를 넘긴다. F0 검토 필요.
  - `frontend/src/styles/legacy.css`의 `.payroll-*`, `.payslip*`, `.badge--payroll-*` 선택자는
    더 이상 쓰지 않으므로 삭제 요청한다.
  - `frontend/src/styles/print.css`의 급여 인쇄 규칙(`body.payroll-printing`,
    `.payslip--printing`)은 새 화면도 사용하므로 유지가 필요하다. 그 안의 `.actions`·
    `.payroll-history`·`.payroll-items-editor`·`.badge` 숨김 규칙은 쓰지 않는다(새 화면은
    모듈 CSS로 처리).
  - 공용 `Modal`/`Drawer`에 바깥 클릭으로 닫는 선택 prop(예: `closeOnBackdrop`) 추가 요청.
    지금은 급여 `HistoryDrawer`가 문서 click 이벤트로 직접 처리한다. 공용 prop이 생기면 바꾼다.
  - `docs/guides/frontend-foundation-contracts.md` 2절 payroll 행: "기존 PayrollPanel"을
    5개 화면 연결 완료로 갱신.

## 미결 사항

- 기존 이력 사유 데이터를 새 형식으로 바꿀지
- 국내 공휴일 데이터 확보 방식
- 주민등록번호 등 민감정보를 급여명세서에 표시할지(현재 저장 필드 없음)
