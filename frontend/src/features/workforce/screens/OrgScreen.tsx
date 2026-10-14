import { useCallback, useState } from "react"
import { createDepartment, createPosition, listEmployees, updateDepartment, updatePosition } from "../../../api/workforce"
import { Alert, Button, Card, Modal, Select, Table, Tabs, TextInput } from "../../../components/ui"
import type { DepartmentSummary, PositionSummary } from "../../../types/workforce"
import type { MasterData } from "../hooks"
import { useMutation, useWorkforceQuery } from "../hooks"
import { departmentLabel, firstFieldErrors, workforceHref } from "../model"
import styles from "../workforce.module.css"

const tabs = [{ value: "departments", label: "부서" }, { value: "positions", label: "직급" }]

type OrgProps = { enabled: boolean; search: URLSearchParams; master: MasterData; canEdit: boolean; onChanged: () => void }

// Query key: tab=departments|positions. 조회는 인증 사용자, 변경은 인사관리자만 서버가 허용한다.
export function OrgScreen({ enabled, search, master, canEdit, onChanged }: OrgProps) {
  const tab = search.get("tab") === "positions" ? "positions" : "departments"
  return (
    <Tabs label="조직 관리 구분" items={tabs} value={tab} onChange={(value) => { window.location.hash = workforceHref("org", { tab: value === "positions" ? value : undefined }) }}>
      {tab === "positions"
        ? <Positions positions={master.positions} canEdit={canEdit} onChanged={onChanged} />
        : <Departments departments={master.departments} enabled={enabled} canEdit={canEdit} onChanged={onChanged} />}
    </Tabs>
  )
}

function Departments({ departments, enabled, canEdit, onChanged }: { departments: DepartmentSummary[]; enabled: boolean; canEdit: boolean; onChanged: () => void }) {
  const [editing, setEditing] = useState<DepartmentSummary | "new" | null>(null)
  const [notice, setNotice] = useState("")
  return (
    <Card title="부서" actions={canEdit && <Button size="small" onClick={() => setEditing("new")}>부서 추가</Button>}>
      {notice && <Alert tone="success">{notice}</Alert>}
      {!canEdit && <p className={styles.hint}>부서 변경은 인사관리자만 할 수 있습니다.</p>}
      {departments.length === 0
        ? <p className={styles.hint}>등록된 부서가 없습니다.</p>
        : <Table caption="부서 목록">
            <thead><tr><th scope="col">부서번호</th><th scope="col">부서명</th><th scope="col">상위 부서</th><th scope="col">부서장 사번</th>{canEdit && <th scope="col">작업</th>}</tr></thead>
            <tbody>
              {departments.map((item) => (
                <tr key={item.dept_no}>
                  <td>{item.dept_no}</td>
                  <th scope="row">{item.dept_name}</th>
                  <td>{item.parent_dept_no === null ? "최상위" : departmentLabel(departments, item.parent_dept_no)}</td>
                  <td>{item.head_emp_no === null ? "미지정" : canEdit ? <a href={workforceHref("employee-detail", { empNo: item.head_emp_no })}>{item.head_emp_no}</a> : item.head_emp_no}</td>
                  {canEdit && <td><Button size="small" variant="secondary" onClick={() => setEditing(item)} aria-label={`${item.dept_name} 수정`}>수정</Button></td>}
                </tr>
              ))}
            </tbody>
          </Table>}
      {editing && (
        <DepartmentDialog key={editing === "new" ? "new" : editing.dept_no} department={editing === "new" ? null : editing} departments={departments} enabled={enabled}
          onClose={() => setEditing(null)}
          onDone={(saved) => { setEditing(null); setNotice(`${saved.dept_name} 부서를 저장했습니다.`); onChanged() }} />
      )}
    </Card>
  )
}

function DepartmentDialog({ department, departments, enabled, onClose, onDone }: {
  department: DepartmentSummary | null; departments: DepartmentSummary[]; enabled: boolean; onClose: () => void; onDone: (saved: DepartmentSummary) => void
}) {
  const [form, setForm] = useState({
    dept_no: department ? String(department.dept_no) : "",
    dept_name: department?.dept_name ?? "",
    parent_dept_no: department?.parent_dept_no === null || department === null ? "" : String(department.parent_dept_no),
    head_emp_no: department?.head_emp_no === null || department === null ? "" : String(department.head_emp_no),
  })
  const [localError, setLocalError] = useState("")
  const mutation = useMutation()
  // 부서장 후보는 해당 부서 소속 재직 사원으로 안내한다. 최종 검증은 서버가 수행한다.
  const loadMembers = useCallback(() => department ? listEmployees({ dept_no: String(department.dept_no), tenure_status: "재직" }) : Promise.resolve([]), [department])
  const members = useWorkforceQuery(enabled && department !== null, loadMembers)
  const errors = firstFieldErrors(mutation.fieldErrors)

  async function save() {
    if (!department && !/^\d+$/.test(form.dept_no)) return setLocalError("부서번호는 숫자로 입력하세요.")
    if (!form.dept_name.trim()) return setLocalError("부서명을 입력하세요.")
    setLocalError("")
    const values = {
      dept_name: form.dept_name.trim(),
      parent_dept_no: form.parent_dept_no ? Number(form.parent_dept_no) : null,
      head_emp_no: form.head_emp_no ? Number(form.head_emp_no) : null,
    }
    const saved = await mutation.run(() => department
      ? updateDepartment(department.dept_no, values)
      : createDepartment({ dept_no: Number(form.dept_no), ...values, head_emp_no: null }))
    if (saved) onDone(saved)
  }

  const parents = departments.filter((item) => item.dept_no !== department?.dept_no)
  return (
    <Modal open title={department ? "부서 수정" : "부서 추가"} onClose={onClose} busy={mutation.pending} actions={<>
      <Button variant="secondary" onClick={onClose} disabled={mutation.pending}>닫기</Button>
      <Button pending={mutation.pending} onClick={() => void save()}>저장</Button>
    </>}>
      <div className={styles.stack}>
        {(localError || mutation.error) && <Alert tone="error">{localError || mutation.error}</Alert>}
        <TextInput label="부서번호" required inputMode="numeric" disabled={department !== null} value={form.dept_no} error={errors.dept_no} hint={department ? "부서번호는 변경할 수 없습니다." : undefined} onChange={(event) => setForm({ ...form, dept_no: event.target.value })} />
        <TextInput label="부서명" required value={form.dept_name} error={errors.dept_name} onChange={(event) => setForm({ ...form, dept_name: event.target.value })} />
        <Select label="상위 부서" value={form.parent_dept_no} error={errors.parent_dept_no} hint="계층 순환은 서버가 거절합니다." onChange={(event) => setForm({ ...form, parent_dept_no: event.target.value })}>
          <option value="">없음(최상위)</option>
          {parents.map((item) => <option key={item.dept_no} value={item.dept_no}>{item.dept_name} (#{item.dept_no})</option>)}
        </Select>
        {department
          ? <Select label="부서장" value={form.head_emp_no} error={errors.head_emp_no} hint={members.error || "해당 부서에 소속된 재직 사원만 지정할 수 있습니다."} onChange={(event) => setForm({ ...form, head_emp_no: event.target.value })}>
              <option value="">미지정</option>
              {form.head_emp_no && !members.data?.some((item) => String(item.emp_no) === form.head_emp_no) && <option value={form.head_emp_no}>사번 {form.head_emp_no}</option>}
              {members.data?.map((item) => <option key={item.emp_no} value={item.emp_no}>{item.name} (사번 {item.emp_no})</option>)}
            </Select>
          : <p className={styles.hint}>부서장은 부서를 만든 뒤 소속 사원을 배정하고 지정합니다.</p>}
      </div>
    </Modal>
  )
}

function Positions({ positions, canEdit, onChanged }: { positions: PositionSummary[]; canEdit: boolean; onChanged: () => void }) {
  const [editing, setEditing] = useState<PositionSummary | "new" | null>(null)
  const [notice, setNotice] = useState("")
  return (
    <Card title="직급" actions={canEdit && <Button size="small" onClick={() => setEditing("new")}>직급 추가</Button>}>
      {notice && <Alert tone="success">{notice}</Alert>}
      {!canEdit && <p className={styles.hint}>직급 변경은 인사관리자만 할 수 있습니다.</p>}
      {positions.length === 0
        ? <p className={styles.hint}>등록된 직급이 없습니다.</p>
        : <Table caption="직급 목록(정렬 순서)">
            <thead><tr><th scope="col">정렬</th><th scope="col">직급 코드</th><th scope="col">직급명</th>{canEdit && <th scope="col">작업</th>}</tr></thead>
            <tbody>
              {positions.map((item) => (
                <tr key={item.position_code}>
                  <td>{item.sort_order}</td>
                  <td>{item.position_code}</td>
                  <th scope="row">{item.position_name}</th>
                  {canEdit && <td><Button size="small" variant="secondary" onClick={() => setEditing(item)} aria-label={`${item.position_name} 수정`}>수정</Button></td>}
                </tr>
              ))}
            </tbody>
          </Table>}
      {editing && (
        <PositionDialog key={editing === "new" ? "new" : editing.position_code} position={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onDone={(saved) => { setEditing(null); setNotice(`${saved.position_name} 직급을 저장했습니다.`); onChanged() }} />
      )}
    </Card>
  )
}

function PositionDialog({ position, onClose, onDone }: { position: PositionSummary | null; onClose: () => void; onDone: (saved: PositionSummary) => void }) {
  const [form, setForm] = useState({ position_code: position?.position_code ?? "", position_name: position?.position_name ?? "", sort_order: String(position?.sort_order ?? "") })
  const [localError, setLocalError] = useState("")
  const mutation = useMutation()
  const errors = firstFieldErrors(mutation.fieldErrors)

  async function save() {
    if (!form.position_code.trim() || !form.position_name.trim()) return setLocalError("직급 코드와 직급명을 입력하세요.")
    if (!/^-?\d+$/.test(form.sort_order.trim())) return setLocalError("정렬 순서는 정수로 입력하세요.")
    setLocalError("")
    const values = { position_name: form.position_name.trim(), sort_order: Number(form.sort_order) }
    const saved = await mutation.run(() => position
      ? updatePosition(position.position_code, values)
      : createPosition({ position_code: form.position_code.trim(), ...values }))
    if (saved) onDone(saved)
  }

  return (
    <Modal open title={position ? "직급 수정" : "직급 추가"} onClose={onClose} busy={mutation.pending} actions={<>
      <Button variant="secondary" onClick={onClose} disabled={mutation.pending}>닫기</Button>
      <Button pending={mutation.pending} onClick={() => void save()}>저장</Button>
    </>}>
      <div className={styles.stack}>
        {(localError || mutation.error) && <Alert tone="error">{localError || mutation.error}</Alert>}
        <TextInput label="직급 코드" required maxLength={20} disabled={position !== null} value={form.position_code} error={errors.position_code} hint={position ? "직급 코드는 변경할 수 없습니다." : undefined} onChange={(event) => setForm({ ...form, position_code: event.target.value })} />
        <TextInput label="직급명" required value={form.position_name} error={errors.position_name} onChange={(event) => setForm({ ...form, position_name: event.target.value })} />
        <TextInput label="정렬 순서" required inputMode="numeric" value={form.sort_order} error={errors.sort_order} onChange={(event) => setForm({ ...form, sort_order: event.target.value })} />
      </div>
    </Modal>
  )
}
