import type { ModuleRegistration } from "../../app/routing"

export const registration: ModuleRegistration = {
  "id": "board",
  "label": "게시판",
  "icon": "▤",
  "entry": "board-list",
  "screens": [
    {
      "id": "board-list",
      "title": "게시판·공지 목록"
    },
    {
      "id": "board-detail",
      "title": "게시글 상세"
    },
    {
      "id": "board-write",
      "title": "일반글 작성"
    },
    {
      "id": "notice-write",
      "title": "권한별 공지 작성"
    }
  ]
}
