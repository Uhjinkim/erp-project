import type { ModuleRegistration } from "../../app/routing"

export const registration: ModuleRegistration = {
  "id": "vacation",
  "label": "휴가",
  "icon": "◷",
  "entry": "leave-apply",
  "screens": [
    {
      "id": "leave-apply",
      "title": "휴가 신청"
    },
    {
      "id": "leave-mine",
      "title": "내 휴가 신청 내역"
    },
    {
      "id": "leave-detail",
      "title": "휴가 상세·처리 이력"
    },
    {
      "id": "leave-queue",
      "title": "휴가 승인 대상"
    },
    {
      "id": "leave-approve",
      "title": "휴가 승인·반려"
    },
    {
      "id": "leave-recall",
      "title": "승인 휴가 회수"
    },
    {
      "id": "leave-resubmit",
      "title": "회수 신청 수정·재신청"
    }
  ]
}
