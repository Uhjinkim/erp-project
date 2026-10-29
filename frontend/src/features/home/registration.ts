import { House, LayoutDashboard } from "lucide-react"
import type { ModuleRegistration } from "../../app/routing"

export const registration: ModuleRegistration = {
  "id": "home",
  "label": "홈",
  "icon": House,
  "entry": "home",
  "screens": [
    {
      "id": "home",
      "icon": House,
      "title": "사원 홈"
    },
    {
      "id": "manager-home",
      "icon": LayoutDashboard,
      "title": "부서장 업무 홈"
    }
  ]
}
