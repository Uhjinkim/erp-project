import { useCallback, useEffect, useRef, useState } from "react"

import { Badge, Card, EmptyState, ErrorState, Select, Spinner, Table } from "../../../components/ui"
import { listEvaluationTargets, listEvaluations } from "../../../api/evaluation"
import type { CurrentUser } from "../../../types/auth"
import type { Evaluation, EvaluationTargetOption } from "../../../types/evaluation"
import { STATUS_TONE, creatableYears, errorText, evaluationHref, formatDateTime } from "../model"
import styles from "../evaluation.module.css"

/** evaluation-team: who the department head may evaluate, and the evaluations they own (FN-EV-001). */
export function TeamScreen({ user, enabled }: { user: CurrentUser; enabled: boolean }) {
  const myNo = user.employee?.emp_no ?? 0
  const years = creatableYears()
  const [year, setYear] = useState(years[0])
  const [targets, setTargets] = useState<EvaluationTargetOption[]>([])
  const [mine, setMine] = useState<Evaluation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const generation = useRef(0)

  const refresh = useCallback(async () => {
    if (!enabled) return
    const run = ++generation.current
    setLoading(true)
    setError("")
    try {
      const [targetList, evaluations] = await Promise.all([listEvaluationTargets(year), listEvaluations()])
      if (run !== generation.current) return
      setTargets(targetList)
      setMine(evaluations.filter((item) => item.evaluator_no === myNo))
    } catch (caught) {
      if (run === generation.current) setError(errorText(caught, "평가 대상을 불러오지 못했습니다."))
    } finally {
      if (run === generation.current) setLoading(false)
    }
  }, [enabled, myNo, year])

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0)
    return () => window.clearTimeout(timer)
  }, [refresh])

  if (error) return <ErrorState onRetry={() => void refresh()}>{error}</ErrorState>

  return <div className={styles.stack}>
    <div className={styles.toolbar}>
      <Select label="평가 연도" value={year} onChange={(event) => setYear(event.target.value)}>
        {years.map((item) => <option key={item} value={item}>{item}</option>)}
      </Select>
    </div>

    <Card title={`평가할 대상 · ${year}`}>
      {loading ? <Spinner /> : targets.length === 0
        ? <EmptyState title="새로 평가할 대상이 없습니다">부서장이 아니거나, 대상자 모두 이 연도 평가가 있거나, 근무 3개월 이하인 사원만 남았습니다.</EmptyState>
        : <Table caption={`${year}년 평가 작성 대상 ${targets.length}명`}>
          <thead><tr><th scope="col">이름</th><th scope="col">사번</th><th scope="col">부서</th><th scope="col">직급</th><th scope="col">작업</th></tr></thead>
          <tbody>{targets.map((target) => <tr key={target.emp_no}>
            <td>{target.name ?? "이름 없음"}</td><td>{target.emp_no}</td><td>{target.dept_no ?? "-"}</td><td>{target.pos_code ?? "-"}</td>
            <td><a className={styles.link} href={evaluationHref("evaluation-form", { empNo: String(target.emp_no), year })}>평가 작성</a></td>
          </tr>)}</tbody>
        </Table>}
    </Card>

    <Card title="내가 평가자인 평가">
      {loading ? <Spinner /> : mine.length === 0
        ? <EmptyState title="작성한 평가가 없습니다" />
        : <Table caption={`내가 평가자인 평가 ${mine.length}건`}>
          <thead><tr><th scope="col">대상</th><th scope="col">연도</th><th scope="col">점수</th><th scope="col">등급</th><th scope="col">상태</th><th scope="col">최근 변경</th></tr></thead>
          <tbody>{mine.map((item) => <tr key={item.eval_id}>
            <td><a className={styles.link} href={evaluationHref("evaluation-form", { evalId: String(item.eval_id) })}>{item.employee_name ?? item.emp_no}</a></td>
            <td>{item.eval_year}</td><td>{item.score}</td><td>{item.grade}</td>
            <td><Badge tone={STATUS_TONE[item.eval_status]}>{item.eval_status}</Badge></td>
            <td>{formatDateTime(item.updated_at)}</td>
          </tr>)}</tbody>
        </Table>}
    </Card>
  </div>
}
