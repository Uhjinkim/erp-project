import { routeHref } from "../../app/routing"
import type { NoticeCategory, Post } from "../../types/board"

export const noticeCategoryLabels: Record<NoticeCategory, string> = {
  MANAGEMENT: "경영",
  HR: "인사",
  PAYROLL: "급여",
}

export type SearchField = "title" | "writer"

export const listHref = routeHref({ moduleId: "board", screenId: "board-list" })
export const writeHref = routeHref({ moduleId: "board", screenId: "board-write" })

export function postHref(postId: number) {
  return routeHref({ moduleId: "board", screenId: "board-list", search: `postId=${postId}` })
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

export function filterPosts(posts: Post[], field: SearchField, query: string): Post[] {
  const keyword = query.trim().toLowerCase()
  if (!keyword) return posts
  return posts.filter((post) =>
    (field === "title" ? post.title : writerLabel(post)).toLowerCase().includes(keyword))
}

export function formatDateTime(value: string) {
  return new Date(value).toLocaleString("ko-KR")
}
