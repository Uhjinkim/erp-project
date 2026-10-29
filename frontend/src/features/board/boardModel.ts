import { BUSINESS_TIME_ZONE } from "../../utils/dateTime"
import { routeHref } from "../../app/routing"
import type { NoticeCategory, Post } from "../../types/board"

export const noticeCategoryLabels: Record<NoticeCategory, string> = {
  MANAGEMENT: "경영",
  HR: "인사",
  PAYROLL: "급여",
}

export type BoardKind = "notice" | "general"
export type SearchField = "title" | "writer"
export type CategoryFilter = NoticeCategory | "all"

const listScreenIds: Record<BoardKind, string> = { notice: "notice-list", general: "board-list" }

export const writeHref = routeHref({ moduleId: "board", screenId: "board-write" })

export function listHref(kind: BoardKind) {
  return routeHref({ moduleId: "board", screenId: listScreenIds[kind] })
}

export function postHref(kind: BoardKind, postId: number) {
  return routeHref({ moduleId: "board", screenId: listScreenIds[kind], search: `postId=${postId}` })
}

export function kindOf(post: Pick<Post, "post_type">): BoardKind {
  return post.post_type === "공지" ? "notice" : "general"
}

export function navigateTo(href: string) {
  window.location.hash = href.slice(1)
}

export function parsePostId(search?: string): number | null {
  const value = new URLSearchParams(search ?? "").get("postId")
  if (!value || !/^[1-9]\d*$/.test(value)) return null
  return Number(value)
}

export function writerLabel(item: { writer_name: string | null; writer_employee_no: number }) {
  return item.writer_name ?? String(item.writer_employee_no)
}

function matches(text: string, query: string) {
  const keyword = query.trim().toLowerCase()
  return !keyword || text.toLowerCase().includes(keyword)
}

// Per-board sequence: oldest post in the board is 1. Filtering never renumbers.
export function boardNumbers(posts: Post[], kind: BoardKind): Map<number, number> {
  const ids = posts.filter((post) => kindOf(post) === kind).map((post) => post.post_id).sort((a, b) => a - b)
  return new Map(ids.map((postId, index) => [postId, index + 1]))
}

export function filterGeneralPosts(posts: Post[], field: SearchField, query: string): Post[] {
  return posts.filter((post) =>
    kindOf(post) === "general" && matches(field === "title" ? post.title : writerLabel(post), query))
}

export function filterNoticePosts(posts: Post[], category: CategoryFilter, query: string): Post[] {
  return posts.filter((post) =>
    kindOf(post) === "notice"
    && (category === "all" || post.notice_category === category)
    && matches(post.title, query))
}

export function formatDateTime(value: string) {
  return new Date(value).toLocaleString("ko-KR", { timeZone: BUSINESS_TIME_ZONE })
}
