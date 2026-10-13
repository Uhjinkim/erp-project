import type { ButtonHTMLAttributes } from "react"
import styles from "./ui.module.css"

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger"
  size?: "regular" | "small"
  pending?: boolean
}

export function Button({ variant = "primary", size = "regular", pending = false, disabled, className = "", children, type = "button", ...props }: ButtonProps) {
  return <button {...props} type={type} disabled={disabled || pending} aria-busy={pending || undefined} className={`${styles.button} ${styles[variant] ?? ""} ${size === "small" ? styles.small : ""} ${className}`}>
    {pending && <span className={styles.spinner} aria-hidden="true" />}{children}
  </button>
}

export function IconButton({ label, children, ...props }: Omit<ButtonProps, "aria-label"> & { label: string }) {
  return <Button {...props} aria-label={label}>{children}</Button>
}
