import type { ModuleRegistration } from "../../app/routing"

export const registration: ModuleRegistration = {
  "id": "payroll",
  "label": "급여",
  "icon": "▥",
  "entry": "payroll-periods",
  "screens": [
    {
      "id": "payroll-periods",
      "title": "급여 정산 기간 목록"
    },
    {
      "id": "payroll-create",
      "title": "급여 정산 생성"
    },
    {
      "id": "payroll-item",
      "title": "사원별 정산 항목"
    },
    {
      "id": "payroll-confirm",
      "title": "급여 확정·정정"
    },
    {
      "id": "payslip",
      "title": "내 급여명세"
    }
  ]
}
