import { useState } from "react"
import type { FormEvent } from "react"
import { updateMyContact } from "../../../api/profile"
import { Alert, Button, Card, TextInput, Textarea } from "../../../components/ui"
import type { EmployeeDetail } from "../../../types/workforce"
import { useMutation } from "../hooks"
import { contactChanged, firstFieldErrors, navigate, profileHref, toContactPayload } from "../model"
import styles from "../profile.module.css"

// FN-HR-002: 연락처·주소 직접 수정. 저장 후 내 인사정보로 돌아간다.
export function ContactEditScreen({ employee, onSaved }: { employee: EmployeeDetail; onSaved: (employee: EmployeeDetail) => void }) {
  const [form, setForm] = useState({ phone: employee.phone ?? "", address: employee.address ?? "" })
  const mutation = useMutation()
  const errors = firstFieldErrors(mutation.fieldErrors)
  const changed = contactChanged(form, employee)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!changed) return
    const updated = await mutation.run(() => updateMyContact(toContactPayload(form)))
    if (updated) {
      onSaved(updated)
      navigate(profileHref("my-profile", { saved: "contact" }))
    }
  }

  return (
    <Card title="연락처·주소 수정">
      <form className={styles.stack} onSubmit={(event) => void submit(event)} noValidate>
        <p className={styles.hint}>연락처·주소는 승인 없이 바로 반영됩니다. 비워 두면 미등록으로 저장됩니다.</p>
        {mutation.error && <Alert tone="error" title="저장하지 못했습니다">{mutation.error}</Alert>}
        <fieldset className={styles.plain} disabled={mutation.pending}>
          <TextInput label="연락처" type="tel" autoComplete="tel" maxLength={20} value={form.phone} error={errors.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} />
          <Textarea label="주소" autoComplete="street-address" maxLength={255} rows={3} value={form.address} error={errors.address} onChange={(event) => setForm({ ...form, address: event.target.value })} />
        </fieldset>
        <div className={styles.formFooter}>
          <Button variant="secondary" disabled={mutation.pending} onClick={() => navigate(profileHref("my-profile"))}>취소</Button>
          <Button type="submit" pending={mutation.pending} disabled={!changed}>저장</Button>
        </div>
        {!changed && <p className={styles.hint}>변경된 내용이 없습니다.</p>}
      </form>
    </Card>
  )
}
