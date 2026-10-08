import type { EmployeeDetail } from "../types/workforce"

type EmployeeInfoCardProps = {
  title: string
  employee: EmployeeDetail | null
  loading: boolean
  onBack?: () => void
}

const genderLabels: Record<string, string> = { M: "남성", F: "여성" }

export function EmployeeInfoCard({ title, employee, loading, onBack }: EmployeeInfoCardProps) {
  const rows: [string, string][] = employee
    ? [
        ["사번", String(employee.emp_no)],
        ["부서", employee.dept_name ?? "미배정"],
        ["직급", employee.position_name ?? "미배정"],
        ["재직 상태", employee.tenure_status],
        ["입사일", employee.hire_date],
        ["퇴사일", employee.term_date ?? "-"],
        ["생년월일", employee.birth_date ?? "미등록"],
        ["성별", employee.gender ? genderLabels[employee.gender] ?? employee.gender : "미등록"],
        ["이메일", employee.email ?? "미등록"],
        ["연락처", employee.phone ?? "미등록"],
        ["내선번호", employee.extension_no ?? "미등록"],
        ["주소", employee.address ?? "미등록"],
        ["은행 코드", employee.bank_code ?? "미등록"],
        ["급여계좌", employee.account_no ?? "미등록"],
      ]
    : []

  return (
    <section className="list-panel employee-info" aria-busy={loading}>
      <div className="section-heading">
        <div>
          <p className="step">PROFILE</p>
          <h2>{title}{employee && <span className="employee-info__name"> · {employee.name}</span>}</h2>
        </div>
        {onBack && <button className="refresh" type="button" onClick={onBack}>내 정보 보기</button>}
      </div>
      {employee
        ? <dl className="employee-info__grid">
            {rows.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
          </dl>
        : <div className="empty">{loading ? "인사 정보를 불러오고 있습니다." : "표시할 인사 정보가 없습니다."}</div>}
    </section>
  )
}
