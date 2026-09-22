export type PayrollComponentCategory = "지급" | "공제"
export type PayrollStatus = "작성중" | "확정"

export type PayrollComponent = {
  code: string
  name: string
  category: PayrollComponentCategory
  is_active: boolean
}

export type PayrollItem = {
  item_id: number | null
  component_code: string
  category: PayrollComponentCategory
  amount: number
}

export type PayrollStatement = {
  statement_id: number
  employee_no: number
  year: number
  month: number
  payment_date: string
  status: PayrollStatus
  items: PayrollItem[]
  total_earnings: number
  total_deductions: number
  net_pay: number
  created_by: number
  confirmed_by: number | null
  confirmed_at: string | null
}

export type PayrollHistoryEntry = {
  history_id: number
  statement_id: number
  action: string
  actor_employee_no: number
  reason: string | null
  change_summary: string | null
  changed_at: string
}
