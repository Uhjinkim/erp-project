import { useState } from "react"
import type { FormEvent } from "react"
import { ApiError } from "../../../api/client"
import { createVacation, resubmitVacation } from "../../../api/vacation"
import { Alert, Button, Card, DetailList, Select, Textarea, TextInput } from "../../../components/ui"
import type { VacationInput, VacationRequest, VacationType } from "../../../types/vacation"
import { formFromRequest, formWithVacationType, transportInput, validateInput } from "../model"
import { useVacationBalances, useVacationMutation } from "../hooks"
import { RequestSummary } from "./RequestSummary"
import type { VacationHref } from "../navigation"
import styles from "../vacation.module.css"

/** FN-LV-001/FN-LV-007 share transport validation, not approval or balance policies. */
export function RequestForm({ employeeNo, types, initial, href }: { employeeNo: number; types: VacationType[]; initial?: VacationRequest; href: VacationHref }) {
  const [form, setForm] = useState<VacationInput>(formFromRequest(initial))
  const [errors, setErrors] = useState<Record<string, string>>({})
  const mutation = useVacationMutation()
  const balances = useVacationBalances(employeeNo, types)
  const selected = balances.types.find((type) => type.type_id === form.type_id)
  const remaining = selected?.remaining_days
  const balanceText = !form.type_id ? "휴가 유형을 선택하세요" : balances.pending ? "조회 중…" : balances.error ? "조회 실패 · 다시 조회하세요" : remaining === undefined ? "확인 불가" : remaining === null ? "제한 없음" : `${remaining}일`
  const shortage = !balances.pending && !balances.error && remaining != null && Number(form.use_days) > Number(remaining)
  const serverErrors = mutation.error instanceof ApiError ? mutation.error.fieldErrors : {}
  const error = (field: keyof VacationInput) => errors[field] ?? serverErrors[field]?.[0]
  const set = (field: keyof VacationInput, value: string) => setForm((current) => ({ ...current, [field]: value }))

  async function submit(event: FormEvent) {
    event.preventDefault()
    const nextErrors = validateInput(form)
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length) {
      window.setTimeout(() => document.querySelector<HTMLInputElement>("[aria-invalid=true]")?.focus(), 0)
      return
    }
    const input = transportInput(form)
    await mutation.execute(() => initial ? resubmitVacation(employeeNo, initial.request_id, input) : createVacation(employeeNo, input))
  }

  if (mutation.saved) return <div className={styles.stack}>
    <Alert tone="success">{initial ? "수정한 휴가를 다시 신청했습니다." : "휴가를 신청했습니다."}</Alert>
    <RequestSummary item={mutation.saved} types={types} />
    <div className={styles.row}><a href={href("leave-detail", mutation.saved.request_id)}>상세·이력 확인</a><a href={href("leave-mine")}>내 신청 목록</a>{initial ? <a href={href("leave-apply")}>새 휴가 신청</a> : <Button variant="secondary" onClick={() => { mutation.reset(); setForm(formFromRequest()); setErrors({}); void balances.refresh() }}>새 휴가 신청</Button>}</div>
  </div>

  return <div className={styles.workspace}>
    <Card title={initial ? `LV-${initial.request_id} 수정·재신청` : "휴가 정보 입력"}>
      <form className={styles.stack} onSubmit={submit}>
        {mutation.error && <Alert tone="error">{mutation.error.message}</Alert>}
        {Object.keys(errors).length > 0 && <Alert tone="error">입력한 항목을 확인하세요.</Alert>}
        <Select label="휴가 유형" required value={form.type_id} disabled={mutation.pending} error={error("type_id")} onChange={(event) => setForm((current) => formWithVacationType(current, types.find((type) => type.type_id === event.target.value)))}>
          <option value="">유형 선택</option>
          {initial && !types.some((type) => type.type_id === initial.type_id) && <option value={initial.type_id}>{initial.type_id} · 기존 유형</option>}
          {types.map((type) => <option key={type.type_id} value={type.type_id}>{type.type_name}</option>)}
        </Select>
        <div className={styles.balance} role="region" aria-label="선택 유형 잔여일수">
          <div className={styles.row}>
            <strong>잔여일수 <span role="status">{balanceText}</span></strong>
            <Button variant="secondary" size="small" pending={balances.pending} onClick={() => { void balances.refresh() }}>잔여일수 새로고침</Button>
          </div>
          {balances.error && <Alert tone="error">{balances.error.message}</Alert>}
          {shortage && <Alert tone="warning">입력한 사용 일수가 현재 잔여일수를 초과합니다.</Alert>}
        </div>
        <div className={styles.fields}>
          <TextInput label="시작 일시" type="datetime-local" step="60" min={form.start_datetime ? `${form.start_datetime.slice(0, 10)}T09:00` : undefined} required value={form.start_datetime} disabled={mutation.pending} error={error("start_datetime")} onChange={(event) => set("start_datetime", event.target.value)} />
          <TextInput label="종료 일시" type="datetime-local" step="60" required value={form.end_datetime} disabled={mutation.pending} error={error("end_datetime")} onChange={(event) => set("end_datetime", event.target.value)} />
        </div>
        <TextInput label="사용 일수" type="number" required min="0.01" max="9.99" step="0.01" value={form.use_days} disabled={mutation.pending} error={error("use_days")} onChange={(event) => set("use_days", event.target.value)} />
        <Textarea label="신청 사유" maxLength={255} rows={4} value={form.reason} disabled={mutation.pending} error={error("reason")} hint={`${form.reason.length}/255자`} onChange={(event) => set("reason", event.target.value)} />
        <div className={styles.row}><Button type="submit" pending={mutation.pending} disabled={types.length === 0}>{initial ? "다시 승인 요청" : "승인 요청"}</Button><a href={href(initial ? "leave-detail" : "leave-mine", initial?.request_id)}>돌아가기</a></div>
      </form>
    </Card>
    <div className={styles.stack}>
      <Card title="신청 전 확인"><DetailList items={[
        { key: "days", label: "이번 신청", value: `${form.use_days || "0"}일` },
        { key: "approver", label: "승인자", value: "신청 시 자동 지정" },
      ]} /></Card>
    </div>
  </div>
}
