import { routeHref } from "../../../app/routing"
import { Button, Card, ErrorState, Spinner, Table } from "../../../components/ui"
import { useManagerData } from "../hooks/useManagerData"
import { currentPeriod, periodLabel, summarizePeriods } from "../model"
import styles from "../payroll.module.css"

const href = (screenId: string, period: string) => routeHref({ moduleId: "payroll", screenId, search: `period=${period}` })

export function PeriodsScreen({ enabled }: { enabled: boolean }) {
  const { data, error, loading, reload } = useManagerData(enabled)
  if (error && !data) return <ErrorState onRetry={() => void reload()}>{error}</ErrorState>
  if (!data) return <Spinner label="정산 기간을 불러오는 중" />

  const summaries = summarizePeriods(data.targets, data.statements, currentPeriod())
  return (
    <Card title="정산월별 처리 현황" actions={<Button variant="secondary" size="small" pending={loading} onClick={() => void reload()}>새로고침</Button>}>
      <p className={styles.hint}>미작성은 현재 재직 중인 사원 가운데 해당 월 급여가 없는 사람 수입니다.</p>
      <Table caption="급여 정산 기간 목록">
        <thead>
          <tr>
            <th scope="col">정산월</th>
            <th scope="col">대상</th>
            <th scope="col">작성중</th>
            <th scope="col">확정</th>
            <th scope="col">미작성</th>
            <th scope="col">바로가기</th>
          </tr>
        </thead>
        <tbody>
          {summaries.map((summary) => (
            <tr key={summary.period}>
              <th scope="row">{periodLabel(summary.period)}</th>
              <td>{summary.drafts + summary.confirmed + summary.missing}</td>
              <td>{summary.drafts}</td>
              <td>{summary.confirmed}</td>
              <td>{summary.missing}</td>
              <td>
                <span className={styles.links}>
                  <a href={href("payroll-item", summary.period)}>정산 항목</a>
                  <a href={href("payroll-confirm", summary.period)}>확정·정정</a>
                  {summary.missing > 0 && <a href={href("payroll-create", summary.period)}>정산 생성</a>}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>
  )
}
