import type { ModuleRegistration } from "../../app/routing"

export const registration: ModuleRegistration = {
  "id": "profile",
  "label": "내 정보",
  "icon": "♙",
  "entry": "my-profile",
  "screens": [
    {
      "id": "my-profile",
      "title": "내 인사정보"
    },
    {
      "id": "change-history",
      "title": "내 수정 요청 이력"
    },
    {
      "id": "change-queue",
      "title": "개인정보 수정 요청 처리함"
    },
    {
      "id": "change-review",
      "title": "개인정보 변경 승인·반려"
    }
  ]
}
