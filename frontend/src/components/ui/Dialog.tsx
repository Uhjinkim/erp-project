import { useEffect, useId, useRef } from "react"
import type { ReactNode } from "react"
import { Button, IconButton } from "./Button"
import styles from "./ui.module.css"

export function Modal({ open, title, onClose, children, actions, drawer = false, busy = false }: {
  open: boolean; title: string; onClose: () => void; children: ReactNode; actions?: ReactNode; drawer?: boolean; busy?: boolean
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const id = useId()
  useEffect(() => {
    const dialog = ref.current
    if (!dialog || !open) return
    const previousFocus = document.activeElement
    dialog.showModal()
    return () => {
      dialog.close()
      if (previousFocus instanceof HTMLElement && previousFocus.isConnected) previousFocus.focus()
    }
  }, [open])
  return <dialog ref={ref} className={`${styles.dialog} ${drawer ? styles.drawer : ""}`} aria-labelledby={id} aria-busy={busy || undefined} onCancel={(event) => { event.preventDefault(); if (!busy) onClose() }}>
    <div className={styles.dialogHead}><h2 id={id}>{title}</h2><IconButton label="닫기" variant="ghost" onClick={onClose} disabled={busy}>×</IconButton></div>
    {children}{actions && <div className={styles.actions}>{actions}</div>}
  </dialog>
}

export function Drawer(props: Omit<Parameters<typeof Modal>[0], "drawer">) {
  return <Modal {...props} drawer />
}

export function ConfirmDialog({ onConfirm, confirmLabel = "확인", danger = false, ...props }: Omit<Parameters<typeof Modal>[0], "actions"> & { onConfirm: () => void; confirmLabel?: string; danger?: boolean }) {
  return <Modal {...props} actions={<><Button variant="secondary" onClick={props.onClose} disabled={props.busy}>취소</Button><Button variant={danger ? "danger" : "primary"} pending={props.busy} onClick={onConfirm}>{confirmLabel}</Button></>} />
}
