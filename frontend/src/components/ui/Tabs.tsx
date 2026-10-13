import { useId } from "react"
import type { ReactNode } from "react"
import styles from "./ui.module.css"

export function Tabs({ label, items, value, onChange, children }: {
  label: string
  items: { value: string; label: string }[]
  value: string
  onChange: (value: string) => void
  children: ReactNode
}) {
  const id = useId()
  const selected = items.findIndex((item) => item.value === value)
  return <div>
    <div className={styles.tabs} role="tablist" aria-label={label}>
      {items.map((item, index) => <button key={item.value} id={`${id}-tab-${index}`} role="tab" type="button" aria-selected={item.value === value} aria-controls={`${id}-panel`} tabIndex={item.value === value ? 0 : -1} className={styles.tab} onClick={() => onChange(item.value)} onKeyDown={(event) => {
        let next: number
        if (event.key === "ArrowRight") next = (index + 1) % items.length
        else if (event.key === "ArrowLeft") next = (index - 1 + items.length) % items.length
        else if (event.key === "Home") next = 0
        else if (event.key === "End") next = items.length - 1
        else return
        event.preventDefault()
        onChange(items[next].value)
        document.getElementById(`${id}-tab-${next}`)?.focus()
      }}>{item.label}</button>)}
    </div>
    <div id={`${id}-panel`} role="tabpanel" aria-labelledby={`${id}-tab-${selected}`} tabIndex={0}>{children}</div>
  </div>
}
