import { useCallback, useState } from "react"

import { downloadPayslipExcel, loadMyPayrollStatements, loadPayrollComponents } from "../../../api/payroll"
import { Alert, Button, Card, EmptyState, ErrorState, Spinner, Table } from "../../../components/ui"
import type { PayrollStatement } from "../../../types/payroll"
import { HistoryDrawer } from "../components/HistoryDrawer"
import { PayslipView } from "../components/PayslipView"
import { usePayrollQuery } from "../hooks/usePayrollQuery"
import { usePayslipPrint } from "../hooks/usePayslipPrint"
import { won } from "../model"
import styles from "../payroll.module.css"

// The API returns only the signed-in employee's confirmed statements.
export function PayslipScreen({ enabled }: { enabled: boolean }) {
  const load = useCallback(async () => {
    const [components, statements] = await Promise.all([loadPayrollComponents(), loadMyPayrollStatements()])
    return { components, statements }
  }, [])
  const { data, error, reload } = usePayrollQuery(enabled, load)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [historyFor, setHistoryFor] = useState<PayrollStatement | null>(null)
  const [message, setMessage] = useState("")
  const { printingId, print } = usePayslipPrint()

  if (error && !data) return <ErrorState onRetry={() => void reload()}>{error}</ErrorState>
  if (!data) return <Spinner label="급여명세를 불러오는 중" />
  if (data.statements.length === 0) return <EmptyState title="확정된 급여명세가 없습니다">급여가 확정되면 여기에서 볼 수 있습니다.</EmptyState>

  const statements = [...data.statements].sort((left, right) => right.year - left.year || right.month - left.month)
  const selected = statements.find((statement) => statement.statement_id === selectedId) ?? statements[0]

  async function saveExcel(statement: PayrollStatement) {
    setMessage("")
    try {
      await downloadPayslipExcel(statement)
    } catch (failure) {
      setMessage(failure instanceof Error ? failure.message : "급여명세서를 내려받지 못했습니다.")
    }
  }

  return (
    <div className={styles.workspace}>
      <Card title="월별 급여명세">
        <Table caption="내 급여명세 목록">
          <thead>
            <tr>
              <th scope="col">정산월</th>
              <th scope="col">지급일</th>
              <th scope="col" className={styles.amount}>차인지급액</th>
              <th scope="col"><span className={styles.visuallyHidden}>선택</span></th>
            </tr>
          </thead>
          <tbody>
            {statements.map((statement) => {
              const current = statement.statement_id === selected.statement_id
              return (
                <tr key={statement.statement_id} aria-selected={current}>
                  <th scope="row">{statement.year}년 {statement.month}월</th>
                  <td>{statement.payment_date}</td>
                  <td className={styles.amount}>{won(statement.net_pay)}</td>
                  <td>
                    <Button size="small" variant={current ? "primary" : "secondary"} aria-pressed={current} onClick={() => setSelectedId(statement.statement_id)}>
                      보기
                    </Button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </Table>
      </Card>

      <div className={styles.stack}>
        {message && <Alert tone="error">{message}</Alert>}
        <PayslipView
          statement={selected}
          components={data.components}
          printing={printingId === selected.statement_id}
          actions={
            <>
              <Button variant="secondary" onClick={() => print(selected.statement_id)}>PDF 저장·인쇄</Button>
              <Button variant="secondary" onClick={() => void saveExcel(selected)}>엑셀 저장</Button>
              <Button variant="ghost" onClick={() => setHistoryFor(selected)}>이력</Button>
            </>
          }
        />
      </div>
      <HistoryDrawer statement={historyFor} onClose={() => setHistoryFor(null)} />
    </div>
  )
}
