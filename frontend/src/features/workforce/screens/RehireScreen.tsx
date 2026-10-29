import { useCallback, useState } from "react"
import type { FormEvent } from "react"
import { getEmployeeDetail, listRetiredEmployees, rehirePerson } from "../../../api/workforce"
import { Alert, Button, Card, EmptyState } from "../../../components/ui"
import type { EmployeeDetail, RegisteredEmployee } from "../../../types/workforce"
import { EmployeeLookup } from "../components/EmployeeLookup"
import type { LookupRow } from "../components/EmployeeLookup"
import { EmployeeSummary } from "../components/EmployeeSummary"
import { EmploymentFormFields } from "../components/EmploymentFormFields"
import { QueryFallback } from "../components/QueryFallback"
import type { MasterData } from "../hooks"
import { useMutation, useWorkforceQuery } from "../hooks"
import type { FieldErrors } from "../model"
import { emptyEmploymentForm, firstFieldErrors, localToday, parseId, toRehirePayload, validateEmploymentForm, workforceHref } from "../model"
import styles from "../workforce.module.css"
import { RegistrationResult } from "./EmployeeCreateScreen"

const loadRetired = async (keyword: string): Promise<LookupRow[]> => {
  const byNumber = /^\d+$/.test(keyword)
  const rows = await listRetiredEmployees(byNumber ? { emp_no: keyword } : { name: keyword })
  return rows.map((row) => ({
    emp_no: row.emp_no, name: row.name, status: "퇴사",
    organization: `${row.dept_name ?? "미배정"} · ${row.position_name ?? "미배정"}`,
    dates: `${row.hire_date} ~ ${row.term_date}`,
  }))
}

// Query key: empNo(이전 고용의 사번). 없으면 퇴사자 검색으로 대상을 고른다.
export function RehireScreen({ enabled, search, master }: { enabled: boolean; search: URLSearchParams; master: MasterData }) {
  const empNo = parseId(search.get("empNo"))
  if (empNo === null) {
    return <EmployeeLookup title="재입사 대상 선택" description="퇴사 처리된 사원을 검색합니다." enabled={enabled} load={loadRetired} hrefFor={(row) => workforceHref("rehire", { empNo: row.emp_no })} actionLabel="재입사 처리" />
  }
  return <RehireView empNo={empNo} enabled={enabled} master={master} />
}

function RehireView({ empNo, enabled, master }: { empNo: number; enabled: boolean; master: MasterData }) {
  const load = useCallback(() => getEmployeeDetail(empNo), [empNo])
  const previous = useWorkforceQuery(enabled, load)
  if (!previous.data) return <QueryFallback query={previous} label="이전 고용 정보를 불러오는 중" />
  if (previous.data.tenure_status !== "퇴사") {
    return <EmptyState title="퇴사한 고용만 재입사할 수 있습니다" action={<a href={workforceHref("employee-detail", { empNo })}>사원 상세로 이동</a>}>현재 상태: {previous.data.tenure_status}</EmptyState>
  }
  return <RehireForm previous={previous.data} master={master} />
}

function RehireForm({ previous, master }: { previous: EmployeeDetail; master: MasterData }) {
  const [form, setForm] = useState(() => ({
    ...emptyEmploymentForm(localToday()),
    // 사내 이메일 중복 여부는 서버가 판단하므로 이전 값을 자동으로 채우지 않는다.
    phone: previous.phone ?? "", address: previous.address ?? "",
  }))
  const [localErrors, setLocalErrors] = useState<FieldErrors>({})
  const [registered, setRegistered] = useState<RegisteredEmployee | null>(null)
  const mutation = useMutation()

  async function submit(event: FormEvent) {
    event.preventDefault()
    const errors = validateEmploymentForm(form, "rehire")
    setLocalErrors(errors)
    if (Object.keys(errors).length) return
    const result = await mutation.run(() => rehirePerson(previous.person_id, toRehirePayload(form)))
    if (result) setRegistered(result)
  }

  if (registered) return <RegistrationResult result={registered} master={master} title="재입사를 처리했습니다" />

  const errors = { ...firstFieldErrors(mutation.fieldErrors), ...localErrors }
  return (
    <div className={styles.stack}>
      <Card title="이전 고용 정보" actions={<a href={workforceHref("employee-detail", { empNo: previous.emp_no })}>이전 사원 상세</a>}>
        <EmployeeSummary employee={previous} />
      </Card>
      <Card title="재입사 처리">
        <form className={styles.stack} onSubmit={(event) => void submit(event)} noValidate>
          <p className={styles.hint}>재입사일은 마지막 퇴사일({previous.term_date}) 이후여야 합니다.</p>
          {mutation.error && <Alert tone="error" title="재입사를 처리하지 못했습니다">{mutation.error}</Alert>}
          <EmploymentFormFields mode="rehire" form={form} errors={errors} master={master} disabled={mutation.pending} onChange={(next) => { setForm(next); setLocalErrors({}) }} />
          <div className={styles.formFooter}>
            <a href={workforceHref("employee-list", { view: "retired" })}>취소</a>
            <Button type="submit" pending={mutation.pending}>재입사 등록</Button>
          </div>
        </form>
      </Card>
    </div>
  )
}
