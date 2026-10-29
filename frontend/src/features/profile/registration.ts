import { ContactRound, FileCheck2, History, Inbox, UserRound } from "lucide-react"
import type { ModuleRegistration } from "../../app/routing"

export const registration: ModuleRegistration = {
  "id": "profile",
  "label": "내 정보",
  "icon": UserRound,
  "entry": "my-profile",
  "screens": [
    {
      "id": "my-profile",
      "icon": ContactRound,
      "title": "내 인사정보"
    },
    {
      "id": "change-history",
      "icon": History,
      "title": "내 수정 요청 이력"
    },
    {
      "id": "change-queue",
      "icon": Inbox,
      "title": "개인정보 수정 요청 처리함"
    },
    {
      "id": "change-review",
      "icon": FileCheck2,
      "title": "개인정보 변경 승인·반려"
    }
  ]
}
