import type { ModuleRegistration } from "../../app/routing"

export const registration: ModuleRegistration = {
  "id": "workforce",
  "label": "사원·조직",
  "icon": "♧",
  "entry": "employee-list",
  "requiredRole": "HR_MANAGER",
  "screens": [
    {
      "id": "employee-list",
      "title": "사원 목록"
    },
    {
      "id": "employee-detail",
      "title": "사원 상세·인사 이력"
    },
    {
      "id": "employee-create",
      "title": "신규 사원 등록"
    },
    {
      "id": "retire",
      "title": "퇴사 처리 확인"
    },
    {
      "id": "rehire",
      "title": "재입사 처리"
    },
    {
      "id": "role-grant",
      "title": "업무 역할 부여·회수"
    },
    {
      "id": "org",
      "title": "부서·직급 관리"
    }
  ]
}
