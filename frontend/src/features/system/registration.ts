import type { ModuleRegistration } from "../../app/routing"

export const registration: ModuleRegistration = {
  "id": "system",
  "label": "시스템",
  "icon": "⚙",
  "entry": "system-health",
  "screens": [
    {
      "id": "account-admin",
      "title": "계정 관리"
    },
    {
      "id": "system-health",
      "title": "연결 상태·시스템 정보"
    }
  ]
}
