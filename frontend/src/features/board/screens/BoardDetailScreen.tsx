import { useCallback, useEffect, useRef, useState } from "react"
import type { FormEvent } from "react"

import { ApiError } from "../../../api/client"
import { deletePost, getPost, listComments, updatePost } from "../../../api/board"
import { Alert, Badge, Button, Card, ConfirmDialog, DetailList, EmptyState, ErrorState, Spinner, Textarea, TextInput } from "../../../components/ui"
import type { Comment, Post } from "../../../types/board"
import styles from "../board.module.css"
import { formatDateTime, listHref, navigateTo, noticeCategoryLabels, writerLabel } from "../boardModel"
import type { BoardKind } from "../boardModel"
import { CommentThread } from "../components/CommentThread"

type LoadState = "loading" | "ready" | "not-found" | "error"

export function BoardDetailScreen({ kind, postId, enabled }: { kind: BoardKind; postId: number | null; enabled: boolean }) {
  const [post, setPost] = useState<Post | null>(null)
  const [comments, setComments] = useState<Comment[]>([])
  const [state, setState] = useState<LoadState>("loading")
  const [loadError, setLoadError] = useState("")
  const [confirming, setConfirming] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState("")
  const [editing, setEditing] = useState(false)
  const [editTitle, setEditTitle] = useState("")
  const [editContent, setEditContent] = useState("")
  const [editErrors, setEditErrors] = useState<Record<string, string[]>>({})
  const [editMessage, setEditMessage] = useState("")
  const [saving, setSaving] = useState(false)
  const generation = useRef(0)
  const savingRef = useRef(false)

  const load = useCallback(async (options: { quiet?: boolean } = {}) => {
    if (!enabled || postId === null) return
    const run = ++generation.current
    if (!options.quiet) setState("loading")
    try {
      const [postData, commentData] = await Promise.all([getPost(postId), listComments(postId)])
      if (run !== generation.current) return
      setPost(postData)
      setComments(commentData)
      setState("ready")
    } catch (caught) {
      if (run !== generation.current) return
      if (caught instanceof ApiError && caught.status === 404) { setState("not-found"); return }
      setLoadError(caught instanceof Error ? caught.message : "게시글을 불러오지 못했습니다.")
      setState("error")
    }
  }, [enabled, postId])

  useEffect(() => {
    const counter = generation
    if (!enabled || postId === null) return
    const timer = window.setTimeout(() => void load(), 0)
    return () => { counter.current++; window.clearTimeout(timer) }
  }, [enabled, load, postId])

  function startEdit() {
    if (!post) return
    setEditTitle(post.title)
    setEditContent(post.content)
    setEditErrors({})
    setEditMessage("")
    setEditing(true)
  }

  async function saveEdit(event: FormEvent) {
    event.preventDefault()
    if (!post || savingRef.current) return
    savingRef.current = true
    setSaving(true)
    setEditErrors({})
    setEditMessage("")
    try {
      setPost(await updatePost(post.post_id, { title: editTitle, content: editContent }))
      setEditing(false)
    } catch (caught) {
      if (caught instanceof ApiError) setEditErrors(caught.fieldErrors)
      setEditMessage(caught instanceof Error ? caught.message : "게시글을 수정하지 못했습니다.")
    } finally {
      savingRef.current = false
      setSaving(false)
    }
  }

  async function confirmDelete() {
    if (!post || deleting) return
    setDeleting(true)
    setDeleteError("")
    try {
      await deletePost(post.post_id)
      navigateTo(listHref(kind))
    } catch (caught) {
      setDeleteError(caught instanceof Error ? caught.message : "게시글을 삭제하지 못했습니다.")
      setDeleting(false)
    }
  }

  const back = <a className={styles.titleLink} href={listHref(kind)}>목록으로</a>

  if (postId === null) return <EmptyState title="게시글 주소가 올바르지 않습니다" action={back}>목록에서 게시글을 다시 선택하세요.</EmptyState>
  if (!enabled) return <EmptyState title="서버 연결 후 게시글을 불러옵니다" />
  if (state === "loading") return <Spinner label="게시글을 불러오는 중" />
  if (state === "not-found") return <EmptyState title="게시글을 찾을 수 없습니다" action={back}>삭제되었거나 주소가 올바르지 않습니다.</EmptyState>
  if (state === "error" || !post) return <ErrorState onRetry={() => void load()}>{loadError}</ErrorState>

  const actions = <div className={styles.row}>
    {back}
    {!editing && post.can_edit && <Button variant="secondary" size="small" onClick={startEdit}>수정</Button>}
    {!editing && post.can_delete && <Button variant="danger" size="small" onClick={() => setConfirming(true)}>삭제</Button>}
  </div>

  if (editing) return <Card title="게시글 수정" actions={actions}>
    <form className={styles.stack} onSubmit={saveEdit} noValidate>
      {editMessage && <Alert tone="error">{editMessage}</Alert>}
      <TextInput label="제목" required maxLength={100} value={editTitle} error={editErrors.title?.[0]} disabled={saving} onChange={(event) => setEditTitle(event.target.value)} hint="100자 이내" />
      <Textarea label="내용" required rows={10} value={editContent} error={editErrors.content?.[0]} disabled={saving} onChange={(event) => setEditContent(event.target.value)} />
      <div className={styles.row}>
        <Button type="submit" pending={saving} disabled={!editTitle.trim() || !editContent.trim()}>수정 저장</Button>
        <Button variant="secondary" disabled={saving} onClick={() => setEditing(false)}>취소</Button>
      </div>
    </form>
  </Card>

  return <div className={styles.stack}>
    <Card title={post.title} actions={actions}>
      <div className={styles.stack}>
        <div className={styles.row}>
          <Badge tone={post.post_type === "공지" ? "info" : "neutral"}>{post.post_type}</Badge>
          {post.notice_category && <Badge>{noticeCategoryLabels[post.notice_category]}</Badge>}
        </div>
        <DetailList items={[
          { key: "writer", label: "작성자", value: writerLabel(post) },
          { key: "created", label: "작성일", value: formatDateTime(post.created_at) },
          ...(post.updated_at ? [{ key: "updated", label: "수정일", value: formatDateTime(post.updated_at) }] : []),
        ]} />
        <p className={styles.body}>{post.content}</p>
      </div>
    </Card>
    <Card>
      <CommentThread postId={post.post_id} comments={comments} enabled={enabled} onChanged={() => load({ quiet: true })} />
    </Card>
    <ConfirmDialog open={confirming} title="게시글 삭제" danger confirmLabel="삭제" busy={deleting} onClose={() => setConfirming(false)} onConfirm={() => void confirmDelete()}>
      <p>이 게시글을 삭제할까요? 삭제한 게시글은 목록에 다시 표시되지 않습니다.</p>
      {deleteError && <Alert tone="error">{deleteError}</Alert>}
    </ConfirmDialog>
  </div>
}
