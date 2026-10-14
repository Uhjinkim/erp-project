import { useState } from "react"
import type { FormEvent } from "react"
import { registerNewHire } from "../../../api/workforce"
import { Alert, Button, Card, DetailList } from "../../../components/ui"
import type { RegisteredEmployee } from "../../../types/workforce"
import { EmploymentFormFields } from "../components/EmploymentFormFields"
import type { MasterData } from "../hooks"
import { useMutation } from "../hooks"
import type { FieldErrors } from "../model"
import { departmentLabel, emptyEmploymentForm, firstFieldErrors, localToday, positionLabel, roleLabel, toNewHirePayload, validateEmploymentForm, workforceHref } from "../model"
import styles from "../workforce.module.css"

// FN-HR-006: 사원·최초 인사이력·역할·계정 등록을 서버의 단일 요청으로 처리한다(HR-007, HR-008).
export function EmployeeCreateScreen({ master }: { master: MasterData }) {
  const [form, setForm] = useState(() => emptyEmploymentForm(localToday()))
  const [localErrors, setLocalErrors] = useState<FieldErrors>({})
  const [registered, setRegistered] = useState<RegisteredEmployee | null>(null)
  const mutation = useMutation()

  async function submit(event: FormEvent) {
    event.preventDefault()
    const errors = validateEmploymentForm(form, "create")
    setLocalErrors(errors)
    if (Object.keys(errors).length) return
    const result = await mutation.run(() => registerNewHire(toNewHirePayload(form)))
    if (result) setRegistered(result)
  }

  if (registered) return <RegistrationResult result={registered} master={master} title="신규 사원을 등록했습니다" onReset={() => { setRegistered(null); setForm(emptyEmploymentForm(localToday())) }} />

  const errors = { ...firstFieldErrors(mutation.fieldErrors), ...localErrors }
  return (
    <Card title="신규 사원 등록" actions={<a href={workforceHref("employee-list")}>사원 목록</a>}>
      <form className={styles.stack} onSubmit={(event) => void submit(event)} noValidate>
        <p className={styles.hint}>사번은 서버가 자동 발급합니다. 등록 후 사번은 변경할 수 없습니다(HR-007).</p>
        {mutation.error && <Alert tone="error" title="등록하지 못했습니다">{mutation.error}</Alert>}
        <EmploymentFormFields mode="create" form={form} errors={errors} master={master} disabled={mutation.pending} onChange={(next) => { setForm(next); setLocalErrors({}) }} />
        <div className={styles.formFooter}>
          <a href={workforceHref("employee-list")}>취소</a>
          <Button type="submit" pending={mutation.pending}>사원 등록</Button>
        </div>
      </form>
    </Card>
  )
}

export function RegistrationResult({ result, master, title, onReset }: { result: RegisteredEmployee; master: MasterData; title: string; onReset?: () => void }) {
  return (
    <Card title={title}>
      <Alert tone="success">발급된 사번: {result.emp_no}. 초기 비밀번호는 다시 표시하지 않습니다.</Alert>
      <DetailList items={[
        { key: "emp", label: "사번", value: result.emp_no },
        { key: "name", label: "이름", value: result.name },
        { key: "email", label: "사내 이메일", value: result.email },
        { key: "org", label: "부서·직급", value: `${departmentLabel(master.departments, result.dept_no)} · ${positionLabel(master.positions, result.position_code)}` },
        { key: "hire", label: "입사일", value: result.hire_date },
        { key: "status", label: "재직 상태", value: result.tenure_status },
        { key: "roles", label: "업무 역할", value: result.roles.length ? result.roles.map((item) => roleLabel(master.roles, item.role_code)).join(", ") : "없음" },
        { key: "account", label: "로그인 계정", value: result.account ? `생성됨 (${result.account.email})` : "생성하지 않음" },
      ]} />
      <div className={styles.formFooter}>
        {onReset && <Button variant="secondary" onClick={onReset}>다른 사원 등록</Button>}
        <a href={workforceHref("employee-detail", { empNo: result.emp_no })}>사원 상세 보기</a>
      </div>
    </Card>
  )
}
