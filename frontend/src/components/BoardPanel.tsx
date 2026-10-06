import { FormEvent, useCallback, useEffect, useMemo, useState } from "react"

import {
  createComment,
  createPost,
  deleteComment,
  deletePost,
  getEligibleNoticeCategories,
  getPost,
  listComments,
  listPosts,
  updateComment,
  updatePost,
} from "../api/board"
import type { CurrentUser } from "../types/auth"
import type { Comment, NoticeCategory, Post, PostType } from "../types/board"

type BoardPanelProps = {
  enabled: boolean
  currentUser: CurrentUser
}

type SearchField = "title" | "writer"

const noticeCategoryLabels: Record<NoticeCategory, string> = {
  MANAGEMENT: "경영",
  HR: "인사",
  PAYROLL: "급여",
  DEPARTMENT: "부서",
}

const initialPostForm = {
  postType: "일반" as PostType,
  noticeCategory: "HR" as NoticeCategory,
  title: "",
  content: "",
}

export function BoardPanel({ enabled, currentUser }: BoardPanelProps) {
  const [posts, setPosts] = useState<Post[]>([])
  const [searchField, setSearchField] = useState<SearchField>("title")
  const [searchQuery, setSearchQuery] = useState("")
  const [postForm, setPostForm] = useState(initialPostForm)
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(false)

  const [selectedPost, setSelectedPost] = useState<Post | null>(null)
  const [comments, setComments] = useState<Comment[]>([])
  const [isEditingPost, setIsEditingPost] = useState(false)
  const [editTitle, setEditTitle] = useState("")
  const [editContent, setEditContent] = useState("")
  const [commentDraft, setCommentDraft] = useState("")
  const [replyTarget, setReplyTarget] = useState<number | null>(null)
  const [replyDraft, setReplyDraft] = useState("")
  const [editingCommentId, setEditingCommentId] = useState<number | null>(null)
  const [editingCommentContent, setEditingCommentContent] = useState("")
  const [eligibleCategories, setEligibleCategories] = useState<NoticeCategory[]>([])

  const canModify = useCallback(
    (post: Post) => currentUser.is_superuser || post.writer_employee_no === currentUser.employee?.emp_no,
    [currentUser],
  )

  const refreshList = useCallback(async () => {
    if (!enabled) return
    setLoading(true)
    try {
      setPosts(await listPosts())
      setMessage("")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "게시글을 불러오지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }, [enabled])

  useEffect(() => {
    if (!enabled) return
    const timer = window.setTimeout(() => void refreshList(), 0)
    return () => window.clearTimeout(timer)
  }, [enabled, refreshList])

  useEffect(() => {
    if (!enabled) return
    let active = true
    void getEligibleNoticeCategories().then((categories) => {
      if (active) setEligibleCategories(categories)
    }).catch(() => {
      if (active) setEligibleCategories([])
    })
    return () => { active = false }
  }, [enabled])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (eligibleCategories.length === 0) {
        setPostForm((current) => (current.postType === "일반" ? current : { ...current, postType: "일반" }))
        return
      }
      if (!eligibleCategories.includes(postForm.noticeCategory)) {
        setPostForm((current) => ({ ...current, noticeCategory: eligibleCategories[0] }))
      }
    }, 0)
    return () => window.clearTimeout(timer)
  }, [eligibleCategories, postForm.noticeCategory])

  const filteredPosts = useMemo(() => {
    const keyword = searchQuery.trim().toLowerCase()
    if (!keyword) return posts
    return posts.filter((post) => {
      if (searchField === "title") return post.title.toLowerCase().includes(keyword)
      const writer = (post.writer_name ?? String(post.writer_employee_no)).toLowerCase()
      return writer.includes(keyword)
    })
  }, [posts, searchField, searchQuery])

  async function submitNewPost(event: FormEvent) {
    event.preventDefault()
    if (!enabled) return
    setLoading(true)
    try {
      await createPost({
        post_type: postForm.postType,
        title: postForm.title,
        content: postForm.content,
        notice_category: postForm.postType === "공지" ? postForm.noticeCategory : undefined,
      })
      setPostForm(initialPostForm)
      await refreshList()
      setMessage("게시글을 작성했습니다.")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "게시글을 작성하지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }

  const openPost = useCallback(async (postId: number) => {
    setLoading(true)
    try {
      const [post, commentList] = await Promise.all([getPost(postId), listComments(postId)])
      setSelectedPost(post)
      setComments(commentList)
      setIsEditingPost(false)
      setReplyTarget(null)
      setCommentDraft("")
      setMessage("")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "게시글을 불러오지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }, [])

  function backToList() {
    setSelectedPost(null)
    setComments([])
    setIsEditingPost(false)
    void refreshList()
  }

  function startEditPost() {
    if (!selectedPost) return
    setEditTitle(selectedPost.title)
    setEditContent(selectedPost.content)
    setIsEditingPost(true)
  }

  async function submitEditPost(event: FormEvent) {
    event.preventDefault()
    if (!selectedPost) return
    setLoading(true)
    try {
      const updated = await updatePost(selectedPost.post_id, { title: editTitle, content: editContent })
      setSelectedPost(updated)
      setIsEditingPost(false)
      setMessage("게시글을 수정했습니다.")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "게시글을 수정하지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }

  async function removePost() {
    if (!selectedPost) return
    if (!window.confirm("이 게시글을 삭제할까요?")) return
    setLoading(true)
    try {
      await deletePost(selectedPost.post_id)
      backToList()
      setMessage("게시글을 삭제했습니다.")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "게시글을 삭제하지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }

  async function refreshComments() {
    if (!selectedPost) return
    setComments(await listComments(selectedPost.post_id))
  }

  async function submitComment(event: FormEvent) {
    event.preventDefault()
    if (!selectedPost || !commentDraft.trim()) return
    setLoading(true)
    try {
      await createComment(selectedPost.post_id, { content: commentDraft })
      setCommentDraft("")
      await refreshComments()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "댓글을 작성하지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }

  async function submitReply(event: FormEvent, parentCommentId: number) {
    event.preventDefault()
    if (!selectedPost || !replyDraft.trim()) return
    setLoading(true)
    try {
      await createComment(selectedPost.post_id, {
        content: replyDraft,
        parent_comment_id: parentCommentId,
      })
      setReplyDraft("")
      setReplyTarget(null)
      await refreshComments()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "답글을 작성하지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }

  function startEditComment(comment: Comment) {
    setEditingCommentId(comment.comment_id)
    setEditingCommentContent(comment.content)
  }

  function cancelEditComment() {
    setEditingCommentId(null)
    setEditingCommentContent("")
  }

  async function submitEditComment(event: FormEvent, commentId: number) {
    event.preventDefault()
    if (!editingCommentContent.trim()) return
    setLoading(true)
    try {
      await updateComment(commentId, editingCommentContent)
      cancelEditComment()
      await refreshComments()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "댓글을 수정하지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }

  async function removeComment(commentId: number) {
    if (!window.confirm("이 댓글을 삭제할까요?")) return
    setLoading(true)
    try {
      await deleteComment(commentId)
      await refreshComments()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "댓글을 삭제하지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }

  function canModifyComment(comment: Comment): boolean {
    return currentUser.is_superuser || comment.writer_employee_no === currentUser.employee?.emp_no
  }

  const topLevelComments = comments.filter((comment) => comment.parent_comment_id === null)
  const repliesByParent = (parentId: number) =>
    comments.filter((comment) => comment.parent_comment_id === parentId)

  if (selectedPost) {
    const post = selectedPost
    return (
      <section className="workspace">
        <section className="list-panel">
          <div className="section-heading">
            <div><p className="step">게시글</p><h2>{isEditingPost ? "게시글 수정" : post.title}</h2></div>
            <button className="text-button" type="button" onClick={backToList}>목록으로</button>
          </div>
          {message && <div className="notice" role="status">{message}</div>}

          {isEditingPost ? (
            <form className="request-card" onSubmit={submitEditPost}>
              <label>
                제목
                <input
                  required
                  maxLength={100}
                  value={editTitle}
                  onChange={(event) => setEditTitle(event.target.value)}
                />
              </label>
              <label>
                내용
                <textarea
                  required
                  rows={6}
                  value={editContent}
                  onChange={(event) => setEditContent(event.target.value)}
                />
              </label>
              <div className="actions">
                <button className="primary" disabled={loading} type="submit">저장</button>
                <button type="button" onClick={() => setIsEditingPost(false)}>취소</button>
              </div>
            </form>
          ) : (
            <article className="request-item">
              <div className="item-top">
                <div>
                  <span className="badge">{post.post_type}</span>
                  {post.notice_category && <strong> {noticeCategoryLabels[post.notice_category]}</strong>}
                </div>
                <span className="request-id">#{post.post_id}</span>
              </div>
              <p className="reason">{post.content}</p>
              <dl>
                <div><dt>작성자</dt><dd>{post.writer_name ?? post.writer_employee_no}</dd></div>
                <div><dt>작성일</dt><dd>{new Date(post.created_at).toLocaleString("ko-KR")}</dd></div>
                {post.updated_at && (
                  <div><dt>수정일</dt><dd>{new Date(post.updated_at).toLocaleString("ko-KR")}</dd></div>
                )}
              </dl>
              {canModify(post) && (
                <div className="actions">
                  <button type="button" onClick={startEditPost}>수정</button>
                  <button type="button" onClick={() => void removePost()}>삭제</button>
                </div>
              )}
            </article>
          )}

          <div className="section-heading"><div><p className="step">댓글</p><h2>댓글 {comments.length}</h2></div></div>
          <form className="department-form" onSubmit={submitComment}>
            <input
              placeholder="댓글을 입력하세요"
              value={commentDraft}
              onChange={(event) => setCommentDraft(event.target.value)}
            />
            <button className="primary" disabled={loading} type="submit">댓글 작성</button>
          </form>
          <div className="request-list">
            {topLevelComments.length === 0 && <div className="empty">아직 댓글이 없습니다.</div>}
            {topLevelComments.map((comment) => (
              <article className="employee-item" key={comment.comment_id}>
                <div><strong>{comment.writer_name ?? comment.writer_employee_no}</strong><span>{new Date(comment.created_at).toLocaleString("ko-KR")}</span></div>
                {editingCommentId === comment.comment_id ? (
                  <form className="department-form" onSubmit={(event) => void submitEditComment(event, comment.comment_id)}>
                    <input
                      value={editingCommentContent}
                      onChange={(event) => setEditingCommentContent(event.target.value)}
                    />
                    <div className="actions">
                      <button className="primary" disabled={loading} type="submit">저장</button>
                      <button type="button" onClick={cancelEditComment}>취소</button>
                    </div>
                  </form>
                ) : (
                  <>
                    <p>{comment.content}</p>
                    <div className="actions">
                      <button type="button" onClick={() => setReplyTarget(comment.comment_id === replyTarget ? null : comment.comment_id)}>답글</button>
                      {canModifyComment(comment) && (
                        <>
                          <button type="button" onClick={() => startEditComment(comment)}>수정</button>
                          <button type="button" onClick={() => void removeComment(comment.comment_id)}>삭제</button>
                        </>
                      )}
                    </div>
                  </>
                )}
                {replyTarget === comment.comment_id && (
                  <form className="department-form" onSubmit={(event) => void submitReply(event, comment.comment_id)}>
                    <input
                      placeholder="답글을 입력하세요"
                      value={replyDraft}
                      onChange={(event) => setReplyDraft(event.target.value)}
                    />
                    <button className="primary" disabled={loading} type="submit">답글 작성</button>
                  </form>
                )}
                {repliesByParent(comment.comment_id).map((reply) => (
                  <article className="employee-item board-reply" key={reply.comment_id}>
                    <div><strong>{reply.writer_name ?? reply.writer_employee_no}</strong><span>{new Date(reply.created_at).toLocaleString("ko-KR")}</span></div>
                    {editingCommentId === reply.comment_id ? (
                      <form className="department-form" onSubmit={(event) => void submitEditComment(event, reply.comment_id)}>
                        <input
                          value={editingCommentContent}
                          onChange={(event) => setEditingCommentContent(event.target.value)}
                        />
                        <div className="actions">
                          <button className="primary" disabled={loading} type="submit">저장</button>
                          <button type="button" onClick={cancelEditComment}>취소</button>
                        </div>
                      </form>
                    ) : (
                      <>
                        <p>{reply.content}</p>
                        {canModifyComment(reply) && (
                          <div className="actions">
                            <button type="button" onClick={() => startEditComment(reply)}>수정</button>
                            <button type="button" onClick={() => void removeComment(reply.comment_id)}>삭제</button>
                          </div>
                        )}
                      </>
                    )}
                  </article>
                ))}
              </article>
            ))}
          </div>
        </section>
      </section>
    )
  }

  return (
    <section className="workspace" aria-disabled={!enabled}>
      <form className="request-card" onSubmit={submitNewPost}>
        <div className="section-heading"><div><p className="step">01</p><h2>새 게시글 작성</h2></div></div>
        {eligibleCategories.length > 0 && (
          <label>
            게시글 유형
            <select
              disabled={!enabled}
              value={postForm.postType}
              onChange={(event) => setPostForm({ ...postForm, postType: event.target.value as PostType })}
            >
              <option value="일반">일반</option>
              <option value="공지">공지</option>
            </select>
          </label>
        )}
        {eligibleCategories.length > 0 && postForm.postType === "공지" && (
          <label>
            공지 분류
            <select
              disabled={!enabled}
              value={postForm.noticeCategory}
              onChange={(event) =>
                setPostForm({ ...postForm, noticeCategory: event.target.value as NoticeCategory })}
            >
              {eligibleCategories.map((code) => (
                <option key={code} value={code}>{noticeCategoryLabels[code]}</option>
              ))}
            </select>
          </label>
        )}
        <label>
          제목
          <input
            disabled={!enabled}
            required
            maxLength={100}
            value={postForm.title}
            onChange={(event) => setPostForm({ ...postForm, title: event.target.value })}
          />
        </label>
        <label>
          내용
          <textarea
            disabled={!enabled}
            required
            rows={5}
            value={postForm.content}
            onChange={(event) => setPostForm({ ...postForm, content: event.target.value })}
          />
        </label>
        <button className="primary" disabled={loading || !enabled} type="submit">
          {enabled ? "작성하기" : "오프라인 / 미연결"}
        </button>
      </form>
      <section className="list-panel">
        <div className="section-heading">
          <div><p className="step">02</p><h2>게시글 목록</h2></div>
          <button className="refresh" type="button" onClick={() => void refreshList()} disabled={loading || !enabled}>
            새로고침
          </button>
        </div>
        <div className="two-columns">
          <label>
            검색 대상
            <select value={searchField} onChange={(event) => setSearchField(event.target.value as SearchField)}>
              <option value="title">제목</option>
              <option value="writer">작성자</option>
            </select>
          </label>
          <label>
            검색어
            <input
              placeholder={searchField === "title" ? "제목으로 검색" : "작성자로 검색"}
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
            />
          </label>
        </div>
        {message && <div className="notice" role="status">{message}</div>}
        <div className="request-list">
          {filteredPosts.length === 0 && (
            <div className="empty">{enabled ? "표시할 게시글이 없습니다." : "서버 연결 후 게시글을 불러옵니다."}</div>
          )}
          {filteredPosts.map((post) => (
            <article
              className="request-item board-list-item"
              key={post.post_id}
              onClick={() => void openPost(post.post_id)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault()
                  void openPost(post.post_id)
                }
              }}
              role="button"
              tabIndex={0}
            >
              <div className="item-top">
                <div>
                  <span className="badge">{post.post_type}</span>
                  {post.notice_category && <strong> {noticeCategoryLabels[post.notice_category]}</strong>}
                  <strong> {post.title}</strong>
                </div>
                <span className="request-id">#{post.post_id}</span>
              </div>
              <small>{post.writer_name ?? post.writer_employee_no} · {new Date(post.created_at).toLocaleString("ko-KR")}</small>
            </article>
          ))}
        </div>
      </section>
    </section>
  )
}
