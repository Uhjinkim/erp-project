import { Settings, UsersRound } from "lucide-react"
import type { ModuleRegistration } from "../../app/routing"

export const registration: ModuleRegistration = {
  "id": "system",
  "label": "시스템",
  "icon": Settings,
  "entry": "account-admin",
  "screens": [
    {
      "id": "account-admin",
      "icon": UsersRound,
      "title": "계정 관리"
    }
  ]
}
