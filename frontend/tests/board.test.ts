import { describe, expect, test } from "bun:test"
import { modules } from "../src/app/modules"
import { findScreen, parseRoute } from "../src/app/routing"
import {
  boardNumbers, filterGeneralPosts, filterNoticePosts, kindOf, listHref, parsePostId, postHref, writeHref,
} from "../src/features/board/boardModel"
import type { Post } from "../src/types/board"

function post(overrides: Partial<Post>): Post {
  return {
    post_id: 1, writer_employee_no: 1001, writer_name: "김사원", post_type: "일반",
    notice_category: null, title: "제목", content: "내용", comment_count: 0,
    created_at: "2026-10-13T00:00:00Z", updated_at: null, can_edit: false, can_delete: false,
    ...overrides,
  }
}

const posts = [
  post({ post_id: 1, title: "급여 지급 안내", writer_name: "박급여", post_type: "공지", notice_category: "PAYROLL" }),
  post({ post_id: 2, title: "인사 발령 공지", writer_name: "최인사", post_type: "공지", notice_category: "HR" }),
  post({ post_id: 3, title: "점심 메뉴 추천", writer_name: null, writer_employee_no: 2002 }),
  post({ post_id: 4, title: "급여 관련 질문", writer_name: "김사원" }),
]

describe("board model", () => {
  test("board menu lists notice board, general board and write in order", () => {
    const board = modules.find((module) => module.id === "board")
    expect(board?.screens.map((screen) => screen.id)).toEqual(["notice-list", "board-list", "board-write"])
    expect(board?.entry).toBe("notice-list")
  })

  test("each board opens its posts on its own list screen", () => {
    expect(findScreen(parseRoute(listHref("notice")), modules)?.screen.id).toBe("notice-list")
    expect(findScreen(parseRoute(listHref("general")), modules)?.screen.id).toBe("board-list")
    expect(findScreen(parseRoute(writeHref), modules)?.screen.id).toBe("board-write")
    const route = parseRoute(postHref("notice", 12))
    expect(findScreen(route, modules)?.screen.id).toBe("notice-list")
    expect(parsePostId(route?.search)).toBe(12)
    expect(kindOf(posts[0])).toBe("notice")
    expect(kindOf(posts[2])).toBe("general")
  })

  test("only positive integer post ids are accepted from the URL", () => {
    expect(parsePostId(undefined)).toBeNull()
    for (const value of ["", "0", "-3", "1.5", "abc", "12abc"]) expect(parsePostId(`postId=${value}`)).toBeNull()
    expect(parsePostId("postId=7&x=1")).toBe(7)
  })

  test("notice board shows only notices, filtered by category and title", () => {
    expect(filterNoticePosts(posts, "all", "").map((item) => item.post_id)).toEqual([1, 2])
    expect(filterNoticePosts(posts, "HR", "").map((item) => item.post_id)).toEqual([2])
    expect(filterNoticePosts(posts, "all", " 급여 ").map((item) => item.post_id)).toEqual([1])
    expect(filterNoticePosts(posts, "MANAGEMENT", "")).toEqual([])
  })

  test("each board numbers its own posts from 1, oldest first, regardless of API order", () => {
    const newestFirst = [...posts].reverse()
    expect(Object.fromEntries(boardNumbers(newestFirst, "notice"))).toEqual({ 1: 1, 2: 2 })
    expect(Object.fromEntries(boardNumbers(newestFirst, "general"))).toEqual({ 3: 1, 4: 2 })
  })

  test("general board shows only general posts, searched by title or writer", () => {
    expect(filterGeneralPosts(posts, "title", "").map((item) => item.post_id)).toEqual([3, 4])
    expect(filterGeneralPosts(posts, "title", "급여").map((item) => item.post_id)).toEqual([4])
    expect(filterGeneralPosts(posts, "writer", "2002").map((item) => item.post_id)).toEqual([3])
  })
})
