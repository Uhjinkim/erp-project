import { useEffect, useState } from "react"

// Print only the chosen payslip; the browser print dialog also offers "PDF로 저장".
// styles/print.css shows only `.payslip--printing` while body has `payroll-printing`.
export function usePayslipPrint() {
  const [printingId, setPrintingId] = useState<number | null>(null)

  useEffect(() => {
    if (printingId === null) return
    const finish = () => setPrintingId(null)
    document.body.classList.add("payroll-printing")
    window.addEventListener("afterprint", finish, { once: true })
    const timer = window.setTimeout(() => window.print(), 0)
    return () => {
      window.clearTimeout(timer)
      window.removeEventListener("afterprint", finish)
      document.body.classList.remove("payroll-printing")
    }
  }, [printingId])

  return { printingId, print: setPrintingId }
}
