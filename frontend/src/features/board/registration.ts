import type { ModuleRegistration } from "../../app/routing"

// Post detail is a state of board-list (?postId=) so it stays out of the menu.
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
      "id": "board-write",
      "title": "게시글 작성"
    }
  ]
}
