import { useEffect, useState } from "react"
import { Alert, Badge, Button, Card, Checkbox, ConfirmDialog, DetailList, Drawer, EmptyState, ErrorState, IconButton, Modal, Select, Skeleton, Spinner, Table, Tabs, Textarea, TextInput } from "../../components/ui"
import styles from "./UiGallery.module.css"

export function UiGallery() {
  useEffect(() => { document.title = "디자인시스템 · WORKLY ERP" }, [])
  const [tab, setTab] = useState("first")
  const [dialog, setDialog] = useState<"modal" | "drawer" | "confirm" | null>(null)
  const [confirmed, setConfirmed] = useState(false)
  const [checked, setChecked] = useState(false)
  return <div className={styles.gallery}>
    <Card title="버튼"><div className={styles.row}>
      <Button>주요 액션</Button><Button variant="secondary">보조 액션</Button><Button variant="ghost">텍스트 액션</Button><Button variant="danger">삭제</Button><Button disabled>비활성</Button><Button pending>처리 중</Button><IconButton label="정보 보기">ⓘ</IconButton>
    </div></Card>
    <Card title="입력·레이블·오류"><div className={styles.fields}>
      <TextInput label="사내 이메일" type="email" hint="합성 예시" placeholder="sample@example.com" />
      <TextInput label="오류 입력" defaultValue="example" error="이메일 형식을 확인하세요." />
      <TextInput label="비활성 입력" disabled value="읽기 전용 예시" />
      <TextInput label="날짜" type="date" /><TextInput label="일시" type="datetime-local" />
      <Select label="선택"><option>전체</option><option>예시 항목</option></Select>
      <Textarea label="설명" required hint="업무 규칙은 모듈에서 처리합니다." />
      <Checkbox label="알림 예시 선택" checked={checked} onChange={(event) => setChecked(event.target.checked)} />
    </div></Card>
    <Card title="상태와 피드백"><div className={styles.stack}>
      <div className={styles.row}><Badge>기본</Badge><Badge tone="info">안내</Badge><Badge tone="success">완료</Badge><Badge tone="warning">대기</Badge><Badge tone="error">실패</Badge><Spinner /></div>
      <Alert>안내 문구</Alert><Alert tone="error">필드와 업무 오류를 확인하세요.</Alert><Skeleton />
      <EmptyState title="표시할 항목이 없습니다">검색 조건을 바꿔 보세요.</EmptyState><ErrorState onRetry={() => setConfirmed(true)}>재시도 동작 예시</ErrorState>
    </div></Card>
    <Card title="탭·표·상세"><Tabs label="전시 탭" items={[{ value: "first", label: "목록" }, { value: "second", label: "상세" }]} value={tab} onChange={setTab}>
      {tab === "first" ? <Table caption="합성 목록"><thead><tr><th scope="col">항목</th><th scope="col">상태</th></tr></thead><tbody><tr><td>예시 항목</td><td><Badge tone="success">완료</Badge></td></tr></tbody></Table> : <DetailList items={[{ key: "name", label: "항목명", value: "예시 항목" }, { key: "status", label: "상태", value: "완료" }]} />}
    </Tabs></Card>
    <Card title="대화상자·Drawer"><div className={styles.row}><Button onClick={() => setDialog("modal")}>대화상자 열기</Button><Button onClick={() => setDialog("drawer")}>Drawer 열기</Button><Button variant="danger" onClick={() => setDialog("confirm")}>확인 창 열기</Button></div>{confirmed && <Alert tone="success">예시 동작이 완료되었습니다.</Alert>}</Card>
    <Modal open={dialog === "modal"} title="대화상자 예시" onClose={() => setDialog(null)}><TextInput label="예시 입력" hint="Tab으로 이동하고 Escape로 닫습니다." /></Modal>
    <Drawer open={dialog === "drawer"} title="Drawer 예시" onClose={() => setDialog(null)}><p>기본 대화상자와 같은 키보드·포커스 동작을 사용합니다.</p></Drawer>
    <ConfirmDialog open={dialog === "confirm"} title="예시 동작을 실행할까요?" danger onClose={() => setDialog(null)} onConfirm={() => { setConfirmed(true); setDialog(null) }}><p>실제 업무 API를 호출하지 않습니다.</p></ConfirmDialog>
  </div>
}
