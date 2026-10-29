import { BadgeCheck, Calculator, CalendarDays, ListOrdered, ReceiptText, WalletCards } from "lucide-react"
import type { ModuleRegistration } from "../../app/routing"

export const registration: ModuleRegistration = {
  "id": "payroll",
  "label": "급여",
  "icon": WalletCards,
  "entry": "payslip",
  "screens": [
    {
      "id": "payroll-periods",
      "icon": CalendarDays,
      "title": "급여 정산 기간 목록"
    },
    {
      "id": "payroll-create",
      "icon": Calculator,
      "title": "급여 정산 생성"
    },
    {
      "id": "payroll-item",
      "icon": ListOrdered,
      "title": "사원별 정산 항목"
    },
    {
      "id": "payroll-confirm",
      "icon": BadgeCheck,
      "title": "급여 확정·정정"
    },
    {
      "id": "payslip",
      "icon": ReceiptText,
      "title": "내 급여명세"
    }
  ]
}
