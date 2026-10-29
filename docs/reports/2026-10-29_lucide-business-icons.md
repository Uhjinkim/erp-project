# Lucide 업무 아이콘·선택 상태 적용

- 기준: dev 기존 작업 트리. 기존 배포·성능·역할 UX·메뉴 검색 변경을 보존했다.
- 요청: Lucide로 업무별 의미를 구분하고 선택 상태도 표현.
- 프론트 표현·등록 타입·의존성만 변경. 업무 규칙·서버 권한·API·스키마 변경 없음.

## 의존성과 적용 범위

frontend에서 bun add lucide-react로 1.63.0을 추가하고 package.json과 bun.lock을 함께
갱신했다. 각 registration은 필요한 아이콘만 named import한다. ModuleRegistration의 icon과
screens[].icon은 LucideIcon 타입으로 지정해 누락을 TypeScript에서 확인한다.
설치/사용 근거는 [Lucide React 공식 문서](https://lucide.dev/guide/react/)다.

| 업무 | 모듈 아이콘 | 하위 메뉴 예 |
| --- | --- | --- |
| 내 정보 | UserRound | 인사정보 ContactRound, 이력 History, 처리함 Inbox, 검토 FileCheck2 |
| 사원·조직 | Network | 목록 UsersRound, 신규 UserRoundPlus, 퇴사 UserRoundMinus, 재입사 UserRoundCheck, 역할 ShieldCheck |
| 휴가 | CalendarDays | 신청 CalendarPlus, 내역 CalendarClock, 승인 CalendarCheck, 회수 CalendarX, 재신청 CalendarSync |
| 게시판 | MessagesSquare | 공지 Megaphone, 일반 MessagesSquare, 작성 SquarePen |
| 인사평가 | ClipboardCheck | 팀 대상 UsersRound, 작성 ClipboardPenLine, 관리 ClipboardCheck, 결과 ChartNoAxesCombined |
| 급여 | WalletCards | 기간 CalendarDays, 생성 Calculator, 항목 ListOrdered, 확정 BadgeCheck, 명세 ReceiptText |

미등록 home/system도 등록 타입에 맞게 House/Settings와 화면 아이콘을 갱신했지만 배포 메뉴에
추가하지 않았다. 검색 SVG는 Search, 화면 메뉴는 Menu, 로그아웃은 LogOut으로 통일했다.
평가 작성 화면의 뒤로 이동 기호는 ArrowLeft로 대체했다. 변경 전후 값을 설명하는 문장 속
화살표는 의미를 가진 본문 텍스트로 유지했다.

## 선택과 접근성

기존 route/역할 필터를 유지하고 aria-current에 따라 선택을 표현한다. 모듈은 24px,
하위 메뉴는 18px, 검색/유틸리티는 16px다. 선택 아이콘은 선 두께 2.5, 기본은 2다.
모듈의 밝은 아이콘·배경·왼쪽 표시선과 하위 메뉴의 파란 아이콘·표시선·회색 배경으로
색 이외의 단서도 제공한다. 비선택 hover와 선택 스타일을 구분해 선택 배경을 유지한다.
SVG는 aria-hidden으로 중복 읽기를 막고 링크 label/title·버튼 텍스트·검색 label을 유지한다.
메뉴의 투명 왼쪽 테두리를 기본으로 두어 선택 시 내용이 옆으로 밀리지 않도록 했다.

## 검증

- bun run lint, bun run build 통과. frontend 테스트 58개 통과.
- 실제 AppShell을 합성 복수 역할 사용자와 정적 본문으로 임시 마운트한 브라우저 검수.
- 6개 모듈의 경로를 바꿔 각각 현재 모듈 1개 선택, 페이지 아이콘, 기본/선택 2/2.5px 선,
  내비게이션 모든 링크의 숨김 SVG를 확인했다.
- 별도 iframe 1200/980/360px 가로 넘침 없음.
- 실제 모바일 뷰포트에서 화면 메뉴를 열고, 360px 컨테이너의 선택 메뉴 파란 아이콘·표시선,
  회색 배경·검색 아이콘·가로 넘침 없음을 확인했다. 선택 메뉴 hover에도 강조가 유지됐다.
- 임시 DOM을 제거하고 원래 앱을 새로고침했다. 공유 계정/업무 데이터 쓰기 없음.
- 이번 변경은 백엔드 수정이 없어 백엔드 검사를 재실행하지 않았다. 전체 업무 흐름 재검수는 아니다.
- 기존 사용자가 실행한 8080·프론트 프로세스를 시작·종료하지 않았다. 배포·migration 없음.
