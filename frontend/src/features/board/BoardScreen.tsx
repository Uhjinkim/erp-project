import type { Route } from "../../app/routing"
import { EmptyState } from "../../components/ui"
import { parsePostId } from "./boardModel"
import { BoardDetailScreen } from "./screens/BoardDetailScreen"
import { BoardListScreen } from "./screens/BoardListScreen"
import { PostWriteScreen } from "./screens/PostWriteScreen"

export function BoardScreen({ route, enabled }: { route: Route; enabled: boolean }) {
  if (route.screenId === "board-write") return <PostWriteScreen enabled={enabled} />
  if (route.screenId !== "board-list") return <EmptyState title="화면을 찾을 수 없습니다" />
  const hasPostParam = new URLSearchParams(route.search ?? "").has("postId")
  if (!hasPostParam) return <BoardListScreen enabled={enabled} />
  const postId = parsePostId(route.search)
  return <BoardDetailScreen key={postId ?? "invalid"} postId={postId} enabled={enabled} />
}
