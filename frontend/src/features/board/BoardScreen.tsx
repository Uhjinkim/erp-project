import type { Route } from "../../app/routing"
import { EmptyState } from "../../components/ui"
import { parsePostId } from "./boardModel"
import type { BoardKind } from "./boardModel"
import { BoardDetailScreen } from "./screens/BoardDetailScreen"
import { BoardListScreen } from "./screens/BoardListScreen"
import { PostWriteScreen } from "./screens/PostWriteScreen"

const listKinds: Record<string, BoardKind> = { "notice-list": "notice", "board-list": "general" }

export function BoardScreen({ route, enabled }: { route: Route; enabled: boolean }) {
  if (route.screenId === "board-write") return <PostWriteScreen enabled={enabled} />
  const kind = listKinds[route.screenId]
  if (!kind) return <EmptyState title="화면을 찾을 수 없습니다" />
  if (!new URLSearchParams(route.search ?? "").has("postId")) return <BoardListScreen key={kind} kind={kind} enabled={enabled} />
  const postId = parsePostId(route.search)
  return <BoardDetailScreen key={`${kind}-${postId ?? "invalid"}`} kind={kind} postId={postId} enabled={enabled} />
}
