import { ContactRound, Network, ShieldCheck, UserRoundCheck, UserRoundMinus, UserRoundPlus, UsersRound } from "lucide-react"
import type { ModuleRegistration } from "../../app/routing"

export const registration: ModuleRegistration = {
  "id": "workforce",
  "label": "사원·조직",
  "icon": Network,
  "entry": "employee-list",
  "requiredRole": "HR_MANAGER",
  "allowSuperuser": true,
  "screens": [
    {
      "id": "employee-list",
      "icon": UsersRound,
      "title": "사원 목록"
    },
    {
      "id": "employee-detail",
      "icon": ContactRound,
      "title": "사원 상세·인사 이력",
      "menu": false
    },
    {
      "id": "employee-create",
      "icon": UserRoundPlus,
      "title": "신규 사원 등록"
    },
    {
      "id": "retire",
      "icon": UserRoundMinus,
      "title": "퇴사 처리 확인"
    },
    {
      "id": "rehire",
      "icon": UserRoundCheck,
      "title": "재입사 처리"
    },
    {
      "id": "role-grant",
      "icon": ShieldCheck,
      "title": "업무 역할 부여·회수"
    },
    {
      "id": "org",
      "icon": Network,
      "title": "부서·직급 관리"
    }
  ]
}
