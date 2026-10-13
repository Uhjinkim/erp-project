import type { ModuleRegistration } from "../../app/routing"

export const registration: ModuleRegistration = {
  "id": "home",
  "label": "홈",
  "icon": "⌂",
  "entry": "home",
  "screens": [
    {
      "id": "home",
      "title": "사원 홈"
    },
    {
      "id": "manager-home",
      "title": "부서장 업무 홈"
    }
  ]
}
