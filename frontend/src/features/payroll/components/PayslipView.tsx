import type { ReactNode } from "react"

import { Badge } from "../../../components/ui"
import type { PayrollComponent, PayrollStatement } from "../../../types/payroll"
import { statusTone, won } from "../model"
import styles from "../payroll.module.css"

type PayslipViewProps = {
  statement: PayrollStatement
  components: PayrollComponent[]
  printing?: boolean
  actions?: ReactNode
}

// `payslip--printing` is the hook for styles/print.css; actions are hidden when printed.
export function PayslipView({ statement, components, printing = false, actions }: PayslipViewProps) {
  // Only nonzero items are listed; the API returns items already in payslip order.
  const nameByCode = new Map(components.map((component) => [component.code, component.name]))
  const lines = statement.items
    .filter((item) => Math.trunc(item.amount) !== 0)
    .map((item) => ({ name: nameByCode.get(item.component_code) ?? item.component_code, ...item }))
  const earnings = lines.filter((line) => line.category === "지급")
  const deductions = lines.filter((line) => line.category === "공제")
  const rowCount = Math.max(earnings.length, deductions.length, 1)

  return (
    <article className={`${styles.payslip} ${printing ? "payslip--printing" : ""}`}>
      <header className={styles.payslipHeader}>
        <h2>
          {statement.year}년 {statement.month}월 급여명세서
        </h2>
        <span className={styles.noPrint}>
          <Badge tone={statusTone(statement.status)}>{statement.status}</Badge>
        </span>
      </header>
      <dl className={styles.payslipMeta}>
        <div>
          <dt>성명</dt>
          <dd>{statement.employee.name ?? "-"}</dd>
        </div>
        <div>
          <dt>직급</dt>
          <dd>{statement.employee.position_name ?? "-"}</dd>
        </div>
        <div>
          <dt>사번</dt>
          <dd>{statement.employee_no}</dd>
        </div>
        <div>
          <dt>지급일</dt>
          <dd>{statement.payment_date}</dd>
        </div>
      </dl>
      <div className={styles.tableScroll}>
        <table className={styles.payslipTable}>
          <caption className={styles.visuallyHidden}>지급·공제 내역</caption>
          <thead>
            <tr>
              <th scope="col">지급내역 (A)</th>
              <th scope="col">지급액</th>
              <th scope="col">공제내역 (B)</th>
              <th scope="col">공제액</th>
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: rowCount }, (_, index) => {
              const earning = earnings[index]
              const deduction = deductions[index]
              return (
                <tr key={index}>
                  <td>{earning?.name ?? ""}</td>
                  <td>{earning ? won(earning.amount) : ""}</td>
                  <td>{deduction?.name ?? ""}</td>
                  <td>{deduction ? won(deduction.amount) : ""}</td>
                </tr>
              )
            })}
          </tbody>
          <tfoot>
            <tr>
              <td>지급총액</td>
              <td>{won(statement.total_earnings)}</td>
              <td>공제액 계</td>
              <td>{won(statement.total_deductions)}</td>
            </tr>
            <tr className={styles.netRow}>
              <td colSpan={3}>차인지급액 (C)</td>
              <td>{won(statement.net_pay)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
      {actions && <div className={`${styles.row} ${styles.noPrint}`}>{actions}</div>}
    </article>
  )
}
