import { CalendarCheck, CalendarClock, CalendarDays, CalendarPlus, CalendarSearch, CalendarSync, CalendarX, Inbox } from "lucide-react"
import type { ModuleRegistration } from "../../app/routing"

export const registration: ModuleRegistration = {
  "id": "vacation",
  "label": "휴가",
  "icon": CalendarDays,
  "entry": "leave-apply",
  "screens": [
    {
      "id": "leave-apply",
      "icon": CalendarPlus,
      "title": "휴가 신청"
    },
    {
      "id": "leave-mine",
      "icon": CalendarClock,
      "title": "내 휴가 신청 내역"
    },
    {
      "id": "leave-detail",
      "icon": CalendarSearch,
      "title": "휴가 상세·처리 이력"
    },
    {
      "id": "leave-queue",
      "icon": Inbox,
      "title": "휴가 승인 대상"
    },
    {
      "id": "leave-approve",
      "icon": CalendarCheck,
      "title": "휴가 승인·반려"
    },
    {
      "id": "leave-recall",
      "icon": CalendarX,
      "title": "승인 휴가 회수"
    },
    {
      "id": "leave-resubmit",
      "icon": CalendarSync,
      "title": "회수 신청 수정·재신청"
    }
  ]
}
