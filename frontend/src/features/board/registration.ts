import type { ModuleRegistration } from "../../app/routing"

// Post detail is a state of each board list (?postId=) so it stays out of the menu.
export const registration: ModuleRegistration = {
  "id": "board",
  "label": "게시판",
  "icon": "▤",
  "entry": "notice-list",
  "screens": [
    {
      "id": "notice-list",
      "title": "공지게시판"
    },
    {
      "id": "board-list",
      "title": "일반게시판"
    },
    {
      "id": "board-write",
      "title": "게시글 작성"
    }
  ]
}
