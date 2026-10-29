import { useId } from "react"
import type { ComponentProps, ReactNode } from "react"
import styles from "./ui.module.css"

type FieldMeta = { label: string; hint?: string; error?: string }

export function FormField({ label, hint, error, id, required, children }: FieldMeta & { id: string; required?: boolean; children: ReactNode }) {
  return <div className={styles.field}>
    <label htmlFor={id}>{label}{required && " *"}</label>
    {children}
    {hint && <span id={`${id}-hint`} className={styles.hint}>{hint}</span>}
    {error && <span id={`${id}-error`} className={styles.error} role="alert">{error}</span>}
  </div>
}

function describedBy(id: string, hint?: string, error?: string, existing?: string) {
  return [existing, hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(" ") || undefined
}

export function TextInput({ label, hint, error, id: suppliedId, className = "", ref, ...props }: FieldMeta & ComponentProps<"input">) {
  const generatedId = useId()
  const id = suppliedId ?? generatedId
  return <FormField {...{ label, hint, error, id, required: props.required }}>
    <input {...props} ref={ref} id={id} className={`${styles.input} ${className}`} aria-invalid={error ? true : props["aria-invalid"]} aria-describedby={describedBy(id, hint, error, props["aria-describedby"])} />
  </FormField>
}

export function Textarea({ label, hint, error, id: suppliedId, className = "", ref, ...props }: FieldMeta & ComponentProps<"textarea">) {
  const generatedId = useId()
  const id = suppliedId ?? generatedId
  return <FormField {...{ label, hint, error, id, required: props.required }}>
    <textarea {...props} ref={ref} id={id} className={`${styles.input} ${styles.textarea} ${className}`} aria-invalid={error ? true : props["aria-invalid"]} aria-describedby={describedBy(id, hint, error, props["aria-describedby"])} />
  </FormField>
}

export function Select({ label, hint, error, id: suppliedId, className = "", ref, children, ...props }: FieldMeta & ComponentProps<"select">) {
  const generatedId = useId()
  const id = suppliedId ?? generatedId
  return <FormField {...{ label, hint, error, id, required: props.required }}>
    <select {...props} ref={ref} id={id} className={`${styles.input} ${className}`} aria-invalid={error ? true : props["aria-invalid"]} aria-describedby={describedBy(id, hint, error, props["aria-describedby"])}>{children}</select>
  </FormField>
}

export function Checkbox({ label, ...props }: { label: string } & Omit<ComponentProps<"input">, "type">) {
  return <label className={styles.checkbox}><input {...props} type="checkbox" />{label}</label>
}
