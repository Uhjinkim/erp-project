import { ChartNoAxesCombined, ClipboardCheck, ClipboardPenLine, UsersRound } from "lucide-react"
import type { ModuleRegistration } from "../../app/routing"

export const registration: ModuleRegistration = {
  "id": "evaluation",
  "label": "인사평가",
  "icon": ClipboardCheck,
  "entry": "evaluation-team",
  "screens": [
    {
      "id": "evaluation-team",
      "icon": UsersRound,
      "title": "팀 평가 대상 목록"
    },
    {
      "id": "evaluation-form",
      "icon": ClipboardPenLine,
      "title": "평가 작성·수정"
    },
    {
      "id": "evaluation-hr",
      "icon": ClipboardCheck,
      "title": "평가 관리·확정"
    },
    {
      "id": "evaluation-mine",
      "icon": ChartNoAxesCombined,
      "title": "내 평가 결과"
    }
  ]
}
