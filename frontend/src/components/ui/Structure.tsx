import { Fragment } from "react"
import type { ReactNode, TableHTMLAttributes } from "react"
import styles from "./ui.module.css"

export function Card({ title, children, actions }: { title?: string; children: ReactNode; actions?: ReactNode }) {
  return <section className={styles.card}>{title && <div className={styles.header}><h2>{title}</h2>{actions}</div>}{children}</section>
}

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return <section><h2>{title}</h2>{children}</section>
}

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return <header className={styles.header}><div><h1 id="page-heading" tabIndex={-1}>{title}</h1>{description && <p>{description}</p>}</div>{actions}</header>
}

export function DetailList({ items }: { items: { key: string; label: string; value: ReactNode }[] }) {
  return <dl className={styles.details}>{items.map((item) => <Fragment key={item.key}><dt>{item.label}</dt><dd>{item.value}</dd></Fragment>)}</dl>
}

export function Table({ caption, children, ...props }: TableHTMLAttributes<HTMLTableElement> & { caption: string }) {
  return <div className={styles.tableWrap} role="region" aria-label={caption} tabIndex={0}><table {...props} className={styles.table}><caption>{caption}</caption>{children}</table></div>
}
