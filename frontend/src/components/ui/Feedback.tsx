import type { ReactNode } from "react"
import styles from "./ui.module.css"
import { Button } from "./Button"

export type Tone = "neutral" | "info" | "success" | "warning" | "error"
const toneClass = (tone: Tone) => tone === "error" ? styles.errorTone : styles[tone] ?? ""

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`${styles.badge} ${toneClass(tone)}`}>{children}</span>
}

export function Alert({ tone = "info", title, children }: { tone?: Tone; title?: string; children: ReactNode }) {
  return <div className={`${styles.alert} ${toneClass(tone)}`} role={tone === "error" ? "alert" : "status"}>{title && <strong>{title}</strong>}{children}</div>
}

export function Spinner({ label = "불러오는 중" }: { label?: string }) {
  return <span role="status"><span className={styles.spinner} aria-hidden="true" /> {label}</span>
}

export function Skeleton({ label = "내용을 불러오는 중" }: { label?: string }) {
  return <div className={styles.skeleton} role="status" aria-label={label} />
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return <section className={styles.state}><h2>{title}</h2>{children && <p>{children}</p>}{action}</section>
}

export function ErrorState({ title = "화면을 불러오지 못했습니다", children, onRetry }: { title?: string; children?: ReactNode; onRetry?: () => void }) {
  return <EmptyState title={title} action={onRetry && <Button onClick={onRetry}>다시 시도</Button>}>{children}</EmptyState>
}
