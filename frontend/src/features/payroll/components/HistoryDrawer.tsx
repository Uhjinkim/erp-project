import { useEffect, useState } from "react"

import { loadPayrollHistory } from "../../../api/payroll"
import { Alert, Drawer, EmptyState, Spinner } from "../../../components/ui"
import type { PayrollHistoryEntry, PayrollStatement } from "../../../types/payroll"
import styles from "../payroll.module.css"

type HistoryDrawerProps = {
  statement: PayrollStatement | null
  onClose: () => void
}

// Payroll managers receive actor and reason; owners receive only action and date.
export function HistoryDrawer({ statement, onClose }: HistoryDrawerProps) {
  const statementId = statement?.statement_id ?? null
  const [loaded, setLoaded] = useState<{ id: number; entries: PayrollHistoryEntry[] } | null>(null)
  const [error, setError] = useState<{ id: number; message: string } | null>(null)

  useEffect(() => {
    if (statementId === null) return
    let current = true
    loadPayrollHistory(statementId)
      .then((entries) => { if (current) setLoaded({ id: statementId, entries }) })
      .catch((failure: unknown) => {
        if (current) setError({ id: statementId, message: failure instanceof Error ? failure.message : "이력을 불러오지 못했습니다." })
      })
    return () => { current = false }
  }, [statementId])

  // A click on the dimmed backdrop targets the open <dialog> itself but lands outside its box.
  // Module-local until the shared Modal offers this (requested from F0).
  useEffect(() => {
    if (statementId === null) return
    function closeOnBackdrop(event: MouseEvent) {
      const dialog = event.target
      if (!(dialog instanceof HTMLDialogElement) || !dialog.open) return
      const box = dialog.getBoundingClientRect()
      const inside = event.clientX >= box.left && event.clientX <= box.right && event.clientY >= box.top && event.clientY <= box.bottom
      if (!inside) onClose()
    }
    document.addEventListener("click", closeOnBackdrop)
    return () => document.removeEventListener("click", closeOnBackdrop)
  }, [statementId, onClose])

  const entries = loaded?.id === statementId ? loaded.entries : null
  const message = error?.id === statementId ? error.message : ""
  const title = statement
    ? `${statement.employee.name ?? statement.employee_no} · ${statement.year}년 ${statement.month}월 이력`
    : "처리 이력"

  return (
    <Drawer open={statement !== null} title={title} onClose={onClose}>
      {message && <Alert tone="error">{message}</Alert>}
      {!message && entries === null && <Spinner label="이력을 불러오는 중" />}
      {entries?.length === 0 && <EmptyState title="이력이 없습니다" />}
      {entries && entries.length > 0 && (
        <ol className={styles.history}>
          {entries.map((entry) => {
            const detailed = entry.actor_name !== undefined
            const changedAt = new Date(entry.changed_at)
            return (
              <li key={entry.history_id}>
                <strong>{entry.action}</strong>
                <span className={styles.hint}>
                  {detailed ? changedAt.toLocaleString("ko-KR") : changedAt.toLocaleDateString("ko-KR")}
                  {detailed && ` · ${entry.actor_name ?? "알 수 없음"}`}
                </span>
                {detailed && entry.reason && <p>{entry.reason}</p>}
              </li>
            )
          })}
        </ol>
      )}
    </Drawer>
  )
}
