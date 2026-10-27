import { useState } from "react"
import type { FormEvent } from "react"
import { createChangeRequest } from "../../../api/profile"
import { Alert, Button, Card, ConfirmDialog, TextInput, Textarea } from "../../../components/ui"
import type { ApprovalRequiredValues } from "../../../types/profile"
import type { EmployeeDetail } from "../../../types/workforce"
import { useMutation } from "../hooks"
import type { ProfileEditForm as EditForm } from "../model"
import { displayValue, fieldLabel, firstFieldErrors, maskAccount, toEditForm, toEditPayload, validateEdit } from "../model"
import styles from "../profile.module.css"

type ProfileEditFormProps = {
  employee: EmployeeDetail
  onCancel: () => void
  onSubmitted: () => void
}

// FN-HR-002·003: 내 정보 수정 모드. 수정완료 → 확인 → 개인정보 수정 요청 제출. 인사관리자 승인 후 반영된다(HR-002).
export function ProfileEditForm({ employee, onCancel, onSubmitted }: ProfileEditFormProps) {
  const current: ApprovalRequiredValues = {
    phone: employee.phone, address: employee.address, email: employee.email, bank_code: employee.bank_code, account_no: employee.account_no,
  }
  const [form, setForm] = useState(() => toEditForm(current))
  const [localErrors, setLocalErrors] = useState<ReturnType<typeof validateEdit>>({})
  const [confirming, setConfirming] = useState(false)
  const mutation = useMutation()
  const payload = toEditPayload(form, current)
  const errors = { ...firstFieldErrors(mutation.fieldErrors), ...localErrors }

  function review(event: FormEvent) {
    event.preventDefault()
    const found = validateEdit(form, current)
    setLocalErrors(found)
    if (Object.keys(found).length) return
    mutation.reset()
    setConfirming(true)
  }

  async function submit() {
    const created = await mutation.run(() => createChangeRequest(payload))
    setConfirming(false)
    if (created) onSubmitted()
  }

  const update = (key: keyof EditForm, value: string) => {
    setForm({ ...form, [key]: value })
    setLocalErrors({})
  }

  return (
    <Card title="내 정보 수정">
      <form className={styles.stack} onSubmit={review} noValidate>
        <p className={styles.hint}>바꿀 항목을 고친 뒤 수정완료를 누르세요. 인사관리자가 승인하면 반영되며, 사내 이메일은 로그인 아이디에도 반영됩니다.</p>
        {(errors.form || mutation.error) && <Alert tone="error">{errors.form || mutation.error}</Alert>}
        <fieldset className={styles.plain} disabled={mutation.pending}>
          <div className={styles.fieldGrid}>
            <TextInput label="연락처" type="tel" autoComplete="tel" maxLength={20} value={form.phone} error={errors.phone} hint="비워 두면 미등록으로 바뀝니다." onChange={(event) => update("phone", event.target.value)} />
            <TextInput label="사내 이메일" type="email" maxLength={100} value={form.email} error={errors.email} onChange={(event) => update("email", event.target.value)} />
            <div className={styles.fullWidth}>
              <Textarea label="주소" autoComplete="street-address" maxLength={255} rows={3} value={form.address} error={errors.address} onChange={(event) => update("address", event.target.value)} />
            </div>
            <TextInput label="은행 코드" maxLength={20} value={form.bank_code} error={errors.bank_code} onChange={(event) => update("bank_code", event.target.value)} />
            <TextInput label="새 급여계좌번호" maxLength={100} autoComplete="off" value={form.account_no} error={errors.account_no} hint={`현재 ${maskAccount(employee.account_no)}. 계좌를 바꿀 때만 입력합니다.`} onChange={(event) => update("account_no", event.target.value)} />
          </div>
        </fieldset>
        <div className={styles.formFooter}>
          <Button variant="secondary" disabled={mutation.pending} onClick={onCancel}>취소</Button>
          <Button type="submit">수정완료</Button>
        </div>
      </form>
      <ConfirmDialog open={confirming} title="개인정보 수정 요청" confirmLabel="요청 제출" busy={mutation.pending} onClose={() => setConfirming(false)} onConfirm={() => void submit()}>
        <p>아래 내용으로 수정을 요청합니다. 인사관리자가 승인하면 반영됩니다.</p>
        <ul className={styles.changeList}>
          {(Object.keys(payload) as (keyof typeof payload)[]).map((field) => (
            <li key={field}><span className={styles.subtext}>{fieldLabel(field)}</span>{displayValue(field, payload[field] ?? null)}</li>
          ))}
        </ul>
      </ConfirmDialog>
    </Card>
  )
}
