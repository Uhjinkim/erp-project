import { useCallback, useEffect, useRef, useState } from "react"

import { Card, DetailList, EmptyState, ErrorState, Spinner } from "../../../components/ui"
import { listEvaluations } from "../../../api/evaluation"
import type { CurrentUser } from "../../../types/auth"
import type { Evaluation } from "../../../types/evaluation"
import { errorText, formatDateTime } from "../model"
import styles from "../evaluation.module.css"

/** evaluation-mine: the employee's own confirmed evaluations (EV-005); unconfirmed ones never arrive. */
export function MineScreen({ user, enabled }: { user: CurrentUser; enabled: boolean }) {
  const myNo = user.employee?.emp_no ?? 0
  const [items, setItems] = useState<Evaluation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const generation = useRef(0)

  const refresh = useCallback(async () => {
    if (!enabled) return
    const run = ++generation.current
    setLoading(true)
    setError("")
    try {
      const list = await listEvaluations()
      if (run !== generation.current) return
      setItems(list.filter((item) => item.emp_no === myNo && item.eval_status === "확정")
        .sort((a, b) => b.eval_year.localeCompare(a.eval_year)))
    } catch (caught) {
      if (run === generation.current) setError(errorText(caught, "평가 결과를 불러오지 못했습니다."))
    } finally {
      if (run === generation.current) setLoading(false)
    }
  }, [enabled, myNo])

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0)
    return () => window.clearTimeout(timer)
  }, [refresh])

  if (error) return <ErrorState onRetry={() => void refresh()}>{error}</ErrorState>
  if (loading) return <Spinner label="평가 결과를 불러오는 중" />
  if (items.length === 0) return <EmptyState title="확정된 평가가 없습니다">평가는 인사관리자가 확정한 뒤에 이 화면에 나타납니다.</EmptyState>

  return <div className={styles.stack}>
    {items.map((item) => <Card key={item.eval_id} title={`${item.eval_year}년 평가`}>
      <div className={styles.result}>
        <span className={styles.score}>{item.grade} · {item.score}점</span>
        <DetailList items={[
          { key: "evaluator", label: "평가자", value: item.evaluator_name ?? item.evaluator_no },
          { key: "dept", label: "기준 부서", value: item.snapshot_dept_no ?? "-" },
          { key: "confirmed", label: "확정일", value: formatDateTime(item.confirmed_at) },
        ]} />
        {item.comments && <p className={styles.comments}>{item.comments}</p>}
      </div>
    </Card>)}
  </div>
}
