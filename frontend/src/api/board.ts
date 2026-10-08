import { requestJson } from "./client"
import type { Comment, NoticeCategory, Post, PostType } from "../types/board"

export async function listPosts() {
  return requestJson<Post[]>("/api/board/posts/")
}

export async function getPost(postId: number) {
  return requestJson<Post>(`/api/board/posts/${postId}/`)
}

export async function createPost(input: {
  post_type: PostType
  title: string
  content: string
  notice_category?: NoticeCategory
}) {
  return requestJson<Post>("/api/board/posts/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  })
}

export async function updatePost(postId: number, input: { title: string; content: string }) {
  return requestJson<Post>(`/api/board/posts/${postId}/`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  })
}

export async function deletePost(postId: number) {
  return requestJson<null>(`/api/board/posts/${postId}/`, { method: "DELETE" })
}

export async function listComments(postId: number) {
  return requestJson<Comment[]>(`/api/board/posts/${postId}/comments/`)
}

export async function createComment(
  postId: number,
  input: { content: string; parent_comment_id?: number },
) {
  return requestJson<Comment>(`/api/board/posts/${postId}/comments/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  })
}

export async function updateComment(commentId: number, content: string) {
  return requestJson<Comment>(`/api/board/comments/${commentId}/`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  })
}

export async function deleteComment(commentId: number) {
  return requestJson<null>(`/api/board/comments/${commentId}/`, { method: "DELETE" })
}
