import { Megaphone, MessagesSquare, SquarePen } from "lucide-react"
import type { ModuleRegistration } from "../../app/routing"

// Post detail is a state of each board list (?postId=) so it stays out of the menu.
export const registration: ModuleRegistration = {
  "id": "board",
  "label": "게시판",
  "icon": MessagesSquare,
  "entry": "notice-list",
  "screens": [
    {
      "id": "notice-list",
      "icon": Megaphone,
      "title": "공지게시판"
    },
    {
      "id": "board-list",
      "icon": MessagesSquare,
      "title": "일반게시판"
    },
    {
      "id": "board-write",
      "icon": SquarePen,
      "title": "게시글 작성"
    }
  ]
}
