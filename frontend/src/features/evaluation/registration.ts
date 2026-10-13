import type { ModuleRegistration } from "../../app/routing"

export const registration: ModuleRegistration = {
  "id": "evaluation",
  "label": "인사평가",
  "icon": "◫",
  "entry": "evaluation-team",
  "screens": [
    {
      "id": "evaluation-team",
      "title": "팀 평가 대상 목록"
    },
    {
      "id": "evaluation-form",
      "title": "평가 작성·수정"
    },
    {
      "id": "evaluation-hr",
      "title": "평가 관리·확정"
    },
    {
      "id": "evaluation-mine",
      "title": "내 평가 결과"
    }
  ]
}
