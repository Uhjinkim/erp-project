import { useState } from "react"
import type { FormEvent } from "react"
import { createChangeRequest } from "../../../api/profile"
import { Alert, Button, Card, ConfirmDialog, DetailList, EmptyState, TextInput } from "../../../components/ui"
import type { PersonalInfoChangeRequest } from "../../../types/profile"
import type { EmployeeDetail } from "../../../types/workforce"
import { useMutation } from "../hooks"
import type { ChangeRequestForm } from "../model"
import { displayValue, fieldLabel, firstFieldErrors, maskAccount, navigate, profileHref, toChangeRequestPayload, validateChangeRequest } from "../model"
import styles from "../profile.module.css"

type ChangeRequestProps = {
  employee: EmployeeDetail
  pending: PersonalInfoChangeRequest | null
  onSubmitted: () => void
}

// FN-HR-003: 사내 이메일·급여계좌 변경 요청. 입력 → 확인 → 제출 후 내 요청 이력으로 이동한다.
export function ChangeRequestScreen({ employee, pending, onSubmitted }: ChangeRequestProps) {
  const [form, setForm] = useState<ChangeRequestForm>({ email: "", bank_code: "", account_no: "" })
  const [localErrors, setLocalErrors] = useState<ReturnType<typeof validateChangeRequest>>({})
  const [confirming, setConfirming] = useState(false)
  const mutation = useMutation()

  if (pending) {
    return (
      <EmptyState title="처리 대기 중인 변경 요청이 있습니다" action={<Button onClick={() => navigate(profileHref("change-history"))}>요청 이력 보기</Button>}>
        한 번에 하나의 요청만 처리할 수 있습니다. 기존 요청을 취소한 뒤 다시 요청하세요.
      </EmptyState>
    )
  }

  const payload = toChangeRequestPayload(form)
  const errors = { ...firstFieldErrors(mutation.fieldErrors), ...localErrors }

  function review(event: FormEvent) {
    event.preventDefault()
    const found = validateChangeRequest(form)
    setLocalErrors(found)
    if (Object.keys(found).length) return
    mutation.reset()
    setConfirming(true)
  }

  async function submit() {
    const created = await mutation.run(() => createChangeRequest(payload))
    setConfirming(false)
    if (created) {
      onSubmitted()
      navigate(profileHref("change-history", { saved: "request" }))
    }
  }

  const update = (key: keyof ChangeRequestForm, value: string) => {
    setForm({ ...form, [key]: value })
    setLocalErrors({})
  }

  return (
    <div className={styles.stack}>
      <Card title="현재 등록 정보">
        <DetailList items={[
          { key: "email", label: "사내 이메일", value: employee.email ?? "미등록" },
          { key: "bank", label: "은행 코드", value: employee.bank_code ?? "미등록" },
          { key: "account", label: "급여계좌", value: maskAccount(employee.account_no) },
        ]} />
      </Card>
      <Card title="변경 요청">
        <form className={styles.stack} onSubmit={review} noValidate>
          <p className={styles.hint}>바꿀 항목만 입력하세요. 인사관리자가 승인하면 반영되며, 사내 이메일은 로그인 아이디에도 반영됩니다.</p>
          {(errors.form || mutation.error) && <Alert tone="error">{errors.form || mutation.error}</Alert>}
          <fieldset className={styles.plain} disabled={mutation.pending}>
            <div className={styles.fieldGrid}>
              <div className={styles.fullWidth}>
                <TextInput label="새 사내 이메일" type="email" maxLength={100} value={form.email} error={errors.email} onChange={(event) => update("email", event.target.value)} />
              </div>
              <TextInput label="새 은행 코드" maxLength={20} value={form.bank_code} error={errors.bank_code} hint="계좌를 바꿀 때는 은행 코드와 계좌번호를 함께 입력합니다." onChange={(event) => update("bank_code", event.target.value)} />
              <TextInput label="새 급여계좌번호" maxLength={100} autoComplete="off" value={form.account_no} error={errors.account_no} onChange={(event) => update("account_no", event.target.value)} />
            </div>
          </fieldset>
          <div className={styles.formFooter}>
            <Button variant="secondary" onClick={() => navigate(profileHref("my-profile"))}>취소</Button>
            <Button type="submit">요청 내용 확인</Button>
          </div>
        </form>
      </Card>
      <ConfirmDialog open={confirming} title="변경 요청 제출" confirmLabel="요청 제출" busy={mutation.pending} onClose={() => setConfirming(false)} onConfirm={() => void submit()}>
        <p>아래 내용으로 변경을 요청합니다.</p>
        <ul className={styles.changeList}>
          {(Object.keys(payload) as (keyof typeof payload)[]).map((field) => (
            <li key={field}><span className={styles.subtext}>{fieldLabel(field)}</span>{displayValue(field, payload[field] ?? null)}</li>
          ))}
        </ul>
      </ConfirmDialog>
    </div>
  )
}
