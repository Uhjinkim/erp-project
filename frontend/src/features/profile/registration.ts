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
      "id": "contact-edit",
      "title": "연락처·주소 직접 수정"
    },
    {
      "id": "change-request",
      "title": "민감 정보 변경 요청"
    },
    {
      "id": "change-history",
      "title": "내 변경 요청 이력"
    },
    {
      "id": "change-queue",
      "title": "개인정보 요청 처리함"
    },
    {
      "id": "change-review",
      "title": "개인정보 요청 승인·반려"
    }
  ]
}
