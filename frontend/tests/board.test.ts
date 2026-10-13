import { describe, expect, test } from "bun:test"
import { modules } from "../src/app/modules"
import { findScreen, parseRoute } from "../src/app/routing"
import { filterPosts, listHref, parsePostId, postHref, writeHref } from "../src/features/board/boardModel"
import type { Post } from "../src/types/board"

function post(overrides: Partial<Post>): Post {
  return {
    post_id: 1, writer_employee_no: 1001, writer_name: "김사원", post_type: "일반",
    notice_category: null, title: "제목", content: "내용", comment_count: 0,
    created_at: "2026-10-13T00:00:00Z", updated_at: null, can_edit: false, can_delete: false,
    ...overrides,
  }
}

describe("board model", () => {
  test("board menu only lists the list and write screens", () => {
    const board = modules.find((module) => module.id === "board")
    expect(board?.screens.map((screen) => screen.id)).toEqual(["board-list", "board-write"])
  })

  test("a post opens as the list screen with its id in the URL", () => {
    expect(findScreen(parseRoute(listHref), modules)?.screen.id).toBe("board-list")
    expect(findScreen(parseRoute(writeHref), modules)?.screen.id).toBe("board-write")
    const route = parseRoute(postHref(12))
    expect(findScreen(route, modules)?.screen.id).toBe("board-list")
    expect(parsePostId(route?.search)).toBe(12)
  })

  test("only positive integer post ids are accepted from the URL", () => {
    expect(parsePostId(undefined)).toBeNull()
    for (const value of ["", "0", "-3", "1.5", "abc", "12abc"]) expect(parsePostId(`postId=${value}`)).toBeNull()
    expect(parsePostId("postId=7&x=1")).toBe(7)
  })

  test("search filters by title or writer and falls back to the employee number", () => {
    const posts = [
      post({ post_id: 1, title: "급여 지급 안내", writer_name: "박급여" }),
      post({ post_id: 2, title: "점심 메뉴", writer_name: null, writer_employee_no: 2002 }),
    ]
    expect(filterPosts(posts, "title", "  급여 ").map((item) => item.post_id)).toEqual([1])
    expect(filterPosts(posts, "writer", "2002").map((item) => item.post_id)).toEqual([2])
    expect(filterPosts(posts, "writer", "")).toBe(posts)
  })
})
