import { Badge } from "../../../components/ui"
import type { EmployeeDetail } from "../../../types/workforce"
import { tenureTone } from "../model"
import styles from "../workforce.module.css"

// 처리 화면 상단에 대상 사원을 식별하는 최소 정보만 보여 준다. 계좌 등 개인정보는 넣지 않는다.
export function EmployeeSummary({ employee }: { employee: EmployeeDetail }) {
  return (
    <dl className={styles.summary}>
      <div><dt>사원</dt><dd>{employee.name} <span className={styles.subtext}>사번 {employee.emp_no}</span></dd></div>
      <div><dt>부서·직급</dt><dd>{employee.dept_name ?? "미배정"} · {employee.position_name ?? "미배정"}</dd></div>
      <div><dt>재직 상태</dt><dd><Badge tone={tenureTone(employee.tenure_status)}>{employee.tenure_status}</Badge></dd></div>
      <div><dt>입사일 / 퇴사일</dt><dd>{employee.hire_date} / {employee.term_date ?? "-"}</dd></div>
    </dl>
  )
}
